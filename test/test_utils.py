import unittest
from unittest.mock import patch
from skill_homeassistant.ha_client.logic.utils import (
    map_entity_to_device_type,
    check_if_device_type_is_group,
    get_device_info,
    get_percentage_brightness_from_ha_value,
    get_ha_value_from_percentage_brightness,
    search_for_device_by_id,
)


class TestUtils(unittest.TestCase):
    def test_map_entity_to_device_type(self):
        # Test supported device types
        self.assertEqual(map_entity_to_device_type("light.living_room"), "light")
        self.assertEqual(map_entity_to_device_type("switch.kitchen"), "switch")
        self.assertEqual(map_entity_to_device_type("media_player.tv"), "media_player")

        # Test unsupported device type
        self.assertIsNone(map_entity_to_device_type("unknown.device"))

        # Test exception handling (e.g. passing None or non-string that fails split)
        # The function catches exceptions and prints them, returning None
        with patch("builtins.print") as mock_print:
            self.assertIsNone(map_entity_to_device_type(123))
            mock_print.assert_called()

    def test_check_if_device_type_is_group(self):
        # Test group icon
        self.assertTrue(check_if_device_type_is_group({"icon": "mdi:light-group"}))

        # Test non-group icon
        self.assertFalse(check_if_device_type_is_group({"icon": "mdi:light"}))

        # Test missing icon key
        self.assertFalse(check_if_device_type_is_group({"friendly_name": "Test"}))

    def test_get_device_info(self):
        devices = [
            {"id": "light.living_room", "state": "on"},
            {"id": "switch.kitchen", "state": "off"},
        ]

        # Test finding a device
        result = get_device_info(devices, "light.living_room")
        self.assertEqual(result, {"id": "light.living_room", "state": "on"})

        # Test device not found (raises IndexError based on current implementation)
        with self.assertRaises(IndexError):
            get_device_info(devices, "non_existent")

    def test_get_percentage_brightness_from_ha_value(self):
        # Test normal values
        self.assertEqual(get_percentage_brightness_from_ha_value(255), 100)
        self.assertEqual(get_percentage_brightness_from_ha_value(0), 0)
        self.assertEqual(get_percentage_brightness_from_ha_value(127.5), 50)

        # Test None input
        self.assertEqual(get_percentage_brightness_from_ha_value(None), 0)

    def test_get_ha_value_from_percentage_brightness(self):
        # Test normal values
        self.assertEqual(get_ha_value_from_percentage_brightness(100), 255)
        self.assertEqual(get_ha_value_from_percentage_brightness(0), 0)
        # 50% of 255 is 127.5, which rounds to 128
        self.assertEqual(get_ha_value_from_percentage_brightness(50), 128)

        # Test None input
        self.assertEqual(get_ha_value_from_percentage_brightness(None), 0)

    def test_search_for_device_by_id(self):
        devices = [
            {"id": "light.living_room", "state": "on"},
            {"id": "switch.kitchen", "state": "off"},
        ]

        # Test found device index
        self.assertEqual(search_for_device_by_id(devices, "light.living_room"), 0)
        self.assertEqual(search_for_device_by_id(devices, "switch.kitchen"), 1)

        # Test not found
        self.assertIsNone(search_for_device_by_id(devices, "sensor.temp"))


if __name__ == "__main__":
    unittest.main()
