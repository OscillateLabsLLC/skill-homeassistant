# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring
import unittest
from unittest.mock import Mock, patch

from skill_homeassistant.ha_client.logic.device import (
    HomeAssistantDevice,
    HomeAssistantLight,
    HomeAssistantSensor,
    HomeAssistantBinarySensor,
    HomeAssistantCover,
    HomeAssistantMediaPlayer,
    HomeAssistantClimate,
    HomeAssistantVacuum,
    HomeAssistantScene,
    HomeAssistantAutomation,
)


class FakeConnector:
    """Fake connector for testing devices."""

    def __init__(self):
        self.callbacks = {}
        self.host = "http://fake.homeassistant.local"
        self._device_states = {}

    def register_callback(self, device_id, callback):
        self.callbacks[device_id] = callback

    def turn_on(self, device_id, device_type):
        return {"state": "on"}

    def turn_off(self, device_id, device_type):
        return {"state": "off"}

    def call_function(self, device_id, device_type, function_name, function_args=None):
        return {"result": "success"}

    def get_device_state(self, entity_id):
        return self._device_states.get(
            entity_id,
            {
                "entity_id": entity_id,
                "state": "on",
                "attributes": {"friendly_name": "Test Device", "icon": "mdi:test"},
            },
        )

    def set_device_state(self, device_id, state, attributes):
        self._device_states[device_id] = {"state": state, "attributes": attributes}


