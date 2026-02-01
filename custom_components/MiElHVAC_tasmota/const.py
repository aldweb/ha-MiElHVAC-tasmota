"""
Constants for the Tasmota MiElHVAC integration.
"""
from homeassistant.components.climate import HVACMode, HVACAction

DOMAIN = "mielhvac_tasmota"

# Configuration keys
CONF_DEVICE_ID = "device_id"
CONF_BASE_TOPIC = "base_topic"
CONF_MODEL = "model"

# Default values
DEFAULT_NAME = "HVAC"
DEFAULT_DEVICE_ID = "tasmota_hvac"
DEFAULT_MODEL = "MiElHVAC"

# Temperature parameters
MIN_TEMP = 10
MAX_TEMP = 31
TEMP_STEP = 1.0
PRECISION = 0.5

# HVAC mode mapping
HVAC_MODE_MAP = {
    "off": HVACMode.OFF,
    "auto": HVACMode.AUTO,
    "cool": HVACMode.COOL,
    "dry": HVACMode.DRY,
    "heat": HVACMode.HEAT,
    "fan_only": HVACMode.FAN_ONLY,
}

HVAC_MODE_REVERSE_MAP = {v: k for k, v in HVAC_MODE_MAP.items()}

# Action mapping
ACTION_MAP = {
    "off": HVACAction.OFF,
    "heat": HVACAction.HEATING,
    "cool": HVACAction.COOLING,
    "dry": HVACAction.DRYING,
    "fan_only": HVACAction.FAN,
    "auto": HVACAction.IDLE,
}

# Available modes
FAN_MODES = ["auto", "quiet", "1", "2", "3", "4"]
SWING_V_MODES = ["auto", "up", "up_middle", "center", "down_middle", "down", "swing"]
SWING_H_MODES = ["auto", "left", "left_middle", "center", "right_middle", "right", "swing"]
