"""
Tasmota MiElHVAC Integration for Home Assistant.

This integration auto-discovers Mitsubishi Electric HVAC devices controlled
by Tasmota's MiElHVAC driver. It leverages Tasmota's native MQTT discovery
to automatically link climate entities to existing Tasmota devices.

Discovery flow:
1. Listens to tasmota/discovery/+/config for device MAC addresses and names
2. Monitors tele/+/SENSOR for MiElHVAC temperature data
3. Creates climate entities linked to Tasmota devices via MAC address
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

DOMAIN = "tasmota_mielhvac"
PLATFORMS = [Platform.CLIMATE]

# MQTT topic patterns
DISCOVERY_TOPIC = "tele/+/SENSOR"
TASMOTA_DISCOVERY_TOPIC = "tasmota/discovery/+/config"

# Internal signal for device discovery
SIGNAL_HVAC_DISCOVERED = f"{DOMAIN}_hvac_discovered"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmota MiElHVAC from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "discovered_devices": {},
        "tasmota_devices": {},
        "unsub": [],
    }

    @callback
    async def tasmota_discovery_received(msg: mqtt.ReceiveMessage) -> None:
        """Process Tasmota discovery messages to cache device metadata."""
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return

        mac = payload.get("mac")
        topic = payload.get("t")

        if not mac or not topic:
            return

        # Cache Tasmota device metadata
        tasmota_devices = hass.data[DOMAIN][entry.entry_id]["tasmota_devices"]
        tasmota_devices[topic] = {
            "mac": mac,
            "device_name": payload.get("dn"),
            "model": payload.get("md"),
            "ip": payload.get("ip"),
        }

        # Update already discovered MiElHVAC devices with MAC/name if needed
        discovered = hass.data[DOMAIN][entry.entry_id]["discovered_devices"]
        if topic in discovered and not discovered[topic].get("mac"):
            discovered[topic]["mac"] = mac
            discovered[topic]["device_name"] = payload.get("dn")

            _LOGGER.info(
                "Linked MiElHVAC device '%s' to Tasmota device (MAC: %s)",
                topic,
                mac,
            )

            # Re-signal with updated metadata
            async_dispatcher_send(
                hass,
                SIGNAL_HVAC_DISCOVERED,
                topic,
                mac,
                payload.get("dn"),
            )

    @callback
    async def sensor_message_received(msg: mqtt.ReceiveMessage) -> None:
        """Discover MiElHVAC devices from SENSOR messages."""
        # Extract device ID from topic (tele/{device_id}/SENSOR)
        match = re.match(r"tele/([^/]+)/SENSOR", msg.topic)
        if not match:
            return

        device_id = match.group(1)

        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError:
            return

        # Check for MiElHVAC data with required Temperature field
        mielhvac_data = payload.get("MiElHVAC")
        if not mielhvac_data or "Temperature" not in mielhvac_data:
            return

        # Skip if already discovered
        discovered = hass.data[DOMAIN][entry.entry_id]["discovered_devices"]
        if device_id in discovered:
            return

        # Retrieve cached Tasmota metadata
        tasmota_devices = hass.data[DOMAIN][entry.entry_id]["tasmota_devices"]
        tasmota_info = tasmota_devices.get(device_id, {})
        mac = tasmota_info.get("mac")
        device_name = tasmota_info.get("device_name")

        _LOGGER.info(
            "Discovered MiElHVAC device: %s (Temperature: %.1f°C)%s",
            device_id,
            float(mielhvac_data.get("Temperature")),
            f" - {device_name}" if device_name else "",
        )

        # Mark as discovered
        discovered[device_id] = {
            "device_id": device_id,
            "mac": mac,
            "device_name": device_name,
        }

        # Signal discovery to climate platform
        async_dispatcher_send(
            hass,
            SIGNAL_HVAC_DISCOVERED,
            device_id,
            mac,
            device_name,
        )

    # Subscribe to both discovery topics
    unsub_tasmota = await mqtt.async_subscribe(
        hass,
        TASMOTA_DISCOVERY_TOPIC,
        tasmota_discovery_received,
        qos=1,
    )

    unsub_sensor = await mqtt.async_subscribe(
        hass,
        DISCOVERY_TOPIC,
        sensor_message_received,
        qos=1,
    )

    hass.data[DOMAIN][entry.entry_id]["unsub"] = [unsub_tasmota, unsub_sensor]

    _LOGGER.info(
        "Started listening for Tasmota devices and MiElHVAC sensors"
    )

    # Forward setup to climate platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry."""
    # Unsubscribe from MQTT topics
    for unsub in hass.data[DOMAIN][entry.entry_id]["unsub"]:
        unsub()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