class TestHomeAssistantDevice(unittest.TestCase):
    """Tests for the base HomeAssistantDevice class."""

    def setUp(self):
        self.connector = FakeConnector()
        self.device = HomeAssistantDevice(
            connector=self.connector,
            device_id="light.test_device",
            device_icon="mdi:lightbulb",
            device_name="Test Device",
            device_state="on",
            device_attributes={"friendly_name": "Test Device", "brightness": 255},
            device_area="Living Room",
        )

    def test_device_initialization_parses_type_from_id(self):
        """Test device_type is correctly parsed from entity_id prefix."""
        self.assertEqual(self.device.device_type, "light")
        
        sensor = HomeAssistantDevice(
            connector=self.connector,
            device_id="sensor.temperature",
            device_icon="mdi:thermometer",
            device_name="Temp",
            device_state="72",
            device_attributes={},
        )
        self.assertEqual(sensor.device_type, "sensor")

    def test_device_registers_callback_on_init(self):
        """Test device registers callback with connector during initialization."""
        self.assertIn("light.test_device", self.connector.callbacks)
        self.assertEqual(self.connector.callbacks["light.test_device"], self.device.callback_listener)

    def test_callback_listener_updates_state_on_state_changed(self):
        """Test callback_listener updates device state when receiving state_changed event."""
        message = {
            "event": {
                "event_type": "state_changed",
                "data": {
                    "new_state": {
                        "entity_id": "light.test_device",
                        "state": "off",
                        "attributes": {"brightness": 0},
                    }
                },
            }
        }
        self.device.callback_listener(message)
        self.assertEqual(self.device.device_state, "off")
        self.assertEqual(self.device.device_attributes["brightness"], 0)

    def test_callback_listener_ignores_events_for_other_entities(self):
        """Test callback_listener does not update state for different entity_id."""
        original_state = self.device.device_state
        original_brightness = self.device.device_attributes["brightness"]
        message = {
            "event": {
                "event_type": "state_changed",
                "data": {
                    "new_state": {
                        "entity_id": "light.other_device",
                        "state": "off",
                        "attributes": {"brightness": 0},
                    }
                },
            }
        }
        self.device.callback_listener(message)
        self.assertEqual(self.device.device_state, original_state)
        self.assertEqual(self.device.device_attributes["brightness"], original_brightness)

    def test_callback_listener_ignores_non_state_changed_events(self):
        """Test callback_listener ignores events that aren't state_changed."""
        original_state = self.device.device_state
        message = {
            "event": {
                "event_type": "call_service",  # Not state_changed
                "data": {
                    "new_state": {
                        "entity_id": "light.test_device",
                        "state": "off",
                        "attributes": {},
                    }
                },
            }
        }
        self.device.callback_listener(message)
        self.assertEqual(self.device.device_state, original_state)

    def test_query_device_class_sets_class_when_present(self):
        """Test device_class is detected from attributes during init."""
        device = HomeAssistantDevice(
            connector=self.connector,
            device_id="sensor.temp",
            device_icon="mdi:thermometer",
            device_name="Temperature",
            device_state="72",
            device_attributes={"device_class": "temperature"},
        )
        self.assertTrue(device.has_device_class)
        self.assertEqual(device.device_class, "temperature")

    def test_query_device_class_unset_when_missing(self):
        """Test device_class is None when not in attributes."""
        self.assertFalse(self.device.has_device_class)
        self.assertIsNone(self.device.device_class)

    def test_get_attribute_raises_keyerror_for_missing_key(self):
        """Test get_attribute raises KeyError when attribute doesn't exist."""
        with self.assertRaises(KeyError):
            self.device.get_attribute("nonexistent_attribute")

    def test_get_supported_features(self):
        """Test get_supported_features returns the supported_features attribute."""
        self.device.device_attributes["supported_features"] = 47
        self.assertEqual(self.device.get_supported_features(), 47)

    def test_is_unavailable(self):
        """Test is_unavailable returns True only when state is 'unavailable'."""
        self.assertFalse(self.device.is_unavailable())
        self.device.device_state = "unavailable"
        self.assertTrue(self.device.is_unavailable())

    def test_turn_on_calls_connector(self):
        """Test turn_on delegates to connector.turn_on with device_id and type."""
        result = self.device.turn_on()
        self.assertEqual(result["state"], "on")

    def test_turn_off_calls_connector(self):
        """Test turn_off delegates to connector.turn_off with device_id and type."""
        result = self.device.turn_off()
        self.assertEqual(result["state"], "off")

    def test_call_function_delegates_to_connector(self):
        """Test call_function passes through to connector.call_function."""
        result = self.device.call_function("test_function", {"arg": "value"})
        self.assertEqual(result["result"], "success")

    def test_update_device_refreshes_all_properties(self):
        """Test update_device fetches fresh state and updates all device properties."""
        self.connector._device_states["light.test_device"] = {
            "state": "off",
            "attributes": {
                "brightness": 128,
                "friendly_name": "Updated Name",
                "icon": "mdi:updated",
            },
        }
        self.device.update_device()
        self.assertEqual(self.device.device_state, "off")
        self.assertEqual(self.device.device_attributes["brightness"], 128)
        self.assertEqual(self.device.device_name, "Updated Name")
        self.assertEqual(self.device.device_icon, "mdi:updated")

    def test_set_device_attribute_updates_via_connector(self):
        """Test set_device_attribute persists attribute change through connector."""
        self.connector._device_states["light.test_device"] = {
            "state": "on",
            "attributes": {"brightness": 255},
        }
        self.device.set_device_attribute("light.test_device", "brightness", 128)
        state = self.connector._device_states.get("light.test_device")
        self.assertEqual(state["attributes"]["brightness"], 128)

    def test_poll_updates_state_from_connector(self):
        """Test poll fetches current state from connector."""
        self.connector._device_states["light.test_device"] = {
            "state": "off",
            "attributes": {"brightness": 100},
        }
        self.device.poll()
        self.assertEqual(self.device.device_state, "off")
        self.assertEqual(self.device.device_attributes["brightness"], 100)

    def test_poll_handles_unavailable_string_state(self):
        """Test poll logs warning when connector returns 'unavailable' string."""
        self.connector.get_device_state = Mock(return_value="unavailable")
        with patch("skill_homeassistant.ha_client.logic.device.LOG") as mock_log:
            self.device.poll()
            mock_log.warning.assert_called()

    def test_poll_handles_unexpected_non_dict_state(self):
        """Test poll logs error when connector returns unexpected non-dict value."""
        self.connector.get_device_state = Mock(return_value="unexpected_string")
        with patch("skill_homeassistant.ha_client.logic.device.LOG") as mock_log:
            self.device.poll()
            mock_log.error.assert_called()

    def test_poll_handles_none_state_gracefully(self):
        """Test poll doesn't crash when connector returns None."""
        self.connector.get_device_state = Mock(return_value=None)
        # Should not raise an exception
        self.device.poll()

    def test_get_device_display_model_structure(self):
        """Test get_device_display_model returns expected dict structure for UI."""
        model = self.device.get_device_display_model()
        self.assertEqual(model["id"], "light.test_device")
        self.assertEqual(model["name"], "Test Device")
        self.assertEqual(model["type"], "light")
        self.assertEqual(model["host"], "http://fake.homeassistant.local")
        self.assertIn("state", model)
        self.assertIn("attributes", model)


