"""
Climate platform for Tasmota MiElHVAC integration.
"""
from __future__ import annotations
import json

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    CONF_NAME,
    UnitOfTemperature,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import mqtt
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_BASE_TOPIC,
    CONF_MODEL,
    MIN_TEMP,
    MAX_TEMP,
    TEMP_STEP,
    PRECISION,
    HVAC_MODE_MAP,
    HVAC_MODE_REVERSE_MAP,
    ACTION_MAP,
    FAN_MODES,
    SWING_V_MODES,
    SWING_H_MODES,
    DEFAULT_NAME,
    DEFAULT_MODEL,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tasmota MiElHVAC climate from config entry."""
    async_add_entities([MiElHVACTasmota(hass, config_entry)])


class MiElHVACTasmota(ClimateEntity):
    """Representation of a Mitsubishi Electric heat pump via Tasmota MiElHVAC."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._config_entry = config_entry
        
        # Configuration data
        self._device_id = config_entry.data.get(CONF_DEVICE_ID)
        self._base_topic = config_entry.data.get(CONF_BASE_TOPIC, self._device_id)
        self._model = config_entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        self._name = config_entry.data.get(CONF_NAME, DEFAULT_NAME)
        
        # Dynamic MQTT topics
        self._topic_avail = f"tele/{self._base_topic}/LWT"
        self._topic_sensor = f"tele/{self._base_topic}/SENSOR"
        self._topic_state = f"tele/{self._base_topic}/HVACSETTINGS"
        self._topic_cmd_mode = f"cmnd/{self._base_topic}/HVACSetHAMode"
        self._topic_cmd_temp = f"cmnd/{self._base_topic}/HVACSetTemp"
        self._topic_cmd_swing_v = f"cmnd/{self._base_topic}/HVACSetSwingV"
        self._topic_cmd_swing_h = f"cmnd/{self._base_topic}/HVACSetSwingH"
        self._topic_cmd_fan = f"cmnd/{self._base_topic}/HVACSetFanSpeed"
        
        # Entity identifiers
        self._attr_unique_id = f"{self._device_id}_climate"
        self._attr_name = self._name
        self._attr_has_entity_name = True
        
        # Device info for registry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
            manufacturer="Mitsubishi Electric",
            model=self._model,
            sw_version="Tasmota MiElHVAC",
        )
        
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

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT topics when added to hass."""
        
        @callback
        def availability_received(msg):
            """Handle availability messages."""
            self._available = msg.payload == "Online"
            self.async_write_ha_state()
        
        await mqtt.async_subscribe(
            self.hass, self._topic_avail, availability_received, 1
        )
        
        @callback
        def current_temp_received(msg):
            """Handle current temperature updates."""
            try:
                data = json.loads(msg.payload)
                temp = data.get(self._model, {}).get("Temperature")
                if temp is not None:
                    self._attr_current_temperature = float(temp)
                    self.async_write_ha_state()
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        await mqtt.async_subscribe(
            self.hass, self._topic_sensor, current_temp_received, 1
        )
        
        @callback
        def state_received(msg):
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
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        await mqtt.async_subscribe(
            self.hass, self._topic_state, state_received, 1
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

