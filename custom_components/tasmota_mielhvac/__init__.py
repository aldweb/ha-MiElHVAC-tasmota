"""
Tasmota MiElHVAC integration for Home Assistant.
Auto-discovers HVAC devices via MQTT SENSOR messages and Tasmota discovery.
Uses Tasmota native discovery to get MAC address directly.
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
# Listen to Tasmota discovery for MAC addresses
TASMOTA_DISCOVERY_TOPIC = "tasmota/discovery/+/config"
SIGNAL_HVAC_DISCOVERED = f"{DOMAIN}_hvac_discovered"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmota MiElHVAC from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "discovered_devices": {},
        "tasmota_devices": {},  # Store Tasmota discovery data (MAC, etc.)
        "unsub": [],
    }
    
    # Callback for Tasmota discovery messages
    @callback
    async def tasmota_discovery_received(msg):
        """Handle Tasmota discovery messages to extract MAC and topic."""
        try:
            # Parse payload
            try:
                payload = json.loads(msg.payload)
            except json.JSONDecodeError:
                return
            
            # Extract MAC and topic
            mac = payload.get("mac")
            topic = payload.get("t")  # Topic du device
            
            if not mac or not topic:
                return
            
            # Store Tasmota device info
            tasmota_devices = hass.data[DOMAIN][entry.entry_id]["tasmota_devices"]
            tasmota_devices[topic] = {
                "mac": mac,
                "device_name": payload.get("dn"),
                "model": payload.get("md"),
                "ip": payload.get("ip"),
            }
            
            _LOGGER.debug(
                "Stored Tasmota device info: %s (MAC: %s)",
                topic,
                mac
            )
            
            # If we already discovered this device as MiElHVAC, signal with MAC
            discovered = hass.data[DOMAIN][entry.entry_id]["discovered_devices"]
            if topic in discovered and not discovered[topic].get("mac"):
                discovered[topic]["mac"] = mac
                _LOGGER.info(
                    "✅ Linked MiElHVAC device %s to MAC %s via Tasmota discovery",
                    topic,
                    mac
                )
                # Re-signal discovery with MAC now available
                async_dispatcher_send(
                    hass,
                    SIGNAL_HVAC_DISCOVERED,
                    topic,
                    mac,
                )
            
        except Exception as err:
            _LOGGER.error("Error processing Tasmota discovery: %s", err)
    
    # Callback for SENSOR messages
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
            
            # Get MAC from Tasmota discovery if available
            tasmota_devices = hass.data[DOMAIN][entry.entry_id]["tasmota_devices"]
            mac = tasmota_devices.get(device_id, {}).get("mac")
            
            _LOGGER.info(
                "🎯 Discovered MiElHVAC device: %s (Temperature: %s°C)%s",
                device_id,
                mielhvac_data.get("Temperature"),
                f" with MAC {mac}" if mac else ""
            )
            
            # Mark as discovered
            discovered[device_id] = {
                "device_id": device_id,
                "base_topic": device_id,
                "mac": mac,  # May be None if Tasmota discovery not received yet
            }
            
            # Signal discovery to climate platform
            async_dispatcher_send(
                hass,
                SIGNAL_HVAC_DISCOVERED,
                device_id,
                mac,  # Pass MAC (may be None)
            )
            
        except Exception as err:
            _LOGGER.error("Error processing MiElHVAC discovery: %s", err)
    
    # Subscribe to Tasmota discovery topic
    unsub_tasmota = await mqtt.async_subscribe(
        hass,
        TASMOTA_DISCOVERY_TOPIC,
        tasmota_discovery_received,
        qos=1,
    )
    
    # Subscribe to SENSOR topic
    unsub_sensor = await mqtt.async_subscribe(
        hass,
        DISCOVERY_TOPIC,
        sensor_message_received,
        qos=1,
    )
    
    hass.data[DOMAIN][entry.entry_id]["unsub"] = [unsub_tasmota, unsub_sensor]
    
    _LOGGER.info("Listening for Tasmota discovery on: %s", TASMOTA_DISCOVERY_TOPIC)
    _LOGGER.info("Listening for MiElHVAC devices on: %s", DISCOVERY_TOPIC)
    
    # Forward to climate platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unsubscribe from MQTT
    for unsub in hass.data[DOMAIN][entry.entry_id]["unsub"]:
        unsub()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