class TestHomeAssistantLight(unittest.TestCase):
    """Tests for HomeAssistantLight - focusing on color/brightness logic."""

    def setUp(self):
        self.connector = FakeConnector()
        self.light = HomeAssistantLight(
            connector=self.connector,
            device_id="light.test_light",
            device_icon="mdi:lightbulb",
            device_name="Test Light",
            device_state="on",
            device_attributes={
                "brightness": 200,
                "rgb_color": [255, 100, 50],
            },
        )

    def test_get_brightness_returns_value_or_zero(self):
        """Test get_brightness returns 0 when attribute missing (not KeyError)."""
        self.assertEqual(self.light.get_brightness(), 200)
        self.light.device_attributes = {}
        self.assertEqual(self.light.get_brightness(), 0)

    def test_get_spoken_color_returns_name_for_known_rgb(self):
        """Test get_spoken_color uses webcolors to convert known RGB to name."""
        self.light.device_attributes["rgb_color"] = [255, 0, 0]
        self.assertEqual(self.light.get_spoken_color(), "red")

    def test_get_spoken_color_returns_rgb_string_for_unknown_color(self):
        """Test get_spoken_color returns descriptive string for non-standard RGB."""
        self.light.device_attributes["rgb_color"] = [123, 45, 67]
        result = self.light.get_spoken_color()
        self.assertIn("RGB code", result)
        self.assertIn("123", result)
        self.assertIn("45", result)
        self.assertIn("67", result)

    def test_set_color_converts_name_to_rgb(self):
        """Test set_color converts color name to RGB using webcolors."""
        with patch.object(self.light, "set_rgb_color") as mock_set_rgb:
            with patch.object(self.light, "update_device"):
                self.light.set_color("blue")
                mock_set_rgb.assert_called_with([0, 0, 255])

    def test_increase_brightness_uses_positive_step(self):
        """Test increase_brightness sends positive brightness_step_pct."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.increase_brightness(15)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": 15})

    def test_decrease_brightness_uses_negative_step(self):
        """Test decrease_brightness sends negative brightness_step_pct."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.decrease_brightness(15)
                mock_call.assert_called_with("turn_on", {"brightness_step_pct": -15})

    def test_light_attribute_defaults(self):
        """Test all light attribute getters have sensible defaults when missing."""
        self.light.device_attributes = {}
        
        # These should not raise and should return defaults
        self.assertEqual(self.light.get_brightness(), 0)
        self.assertEqual(self.light.get_color_mode(), "unknown")
        self.assertEqual(self.light.get_color_temp(), 0)
        self.assertEqual(self.light.get_effect(), "none")
        self.assertEqual(self.light.get_effect_list(), [])
        self.assertEqual(self.light.get_hs_color(), [0, 0])
        self.assertEqual(self.light.get_max_mireds(), 0)
        self.assertEqual(self.light.get_min_mireds(), 0)
        self.assertEqual(self.light.get_rgb_color(), [0, 0, 0])
        self.assertEqual(self.light.get_supported_color_modes(), [])
        self.assertEqual(self.light.get_xy_color(), [0, 0])

    def test_set_brightness(self):
        """Test set_brightness calls turn_on with brightness arg."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_brightness(128)
                mock_call.assert_called_with("turn_on", {"brightness": 128})

    def test_set_color_mode(self):
        """Test set_color_mode calls connector with color_mode."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_color_mode("rgb")
                mock_call.assert_called_with("set_color_mode", {"color_mode": "rgb"})

    def test_set_color_temp(self):
        """Test set_color_temp calls connector with color_temp."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_color_temp(400)
                mock_call.assert_called_with("set_color_temp", {"color_temp": 400})

    def test_set_effect(self):
        """Test set_effect calls connector with effect."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_effect("rainbow")
                mock_call.assert_called_with("set_effect", {"effect": "rainbow"})

    def test_set_hs_color(self):
        """Test set_hs_color calls connector with hs_color."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_hs_color([120, 80])
                mock_call.assert_called_with("set_hs_color", {"hs_color": [120, 80]})

    def test_set_rgb_color(self):
        """Test set_rgb_color calls turn_on with rgb_color."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_rgb_color([100, 150, 200])
                mock_call.assert_called_with("turn_on", {"rgb_color": [100, 150, 200]})

    def test_set_xy_color(self):
        """Test set_xy_color calls connector with xy_color."""
        with patch.object(self.light, "call_function") as mock_call:
            with patch.object(self.light, "update_device"):
                self.light.set_xy_color([0.5, 0.6])
                mock_call.assert_called_with("set_xy_color", {"xy_color": [0.5, 0.6]})


