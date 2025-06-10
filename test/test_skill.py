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
