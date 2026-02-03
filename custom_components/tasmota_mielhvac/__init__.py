"""
Tasmota MiElHVAC integration for Home Assistant.
Auto-discovers HVAC devices via MQTT SENSOR messages.
"""
from __future__ import annotations
import logging
import json
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import Platform
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import async_dispatcher_send

DOMAIN = "tasmota_mielhvac"
PLATFORMS = [Platform.CLIMATE]

# Listen to SENSOR topic to detect MiElHVAC devices
DISCOVERY_TOPIC = "tele/+/SENSOR"
SIGNAL_HVAC_DISCOVERED = f"{DOMAIN}_hvac_discovered"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmota MiElHVAC from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "discovered_devices": {},
        "unsub": None,
    }
    
    # Start MQTT discovery
    @callback
    async def sensor_message_received(msg):
        """Handle SENSOR messages for MiElHVAC discovery."""
        try:
            # Parse topic to extract device ID
            # Topic format: tele/{device_id}/SENSOR
            match = re.match(r"tele/([^/]+)/SENSOR", msg.topic)
            if not match:
                return
            
            device_id = match.group(1)
            
            # Parse payload
            try:
                payload = json.loads(msg.payload)
            except json.JSONDecodeError:
                return
            
            # Check if this is a MiElHVAC device
            # Look for MiElHVAC key in the payload
            if "MiElHVAC" not in payload:
                return
            
            # Validate it has Temperature (minimum requirement)
            mielhvac_data = payload.get("MiElHVAC", {})
            if "Temperature" not in mielhvac_data:
                _LOGGER.debug("MiElHVAC found in %s but no Temperature", device_id)
                return
            
            # Check if already discovered
            discovered = hass.data[DOMAIN][entry.entry_id]["discovered_devices"]
            if device_id in discovered:
                return
            
            _LOGGER.info("🎯 Discovered MiElHVAC device: %s (Temperature: %s°C)", 
                        device_id, mielhvac_data.get("Temperature"))
            
            # Mark as discovered
            discovered[device_id] = {
                "device_id": device_id,
                "base_topic": device_id,
            }
            
            # Signal discovery to climate platform
            async_dispatcher_send(
                hass,
                SIGNAL_HVAC_DISCOVERED,
                device_id,
            )
            
        except Exception as err:
            _LOGGER.error("Error processing MiElHVAC discovery: %s", err)
    
    # Subscribe to SENSOR topic
    unsub = await mqtt.async_subscribe(
        hass,
        DISCOVERY_TOPIC,
        sensor_message_received,
        qos=1,
    )
    
    hass.data[DOMAIN][entry.entry_id]["unsub"] = unsub
    
    _LOGGER.info("Listening for MiElHVAC devices on topic: %s", DISCOVERY_TOPIC)
    
    # Forward to climate platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unsubscribe from MQTT
    if hass.data[DOMAIN][entry.entry_id]["unsub"]:
        hass.data[DOMAIN][entry.entry_id]["unsub"]()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