class TestHomeAssistantSensor(unittest.TestCase):
    """Tests for HomeAssistantSensor attribute defaults."""

    def setUp(self):
        self.connector = FakeConnector()
        self.sensor = HomeAssistantSensor(
            connector=self.connector,
            device_id="sensor.temperature",
            device_icon="mdi:thermometer",
            device_name="Temperature Sensor",
            device_state="72",
            device_attributes={},
        )

    def test_sensor_attribute_defaults(self):
        """Test all sensor attribute getters return 'unknown' when missing."""
        self.assertEqual(self.sensor.get_device_class(), "unknown")
        self.assertEqual(self.sensor.get_last_reset(), "unknown")
        self.assertEqual(self.sensor.get_native_value(), "unknown")
        self.assertEqual(self.sensor.get_native_unit_of_measurement(), "unknown")
        self.assertEqual(self.sensor.get_state_class(), "unknown")
        self.assertEqual(self.sensor.get_suggested_unit_of_measurement(), "unknown")


class TestHomeAssistantBinarySensor(unittest.TestCase):
    """Tests for HomeAssistantBinarySensor."""

    def test_binary_sensor_device_class_default(self):
        """Test get_device_class returns 'unknown' when not set."""
        connector = FakeConnector()
        binary_sensor = HomeAssistantBinarySensor(
            connector=connector,
            device_id="binary_sensor.motion",
            device_icon="mdi:motion-sensor",
            device_name="Motion Sensor",
            device_state="off",
            device_attributes={},
        )
        self.assertEqual(binary_sensor.get_device_class(), "unknown")


class TestHomeAssistantCover(unittest.TestCase):
    """Tests for HomeAssistantCover state methods."""

    def setUp(self):
        self.connector = FakeConnector()
        self.cover = HomeAssistantCover(
            connector=self.connector,
            device_id="cover.garage",
            device_icon="mdi:garage",
            device_name="Garage Door",
            device_state="closed",
            device_attributes={"current_position": 0},
        )

    def test_cover_calls_correct_functions(self):
        """Test cover methods call connector with correct function names."""
        with patch.object(self.cover, "call_function") as mock_call:
            self.cover.open()
            mock_call.assert_called_with("open")
            
            self.cover.close()
            mock_call.assert_called_with("close")
            
            self.cover.stop()
            mock_call.assert_called_with("stop")

    def test_set_position_includes_position_arg(self):
        """Test set_position passes position to connector."""
        with patch.object(self.cover, "call_function") as mock_call:
            with patch.object(self.cover, "update_device"):
                self.cover.set_position(50)
                mock_call.assert_called_with("set_position", {"position": 50})

    def test_cover_state_checks(self):
        """Test cover state helper methods return correct boolean for each state."""
        self.cover.device_state = "opening"
        self.assertTrue(self.cover.is_opening())
        self.assertFalse(self.cover.is_closing())
        
        self.cover.device_state = "closing"
        self.assertTrue(self.cover.is_closing())
        self.assertFalse(self.cover.is_opening())
        
        self.cover.device_state = "open"
        self.assertTrue(self.cover.is_open())
        self.assertFalse(self.cover.is_closed())
        
        self.cover.device_state = "closed"
        self.assertTrue(self.cover.is_closed())
        self.assertFalse(self.cover.is_open())

    def test_get_position(self):
        """Test get_position returns current_position attribute."""
        self.assertEqual(self.cover.get_position(), 0)
        self.cover.device_attributes["current_position"] = 75
        self.assertEqual(self.cover.get_position(), 75)


class TestHomeAssistantMediaPlayer(unittest.TestCase):
    """Tests for HomeAssistantMediaPlayer - testing missing attribute handling."""

    def setUp(self):
        self.connector = FakeConnector()
        self.media_player = HomeAssistantMediaPlayer(
            connector=self.connector,
            device_id="media_player.living_room",
            device_icon="mdi:speaker",
            device_name="Living Room Speaker",
            device_state="playing",
            device_attributes={},  # Empty - testing missing attributes
        )

    def test_media_player_getters_raise_keyerror_when_missing(self):
        """Test media player getters raise KeyError when attributes missing.
        
        Unlike Light, MediaPlayer uses direct dict access without .get() defaults.
        This documents that behavior - callers must handle KeyError.
        """
        with self.assertRaises(KeyError):
            self.media_player.get_media_title()
        
        with self.assertRaises(KeyError):
            self.media_player.get_volume_level()


