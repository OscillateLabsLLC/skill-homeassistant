# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring
# pylint: disable=invalid-name,protected-access
import unittest

from mock import Mock, patch
from ovos_bus_client import Message
from ovos_utils.messagebus import FakeBus
from padacioso import IntentContainer

from skill_homeassistant import HomeAssistantSkill

BRANCH = "main"
REPO = "skill-homeassistant"
AUTHOR = "oscillatelabsllc"
url = f"https://github.com/{AUTHOR}/{REPO}@{BRANCH}"


class TestSkillIntentMatching(unittest.TestCase):
    skill = HomeAssistantSkill(settings={"host": "http://homeassistant.local:8123", "api_key": "test"})
    ha_intents = IntentContainer()

    bus = FakeBus()
    test_skill_id = "test_skill.test"

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill._startup(cls.bus, cls.test_skill_id)

    @patch("requests.get")
    def test_get_all_devices(self, mock_get):
        self.skill.speak_dialog = Mock()
        self.skill.handle_rebuild_device_list(Message(msg_type="test"))
        self.skill.speak_dialog.assert_called_once_with("acknowledge")

    @patch("requests.get")
    def test_verify_ssl_config_default(self, mock_get):
        self.assertTrue(self.skill.verify_ssl)
        self.assertTrue(self.skill.ha_client.config.get("verify_ssl"))


def test_verify_ssl_config_nondefault():
    skill = HomeAssistantSkill(
        settings={"host": "http://homeassistant.local:8123", "api_key": "TEST_API_KEY", "verify_ssl": False}
    )
    skill._startup(FakeBus(), "test_skill.ssl_test")
    assert skill.verify_ssl == False
    assert skill.ha_client.config.get("verify_ssl") == False


class TestSkillConfigFallback(unittest.TestCase):
    """Test the config fallback chain in _get_client_config."""

    def test_get_client_config_from_settings(self):
        """When settings have host and api_key, use settings."""
        skill = HomeAssistantSkill(
            settings={"host": "http://ha.local", "api_key": "my_key", "timeout": 5}
        )
        skill._startup(FakeBus(), "test_skill.config_settings")
        config = skill._get_client_config()
        self.assertEqual(config["host"], "http://ha.local")
        self.assertEqual(config["api_key"], "my_key")
        self.assertEqual(config["timeout"], 5)

    def test_get_client_config_no_config_returns_defaults(self):
        """When no config is found anywhere, return defaults and log error."""
        skill = HomeAssistantSkill(settings={})
        skill.config_core = {}  # No PHAL config
        skill._startup(FakeBus(), "test_skill.config_none")
        config = skill._get_client_config()
        # Should return defaults
        self.assertEqual(config["host"], "")
        self.assertEqual(config["api_key"], "")


class TestSkillDeviceParsing(unittest.TestCase):
    """Test _get_device_from_message logic."""

    @classmethod
    def setUpClass(cls):
        cls.skill = HomeAssistantSkill(
            settings={"host": "http://ha.local", "api_key": "test"}
        )
        cls.skill._startup(FakeBus(), "test_skill.device_parsing")

    def test_get_device_from_message_with_entity(self):
        """When message has entity, return it."""
        message = Message("test", {"entity": "living room light"})
        result = self.skill._get_device_from_message(message)
        self.assertEqual(result, "living room light")

    def test_get_device_from_message_no_entity_require_true(self):
        """When no entity and require_device=True, speak dialog and return None."""
        message = Message("test", {})
        self.skill.speak_dialog = Mock()
        result = self.skill._get_device_from_message(message, require_device=True)
        self.assertIsNone(result)
        self.skill.speak_dialog.assert_called_once_with("no.parsed.device")

    def test_get_device_from_message_no_entity_require_false(self):
        """When no entity and require_device=False, return None without speaking."""
        message = Message("test", {})
        self.skill.speak_dialog = Mock()
        result = self.skill._get_device_from_message(message, require_device=False)
        self.assertIsNone(result)
        self.skill.speak_dialog.assert_not_called()


