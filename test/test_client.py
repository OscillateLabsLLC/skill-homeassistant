# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring
import unittest
from unittest.mock import Mock, patch

from ovos_utils.messagebus import FakeBus, FakeMessage
from skill_homeassistant.ha_client import HomeAssistantClient, SUPPORTED_DEVICES


class FakeConnector:
    def __init__(self):
        self.callbacks = []
        self.host = "http://fake.homeassistant.local"

    def register_callback(self, callback, *args):
        self.callbacks.append(callback)

    def turn_off(self, *args):
        return

    def get_device_state(self, entity_id):
        return {"entity_id": entity_id, "state": "on", "attributes": {}}


class TestHomeAssistantClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin = HomeAssistantClient(config={"foo": "bar"})
        fake_devices = [
            cls.plugin.device_types["media_player"](
                FakeConnector(),
                "test_media_player",
                "mdi:media_player",
                "test_media_player",
                "off",
                {"friendly_name": "Test Media Player"},
                "Living Room",
            ),
            cls.plugin.device_types["light"](
                FakeConnector(),
                "test_light",
                "mdi:light",
                "test_light",
                "on",
                {"friendly_name": "Test Light"},
                "Living Room",
            ),
            cls.plugin.device_types["switch"](
                FakeConnector(),
                "test_switch",
                "mdi:switch",
                "test_switch",
                "on",
                {"friendly_name": "Test Switch"},
                "Living Room",
            ),
            cls.plugin.device_types["sensor"](
                FakeConnector(),
                "test_sensor",
                "mdi:sensor",
                "test_sensor",
                "on",
                {"friendly_name": "Test Sensor"},
                "Living Room",
            ),
            cls.plugin.device_types["binary_sensor"](
                FakeConnector(),
                "test_binary_sensor",
                "mdi:binary_sensor",
                "test_binary_sensor",
                "on",
                {"friendly_name": "Test Binary Sensor"},
                "Living Room",
            ),
            cls.plugin.device_types["climate"](
                FakeConnector(),
                "test_climate",
                "mdi:climate",
                "test_climate",
                "on",
                {"friendly_name": "Test Climate"},
                "Living Room",
            ),
            cls.plugin.device_types["vacuum"](
                FakeConnector(),
                "test_vacuum",
                "mdi:vacuum",
                "test_vacuum",
                "on",
                {"friendly_name": "Test Vacuum"},
                "Living Room",
            ),
            cls.plugin.device_types["camera"](
                FakeConnector(),
                "test_camera",
                "mdi:camera",
                "test_camera",
                "on",
                {"friendly_name": "Test Camera"},
                "Living Room",
            ),
            cls.plugin.device_types["scene"](
                FakeConnector(),
                "test_scene",
                "mdi:scene",
                "test_scene",
                "on",
                {"friendly_name": "Test Scene"},
                "Living Room",
            ),
            cls.plugin.device_types["automation"](
                FakeConnector(),
                "test_automation",
                "mdi:automation",
                "test_automation",
                "on",
                {"friendly_name": "Test Automation"},
                "Living Room",
            ),
        ]
        for device in fake_devices:
            cls.plugin.registered_devices.append(device)
            cls.plugin.registered_device_names.append(device.device_attributes.get("friendly_name"))
        cls.testable_devices = {dtype.device_id.replace("test_", "") for dtype in cls.plugin.registered_devices}

    def test_plugin_loads_with_fake_bus(self):
        self.assertIsNotNone(self.plugin)
        self.assertIsInstance(self.plugin, HomeAssistantClient)

    def test_all_supported_device_types_available(self):
        # We want to make sure to at least instantiate one of every type in our tests
        self.assertSetEqual(set(SUPPORTED_DEVICES.keys()), self.testable_devices)

    def test_fuzzy_match_name_does_not_mutate(self):
        print(f"Pre-fuzzy_match: {self.plugin.registered_device_names[0]}")
        device_id = self.plugin.fuzzy_match_name(
            self.plugin.registered_devices,
            "test media layer",
            self.plugin.registered_device_names,
        )
        self.assertEqual(device_id, "test_media_player")
        # pfzy has mutated this before, we want to make sure it doesn't
        print(f"Post-fuzzy_match: {self.plugin.registered_device_names[0]}")
        self.assertIsInstance(self.plugin.registered_device_names[0], str)

    def test_fuzzy_match_name_handles_underscores(self):
        test_switch = self.plugin.device_types["switch"](
            FakeConnector(),
            "test_switch",
            "mdi:switch",
            "test_switch",
            "on",
            {"friendly_name": None},
            "Living Room",
        )
        plugin = HomeAssistantClient({"search_confidence_threshold": 0.75})
        # Overly broad search returning the result with high confidence score
        not_match = plugin.fuzzy_match_name([test_switch], "test", ["test_switch"])
        self.assertNotEqual(not_match, "test_switch")
        # Handle underscores appropriately
        match = plugin.fuzzy_match_name([test_switch], "test switch", ["test_switch"])
        self.assertEqual(match, "test_switch")

    # Get device
    def test_return_device_response_when_passed_explicitly(self):
        # Device passed explicitly
        fake_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.on", {"device_id": "test_switch"}, None)
        with patch.object(self.plugin, "_return_device_response") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_get_device(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_return_device_response_when_fuzzy_searching(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage("ovos.phal.plugin.homeassistant.get.device", {"device": "test switch"}, None)
        with patch.object(self.plugin, "_return_device_response") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_get_device(fake_message)
                self.assertTrue(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    def test_return_device_response_when_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage("ovos.phal.plugin.homeassistant.get.device", {"device": "NOT REAL"}, None)
        with patch.object(self.plugin, "_return_device_response") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_get_device(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Turn on device
    def test_handle_turn_on_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.on", {"device_id": "test_switch"}, None)
        with patch.object(self.plugin.device_types["switch"], "turn_on") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_turn_on(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_turn_on_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.on", {"device": "test switch"}, None)
        with patch.object(self.plugin.device_types["switch"], "turn_on") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_switch") as mock_fuzzy_search:
                self.plugin.handle_turn_on(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_turn_on_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.on", {"device": "NOT REAL"}, None)
        with patch.object(self.plugin.device_types["switch"], "turn_on") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_turn_on(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Turn off device
    def test_handle_turn_off_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.turn.off",
            {"device_id": "test_switch"},
            None,
        )
        with patch.object(self.plugin.device_types["switch"], "turn_off") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_turn_off(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_turn_off_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.off", {"device": "test switch"}, None)
        with patch.object(self.plugin.device_types["switch"], "turn_off") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_switch") as mock_fuzzy_search:
                self.plugin.handle_turn_off(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_turn_off_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage("ovos.phal.plugin.homeassistant.turn.off", {"device": "NOT REAL"}, None)
        with patch.object(self.plugin.device_types["switch"], "turn_off") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_turn_off(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Call supported function
    def test_handle_called_supported_function_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.call.supported.function",
            {
                "device_id": "test_switch",
                "function_name": "order_66",
                "function_args": "execute",
            },
            None,
        )
        with patch.object(self.plugin.device_types["switch"], "call_function") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_call_supported_function(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_called_supported_function_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.call.supported.function",
            {
                "device": "test switch",
                "function_name": "order_66",
                "function_args": "execute",
            },
            None,
        )
        with patch.object(self.plugin.device_types["switch"], "call_function") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_switch") as mock_fuzzy_search:
                self.plugin.handle_call_supported_function(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_called_supported_function_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.call.supported.function",
            {
                "device": "NOT REAL",
                "function_name": "order_66",
                "function_args": "execute",
            },
            None,
        )
        with patch.object(self.plugin.device_types["switch"], "call_function") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_call_supported_function(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Get light brightness
    def test_handle_get_light_brightness_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.brightness",
            {"device_id": "test_light"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_get_light_brightness(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_get_light_brightness_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.brightness",
            {"device": "test_switch"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_get_light_brightness(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_get_light_brightness_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.brightness",
            {"device": "NOT REAL"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_get_light_brightness(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Set light brightness
    def test_handle_set_light_brightness_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.brightness",
            {"device_id": "test_light", "brightness": 200},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_set_light_brightness(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_set_light_brightness_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.brightness",
            {"device": "test_switch", "brightness": 200},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_set_light_brightness(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_set_light_brightness_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.brightness",
            {"device": "NOT REAL", "brightness": 200},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_set_light_brightness(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Increase light brightness
    def test_handle_increase_light_brightness_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.increase.light.brightness",
            {"device_id": "test_light"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "increase_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_increase_light_brightness(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_increase_light_brightness_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.increase.light.brightness",
            {"device": "test_switch"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "increase_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_increase_light_brightness(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_increase_light_brightness_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.increase.light.brightness",
            {"device": "NOT REAL"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "increase_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_increase_light_brightness(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Decrease light brightness
    def test_handle_decrease_light_brightness_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.decrease.light.brightness",
            {"device_id": "test_light"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "decrease_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_decrease_light_brightness(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_decrease_light_brightness_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.decrease.light.brightness",
            {"device": "test_switch"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "decrease_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_decrease_light_brightness(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_decrease_light_brightness_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.decrease.light.brightness",
            {"device": "NOT REAL"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "decrease_brightness") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_decrease_light_brightness(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Get light color
    def test_handle_get_light_color_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.color",
            {"device_id": "test_light"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_spoken_color", return_value="black") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_get_light_color(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_get_light_color_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.color",
            {"device": "test_light"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_spoken_color", return_value="black") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_get_light_color(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_get_light_color_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.get.light.color",
            {"device": "NOT REAL"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "get_spoken_color", return_value="black") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_get_light_color(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    # Set light color
    def test_handle_set_light_color_with_device_id(self):
        # Device passed explicitly
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.color",
            {"device_id": "test_light", "color": "red"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_color") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name") as mock_fuzzy_search:
                self.plugin.handle_set_light_color(fake_message)
                self.assertTrue(mock_call.called)
                self.assertFalse(mock_fuzzy_search.called)

    def test_handle_set_light_color_fuzzy_search(self):
        # Device exists but STT is fuzzy
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.color",
            {"device": "test_light", "color": "red"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_color") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value="test_light") as mock_fuzzy_search:
                self.plugin.handle_set_light_color(fake_message)
                self.assertTrue(mock_fuzzy_search.called)
                self.assertTrue(mock_call.called)

    def test_handle_set_light_color_device_does_not_exist(self):
        # Device does not exist
        bad_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.set.light.color",
            {"device": "NOT REAL", "color": "red"},
            None,
        )
        with patch.object(self.plugin.device_types["light"], "set_color") as mock_call:
            with patch.object(self.plugin, "fuzzy_match_name", return_value=None) as mock_fuzzy_search:
                self.plugin.handle_set_light_color(bad_message)
                self.assertFalse(mock_call.called)
                self.assertTrue(mock_fuzzy_search.called)

    def test_brightness_increment_increase(self):
        fake_bulb = self.plugin.device_types["light"](
            FakeConnector(),
            "test_light",
            "mdi:light",
            "test_light",
            "on",
            {"friendly_name": "Test Light"},
            "Living Room",
        )
        with patch.object(fake_bulb, "call_function") as mock_call:
            with patch.object(fake_bulb, "update_device"):
                fake_bulb.increase_brightness(20)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": 20})
                fake_bulb.increase_brightness(50)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": 50})

    def test_brightness_increment_decrease(self):
        fake_bulb = self.plugin.device_types["light"](
            FakeConnector(),
            "test_light",
            "mdi:light",
            "test_light",
            "on",
            {"friendly_name": "Test Light"},
            "Living Room",
        )
        with patch.object(fake_bulb, "call_function") as mock_call:
            with patch.object(fake_bulb, "update_device"):
                fake_bulb.decrease_brightness(20)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": -20})
                fake_bulb.decrease_brightness(50)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": -50})

    @patch("requests.get")
    def test_verify_ssl(self, mock_get):
        # Use a separate plugin instance to avoid mutating shared state
        test_plugin = HomeAssistantClient(config={})

        # Set config directly, then call init_configuration
        test_plugin.config["host"] = "http://homeassistant.local"
        test_plugin.config["api_key"] = "FAKE_API_KEY"
        test_plugin.init_configuration()
        mock_get.assert_called_with(
            "http://homeassistant.local/api/states",
            headers={"Authorization": "Bearer FAKE_API_KEY", "content-type": "application/json"},
            timeout=3,
            verify=True,
        )
        mock_get.reset_mock()

        # Change the config to set verify_ssl to False
        test_plugin.config["verify_ssl"] = False
        test_plugin.init_configuration()
        # Verify that verify_ssl is now False
        mock_get.assert_called_with(
            "http://homeassistant.local/api/states",
            headers={"Authorization": "Bearer FAKE_API_KEY", "content-type": "application/json"},
            timeout=3,
            verify=False,
        )

    def test_toggle_automations_default(self):
        """Test toggle_automations property returns False by default."""
        plugin = HomeAssistantClient(config={})
        self.assertFalse(plugin.toggle_automations)

    def test_toggle_automations_configured(self):
        """Test toggle_automations property returns configured value."""
        plugin = HomeAssistantClient(config={"toggle_automations": True})
        self.assertTrue(plugin.toggle_automations)

    def test_handle_get_devices(self):
        """Test handle_get_devices returns list of device models."""
        result = self.plugin.handle_get_devices()
        self.assertIn("devices", result)
        self.assertIsInstance(result["devices"], list)
        self.assertGreater(len(result["devices"]), 0)

    @patch("skill_homeassistant.ha_client.HomeAssistantRESTConnector")
    def test_validate_instance_connection_success(self, mock_connector_class):
        """Test validate_instance_connection returns True on success."""
        mock_connector = Mock()
        mock_connector.get_all_devices.return_value = [{"entity_id": "light.test"}]
        mock_connector_class.return_value = mock_connector

        result = self.plugin.validate_instance_connection(
            "http://ha.local", "api_key", True, True
        )

        self.assertTrue(result)
        mock_connector.get_all_devices.assert_called_once()

    @patch("skill_homeassistant.ha_client.HomeAssistantRESTConnector")
    def test_validate_instance_connection_failure(self, mock_connector_class):
        """Test validate_instance_connection returns False on exception."""
        mock_connector_class.side_effect = Exception("Connection failed")

        result = self.plugin.validate_instance_connection(
            "http://ha.local", "api_key", True, True
        )

        self.assertFalse(result)

    def test_handle_call_supported_function_without_args(self):
        """Test calling a function without additional arguments."""
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.call.supported.function",
            {
                "device_id": "test_switch",
                "function_name": "toggle",
                # No function_args
            },
            None,
        )
        with patch.object(self.plugin.device_types["switch"], "call_function") as mock_call:
            self.plugin.handle_call_supported_function(fake_message)
            mock_call.assert_called_once_with("toggle")

    def test_return_device_response_with_extra_args(self):
        """Test _return_device_response logs warnings for extra args/kwargs."""
        result = self.plugin._return_device_response(
            "extra_arg",
            device_id="test_switch",
            extra_kwarg="value"
        )
        # Should still return the device despite extra args
        self.assertIsNotNone(result)

    def test_return_device_response_device_not_found(self):
        """Test _return_device_response returns empty dict when device not found."""
        result = self.plugin._return_device_response(device_id="nonexistent_device")
        self.assertEqual(result, {})

    def test_handle_assist_message_with_connector(self):
        """Test handle_assist_message calls connector method."""
        self.plugin.connector = Mock()
        self.plugin.connector.send_assist_command.return_value = {"response": "ok"}
        
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.assist.message",
            {"command": "turn on kitchen light"},
            None,
        )
        
        result = self.plugin.handle_assist_message(fake_message)
        
        self.plugin.connector.send_assist_command.assert_called_once_with("turn on kitchen light")
        self.assertEqual(result, {"response": "ok"})

    def test_handle_assist_message_without_connector(self):
        """Test handle_assist_message returns None when no connector."""
        self.plugin.connector = None
        
        fake_message = FakeMessage(
            "ovos.phal.plugin.homeassistant.assist.message",
            {"command": "turn on kitchen light"},
            None,
        )
        
        result = self.plugin.handle_assist_message(fake_message)
        
        self.assertIsNone(result)

    def test_device_get_state(self):
        """Test device get_state method."""
        device = self.plugin.registered_devices[0]
        state = device.get_state()
        self.assertIsNotNone(state)

    def test_device_get_id(self):
        """Test device get_id method."""
        device = self.plugin.registered_devices[0]
        device_id = device.get_id()
        self.assertEqual(device_id, device.device_id)

    def test_device_get_name(self):
        """Test device get_name method."""
        device = self.plugin.registered_devices[0]
        name = device.get_name()
        self.assertIsNotNone(name)

    def test_device_get_icon(self):
        """Test device get_icon method."""
        device = self.plugin.registered_devices[0]
        icon = device.get_icon()
        self.assertIsNotNone(icon)

    def test_device_get_attributes(self):
        """Test device get_attributes method."""
        device = self.plugin.registered_devices[0]
        attrs = device.get_attributes()
        self.assertIsInstance(attrs, dict)

    def test_device_is_on(self):
        """Test device is_on method."""
        # Find a device that's "on"
        for device in self.plugin.registered_devices:
            if device.device_state == "on":
                self.assertTrue(device.is_on())
                break

    def test_device_is_off(self):
        """Test device is_off method."""
        # Find a device that's "off"
        for device in self.plugin.registered_devices:
            if device.device_state == "off":
                self.assertTrue(device.is_off())
                break

    def test_device_get_has_device_class(self):
        """Test device get_has_device_class method."""
        device = self.plugin.registered_devices[0]
        result = device.get_has_device_class()
        self.assertIsInstance(result, bool)

    def test_device_get_device_class(self):
        """Test device get_device_class method."""
        device = self.plugin.registered_devices[0]
        # May be None if no device_class attribute
        _ = device.get_device_class()

    @patch("requests.get")
    def test_config_removal_clears_state(self, mock_get):
        """Test that removing config clears connector and device state."""
        # Use a separate plugin instance to avoid mutating shared state
        test_plugin = HomeAssistantClient(config={})

        # First, set up a valid connection
        test_plugin.config["host"] = "http://homeassistant.local"
        test_plugin.config["api_key"] = "FAKE_API_KEY"
        mock_get.return_value.json.return_value = [{"entity_id": "light.test", "state": "on"}]
        test_plugin.init_configuration()

        # Verify we have a connection
        self.assertTrue(test_plugin.instance_available)
        self.assertIsNotNone(test_plugin.connector)

        # Now remove the config
        test_plugin.config["host"] = ""
        test_plugin.config["api_key"] = ""
        test_plugin.init_configuration()

        # Verify state is cleared
        self.assertFalse(test_plugin.instance_available)
        self.assertIsNone(test_plugin.connector)
        self.assertEqual(test_plugin.devices, [])
        self.assertEqual(test_plugin.registered_devices, [])
        self.assertEqual(test_plugin.registered_device_names, [])

    @patch("requests.get")
    def test_update_config(self, mock_get):
        """Test that update_config updates config and reinitializes."""
        # Use a separate plugin instance to avoid mutating shared state
        test_plugin = HomeAssistantClient(config={})

        # Start with no config
        self.assertFalse(test_plugin.instance_available)

        # Use update_config to add configuration
        mock_get.return_value.json.return_value = [{"entity_id": "light.test", "state": "on"}]
        new_config = {"host": "http://new-ha.local", "api_key": "NEW_KEY"}
        test_plugin.update_config(new_config)

        # Verify config was updated and client initialized
        self.assertEqual(test_plugin.config["host"], "http://new-ha.local")
        self.assertEqual(test_plugin.config["api_key"], "NEW_KEY")
        self.assertTrue(test_plugin.instance_available)
        self.assertIsNotNone(test_plugin.connector)