class TestHomeAssistantClimate(unittest.TestCase):
    """Tests for HomeAssistantClimate setter methods."""

    def setUp(self):
        self.connector = FakeConnector()
        self.climate = HomeAssistantClimate(
            connector=self.connector,
            device_id="climate.thermostat",
            device_icon="mdi:thermostat",
            device_name="Thermostat",
            device_state="heat",
            device_attributes={},
        )

    def test_climate_setters_call_correct_functions(self):
        """Test climate setters call connector with correct function names and args."""
        test_cases = [
            ("set_temperature", {"temperature": 74}),
            ("set_hvac_mode", {"hvac_mode": "cool"}),
            ("set_fan_mode", {"fan_mode": "high"}),
            ("set_swing_mode", {"swing_mode": "vertical"}),
            ("set_preset_mode", {"preset_mode": "away"}),
            ("set_aux_heat", {"aux_heat": True}),
            ("set_humidity", {"humidity": 55}),
            ("set_target_humidity", {"target_humidity": 60}),
            ("set_target_temp_low", {"target_temp_low": 62}),
            ("set_target_temp_high", {"target_temp_high": 78}),
        ]
        
        for method_name, expected_args in test_cases:
            with patch.object(self.climate, "call_function") as mock_call:
                with patch.object(self.climate, "update_device"):
                    method = getattr(self.climate, method_name)
                    arg_value = list(expected_args.values())[0]
                    method(arg_value)
                    mock_call.assert_called_with(method_name, expected_args)


class TestHomeAssistantVacuum(unittest.TestCase):
    """Tests for HomeAssistantVacuum methods."""

    def setUp(self):
        self.connector = FakeConnector()
        self.vacuum = HomeAssistantVacuum(
            connector=self.connector,
            device_id="vacuum.roomba",
            device_icon="mdi:robot-vacuum",
            device_name="Roomba",
            device_state="docked",
            device_attributes={
                "battery_level": 100,
                "fan_speed": "turbo",
                "fan_speed_list": ["quiet", "normal", "turbo"],
                "status": "idle",
            },
        )

    def test_vacuum_control_methods(self):
        """Test vacuum control methods call correct functions."""
        with patch.object(self.vacuum, "call_function") as mock_call:
            self.vacuum.start()
            mock_call.assert_called_with("start")
            
            self.vacuum.pause()
            mock_call.assert_called_with("pause")
            
            self.vacuum.stop()
            mock_call.assert_called_with("stop")
            
            self.vacuum.return_to_base()
            mock_call.assert_called_with("return_to_base")

    def test_send_command_passes_command_and_params(self):
        """Test send_command forwards command name and params to connector."""
        with patch.object(self.vacuum, "call_function") as mock_call:
            self.vacuum.send_command("clean_segment", {"segment_id": 1})
            mock_call.assert_called_with(
                "send_command", 
                {"command": "clean_segment", "params": {"segment_id": 1}}
            )

    def test_set_fan_speed_uses_set_device_attribute(self):
        """Test set_fan_speed updates attribute rather than calling function."""
        with patch.object(self.vacuum, "set_device_attribute") as mock_set:
            with patch.object(self.vacuum, "update_device"):
                self.vacuum.set_fan_speed("quiet")
                mock_set.assert_called_with("vacuum.roomba", "fan_speed", "quiet")


class TestHomeAssistantScene(unittest.TestCase):
    """Tests for HomeAssistantScene safety behavior."""

    def test_turn_off_logs_warning_and_returns_none(self):
        """Test scene turn_off logs warning and does nothing (scenes can't be turned off)."""
        connector = FakeConnector()
        connector.turn_off = Mock()  # Track if it gets called
        scene = HomeAssistantScene(
            connector=connector,
            device_id="scene.movie_time",
            device_icon="mdi:movie",
            device_name="Movie Time",
            device_state="on",
            device_attributes={},
        )
        
        with patch("skill_homeassistant.ha_client.logic.device.LOG") as mock_log:
            result = scene.turn_off()
            mock_log.warning.assert_called()
            self.assertIsNone(result)
            # Verify connector.turn_off was NOT called (scene overrides to do nothing)
            connector.turn_off.assert_not_called()


class TestHomeAssistantAutomation(unittest.TestCase):
    """Tests for HomeAssistantAutomation safety behavior."""

    def test_turn_off_logs_warning_and_returns_none(self):
        """Test automation turn_off logs warning (would disable, not just deactivate)."""
        connector = FakeConnector()
        connector.turn_off = Mock()  # Track if it gets called
        automation = HomeAssistantAutomation(
            connector=connector,
            device_id="automation.morning_routine",
            device_icon="mdi:robot",
            device_name="Morning Routine",
            device_state="on",
            device_attributes={},
        )
        
        with patch("skill_homeassistant.ha_client.logic.device.LOG") as mock_log:
            result = automation.turn_off()
            mock_log.warning.assert_called()
            self.assertIsNone(result)
            # Verify connector.turn_off was NOT called (automation overrides to do nothing)
            connector.turn_off.assert_not_called()


if __name__ == "__main__":
    unittest.main()
