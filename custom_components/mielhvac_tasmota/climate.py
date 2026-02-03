"""
Climate platform for Tasmota MiElHVAC integration.
Auto-created entities based on MQTT discovery.
"""
from __future__ import annotations
import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.components.mqtt import subscription
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    DEFAULT_MODEL,
    MIN_TEMP,
    MAX_TEMP,
    TEMP_STEP,
    PRECISION,
    HVAC_MODE_MAP,
    HVAC_MODE_REVERSE_MAP,
    ACTION_MAP,
    FAN_MODES,
    SWING_V_MODES,
)

_LOGGER = logging.getLogger(__name__)

SIGNAL_HVAC_DISCOVERED = f"{DOMAIN}_hvac_discovered"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tasmota MiElHVAC climate entities."""
    
    created_entities = {}
    
    @callback
    def async_discover_hvac(device_id: str):
        """Handle discovery of a new HVAC device."""
        if device_id in created_entities:
            _LOGGER.debug("HVAC device %s already created", device_id)
            return
        
        _LOGGER.info("Creating climate entity for %s", device_id)
        
        # Create entity
        entity = MiElHVACTasmota(hass, device_id)
        created_entities[device_id] = entity
        
        # Add to Home Assistant
        async_add_entities([entity])
    
    # Listen for discovery events
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_HVAC_DISCOVERED,
            async_discover_hvac,
        )
    )


class MiElHVACTasmota(ClimateEntity, RestoreEntity):
    """Climate entity auto-created from MQTT discovery."""

    def __init__(self, hass: HomeAssistant, device_id: str) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._device_id = device_id
        self._base_topic = device_id
        self._model = DEFAULT_MODEL
        
        # Dynamic MQTT topics
        self._topic_avail = f"tele/{self._base_topic}/LWT"
        self._topic_sensor = f"tele/{self._base_topic}/SENSOR"
        self._topic_state = f"tele/{self._base_topic}/HVACSETTINGS"
        self._topic_cmd_mode = f"cmnd/{self._base_topic}/HVACSetHAMode"
        self._topic_cmd_temp = f"cmnd/{self._base_topic}/HVACSetTemp"
        self._topic_cmd_swing_v = f"cmnd/{self._base_topic}/HVACSetSwingV"
        self._topic_cmd_swing_h = f"cmnd/{self._base_topic}/HVACSetSwingH"
        self._topic_cmd_fan = f"cmnd/{self._base_topic}/HVACSetFanSpeed"
        
        # Find existing Tasmota device by looking for related entities
        device_registry = dr.async_get(hass)
        from homeassistant.helpers import entity_registry as er
        entity_reg = er.async_get(hass)
        
        existing_device = None
        
        _LOGGER.info("=" * 60)
        _LOGGER.info("Searching for device with topic: %s", self._device_id)
        
        # Extract the topic part (e.g., "wPac1" from "tasmota_wPac1")
        topic_short = self._device_id.replace("tasmota_", "")
        
        # Search for entities that match our topic
        # Look for entity_ids like: sensor.wpac_1_*, sensor.wPac1_*, etc.
        search_patterns = [
            topic_short.lower(),  # wpac1
            topic_short.lower().replace("w", "w_"),  # w_pac1
            topic_short.replace("_", " ").lower(),  # wpac 1
        ]
        
        _LOGGER.info("Searching for entities matching patterns: %s", search_patterns)
        
        matching_entities = []
        for entity in entity_reg.entities.values():
            entity_id_lower = entity.entity_id.lower()
            # Check if entity_id contains our topic patterns
            for pattern in search_patterns:
                if pattern in entity_id_lower:
                    matching_entities.append({
                        "entity_id": entity.entity_id,
                        "device_id": entity.device_id,
                        "platform": entity.platform,
                    })
                    break
        
        _LOGGER.info("Found %d entities matching our topic:", len(matching_entities))
        for ent in matching_entities[:5]:  # Log first 5
            _LOGGER.info("  - %s (platform: %s, device: %s)", 
                        ent["entity_id"], ent["platform"], ent["device_id"])
        
        # Find the device that has the most matching entities
        device_entity_count = {}
        for ent in matching_entities:
            if ent["device_id"]:
                device_entity_count[ent["device_id"]] = device_entity_count.get(ent["device_id"], 0) + 1
        
        if device_entity_count:
            # Get device with most entities
            best_device_id = max(device_entity_count, key=device_entity_count.get)
            existing_device = device_registry.devices.get(best_device_id)
            
            if existing_device:
                _LOGGER.info("✓ MATCH by entities! Device: %s (%d matching entities)",
                            existing_device.name or existing_device.name_by_user,
                            device_entity_count[best_device_id])
                _LOGGER.info("  Device identifiers: %s", list(existing_device.identifiers))
        
        if not existing_device:
            _LOGGER.warning("✗ NO MATCH - Device not found")
        
        _LOGGER.info("=" * 60)
        
        # Determine entity name and device info
        if existing_device:
            # Use device's actual name
            device_name = (
                existing_device.name_by_user 
                or existing_device.name 
                or self._device_id
            )
            
            # Attach to existing Tasmota device using exact same identifiers
            self._attr_device_info = {
                "identifiers": existing_device.identifiers,
            }
        else:
            # Device not found - create standalone with a proper name
            # Extract readable name from topic ID
            # tasmota_wPac1 -> wPac1 -> WPAC1
            clean_name = self._device_id.replace("tasmota_", "")
            device_name = clean_name
            
            _LOGGER.warning(
                "Creating standalone climate entity for %s with name '%s'",
                self._device_id,
                device_name
            )
            
            # Fallback: create minimal device info
            self._attr_device_info = {
                "identifiers": {("tasmota", self._device_id)},
                "name": f"{clean_name}",  # Don't add "HVAC" prefix to device name
                "manufacturer": "Tasmota",
                "model": "MiElHVAC",
            }
        
        # Entity configuration - CRITICAL: set name before entity is registered
        self._attr_unique_id = f"{self._device_id}_climate"
        self._attr_name = f"{device_name} Climate"
        self._attr_has_entity_name = False
        
        _LOGGER.info("Entity will be named: '%s'", self._attr_name)
        
        # Temperature configuration
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP
        self._attr_target_temperature_step = TEMP_STEP
        self._attr_precision = PRECISION
        
        # Current states
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_action = HVACAction.OFF
        self._attr_fan_mode = "auto"
        self._attr_swing_mode = "auto"
        self._swing_h_mode = "auto"
        self._available = False
        
        # Supported modes
        self._attr_hvac_modes = list(HVAC_MODE_MAP.values())
        self._attr_fan_modes = FAN_MODES
        self._attr_swing_modes = SWING_V_MODES
        
        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
        )
        
        # Subscription tracking
        self._sub_state = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when added to hass."""
        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state:
            if last_state.state in HVAC_MODE_MAP.values():
                self._attr_hvac_mode = HVACMode(last_state.state)
            if last_state.attributes.get(ATTR_TEMPERATURE):
                self._attr_target_temperature = float(
                    last_state.attributes.get(ATTR_TEMPERATURE)
                )
            if last_state.attributes.get("fan_mode"):
                self._attr_fan_mode = last_state.attributes.get("fan_mode")
            if last_state.attributes.get("swing_mode"):
                self._attr_swing_mode = last_state.attributes.get("swing_mode")
            if last_state.attributes.get("swing_horizontal"):
                self._swing_h_mode = last_state.attributes.get("swing_horizontal")
        
        # Subscribe to topics
        await self._subscribe_topics()

    async def _subscribe_topics(self):
        """(Re)Subscribe to MQTT topics."""
        
        @callback
        def availability_received(msg: ReceiveMessage):
            """Handle availability messages."""
            self._available = msg.payload == "Online"
            self.async_write_ha_state()
        
        @callback
        def current_temp_received(msg: ReceiveMessage):
            """Handle current temperature updates."""
            try:
                data = json.loads(msg.payload)
                temp = data.get(self._model, {}).get("Temperature")
                if temp is not None:
                    self._attr_current_temperature = float(temp)
                    self.async_write_ha_state()
            except (json.JSONDecodeError, ValueError, KeyError) as err:
                _LOGGER.debug("Error parsing temperature for %s: %s", self._device_id, err)
        
        @callback
        def state_received(msg: ReceiveMessage):
            """Handle state updates."""
            try:
                data = json.loads(msg.payload)
                
                if "Temp" in data:
                    self._attr_target_temperature = float(data["Temp"])
                
                if "HAMode" in data:
                    ha_mode = data["HAMode"]
                    self._attr_hvac_mode = HVAC_MODE_MAP.get(ha_mode, HVACMode.OFF)
                    self._attr_hvac_action = ACTION_MAP.get(ha_mode, HVACAction.OFF)
                
                if "FanSpeed" in data:
                    self._attr_fan_mode = data["FanSpeed"]
                
                if "SwingV" in data:
                    self._attr_swing_mode = data["SwingV"]
                
                if "SwingH" in data:
                    self._swing_h_mode = data["SwingH"]
                
                self.async_write_ha_state()
            except (json.JSONDecodeError, ValueError, KeyError) as err:
                _LOGGER.debug("Error parsing state for %s: %s", self._device_id, err)
        
        # Subscribe to all topics
        self._sub_state = subscription.async_prepare_subscribe_topics(
            self.hass,
            self._sub_state,
            {
                "availability": {
                    "topic": self._topic_avail,
                    "msg_callback": availability_received,
                    "qos": 1,
                },
                "sensor": {
                    "topic": self._topic_sensor,
                    "msg_callback": current_temp_received,
                    "qos": 1,
                },
                "state": {
                    "topic": self._topic_state,
                    "msg_callback": state_received,
                    "qos": 1,
                },
            },
        )
        await subscription.async_subscribe_topics(self.hass, self._sub_state)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        self._sub_state = subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "swing_horizontal": self._swing_h_mode,
        }

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await mqtt.async_publish(
                self.hass,
                self._topic_cmd_temp,
                str(int(temperature)),
                qos=1,
                retain=False,
            )
            self._attr_target_temperature = temperature
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        tasmota_mode = HVAC_MODE_REVERSE_MAP.get(hvac_mode)
        if tasmota_mode:
            await mqtt.async_publish(
                self.hass,
                self._topic_cmd_mode,
                tasmota_mode,
                qos=1,
                retain=False,
            )
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        if fan_mode in self._attr_fan_modes:
            await mqtt.async_publish(
                self.hass,
                self._topic_cmd_fan,
                fan_mode,
                qos=1,
                retain=False,
            )
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new vertical swing mode."""
        if swing_mode in self._attr_swing_modes:
            await mqtt.async_publish(
                self.hass,
                self._topic_cmd_swing_v,
                swing_mode,
                qos=1,
                retain=False,
            )
            self._attr_swing_mode = swing_mode
            self.async_write_ha_state()