class TestSkillResponseHandling(unittest.TestCase):
    """Test _handle_device_response logic."""

    @classmethod
    def setUpClass(cls):
        cls.skill = HomeAssistantSkill(
            settings={"host": "http://ha.local", "api_key": "test", "silent_entities": []}
        )
        cls.skill._startup(FakeBus(), "test_skill.response_handling")

    def setUp(self):
        self.skill.speak_dialog = Mock()
        self.skill.gui = Mock()
        self.skill.settings["silent_entities"] = []

    def test_handle_device_response_none_response(self):
        """When response is None, speak device.not.found and return False."""
        result = self.skill._handle_device_response(
            None, "kitchen light", "device.turned.on"
        )
        self.assertFalse(result)
        self.skill.speak_dialog.assert_called_with("device.not.found", {"device": "kitchen light"})

    def test_handle_device_response_error_in_response(self):
        """When response has 'response' key (error), speak device.not.found."""
        result = self.skill._handle_device_response(
            {"response": "Device not found"}, "kitchen light", "device.turned.on"
        )
        self.assertFalse(result)
        self.skill.speak_dialog.assert_called_with("device.not.found", {"device": "kitchen light"})

    def test_handle_device_response_success_speaks_dialog(self):
        """On success with device not in silent_entities, speak success dialog."""
        result = self.skill._handle_device_response(
            {"device": "kitchen light"}, "kitchen light", "device.turned.on",
            success_message="Turned on!"
        )
        self.assertTrue(result)
        self.skill.speak_dialog.assert_called_with("device.turned.on", {"device": "kitchen light"})
        self.skill.gui.show_text.assert_called_with("kitchen light: Turned on!")

    def test_handle_device_response_success_with_data(self):
        """On success, success_data is merged into dialog data."""
        result = self.skill._handle_device_response(
            {"device": "thermostat"}, "thermostat", "temperature.set",
            success_data={"temperature": "72"},
            success_message="Temperature set!"
        )
        self.assertTrue(result)
        self.skill.speak_dialog.assert_called_with(
            "temperature.set", {"device": "thermostat", "temperature": "72"}
        )

    def test_handle_device_response_silent_entity_no_speak(self):
        """When device is in silent_entities, don't speak but do show GUI."""
        self.skill.settings["silent_entities"] = ["kitchen light"]
        result = self.skill._handle_device_response(
            {"device": "kitchen light"}, "kitchen light", "device.turned.on",
            success_message="Turned on!"
        )
        self.assertTrue(result)
        # speak_dialog should NOT be called for success (may be called for setup)
        # Actually, we need to check it wasn't called with the success dialog
        for call in self.skill.speak_dialog.call_args_list:
            self.assertNotEqual(call[0][0], "device.turned.on")
        # But GUI should still be shown
        self.skill.gui.show_text.assert_called_with("kitchen light: Turned on!")


class TestSkillSilentEntities(unittest.TestCase):
    """Test silent_entities property."""

    def test_silent_entities_returns_set(self):
        """silent_entities property should return a set."""
        skill = HomeAssistantSkill(
            settings={"host": "http://ha.local", "api_key": "test", "silent_entities": ["light1", "light2"]}
        )
        skill._startup(FakeBus(), "test_skill.silent_entities")
        result = skill.silent_entities
        self.assertIsInstance(result, set)
        self.assertEqual(result, {"light1", "light2"})

    def test_silent_entities_setter(self):
        """silent_entities setter should update settings."""
        skill = HomeAssistantSkill(
            settings={"host": "http://ha.local", "api_key": "test", "silent_entities": []}
        )
        skill._startup(FakeBus(), "test_skill.silent_entities_set")
        skill.silent_entities = ["new_light"]
        self.assertEqual(skill.settings["silent_entities"], ["new_light"])
