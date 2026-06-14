"""Home Assistant Constants Module.

This module contains constants used throughout the Home Assistant client.
"""

from skill_homeassistant.ha_client.logic.device import (
    HomeAssistantAutomation,
    HomeAssistantBinarySensor,
    HomeAssistantCamera,
    HomeAssistantClimate,
    HomeAssistantLight,
    HomeAssistantMediaPlayer,
    HomeAssistantScene,
    HomeAssistantScript,
    HomeAssistantSensor,
    HomeAssistantSwitch,
    HomeAssistantVacuum,
)

SUPPORTED_DEVICES = {
    "sensor": HomeAssistantSensor,
    "binary_sensor": HomeAssistantBinarySensor,
    "light": HomeAssistantLight,
    "media_player": HomeAssistantMediaPlayer,
    "vacuum": HomeAssistantVacuum,
    "switch": HomeAssistantSwitch,
    "climate": HomeAssistantClimate,
    "camera": HomeAssistantCamera,
    "scene": HomeAssistantScene,
    "script": HomeAssistantScript,
    "automation": HomeAssistantAutomation,
}
