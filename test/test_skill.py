# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring
# pylint: disable=invalid-name,protected-access
import unittest
from os import getenv

from mock import Mock, call
from ovos_bus_client import Message
from ovos_utils.messagebus import FakeBus
from padacioso import IntentContainer
from yaml import safe_load

from skill_homeassistant import HomeAssistantSkill

BRANCH = "main"
REPO = "skill-homeassistant"
AUTHOR = "oscillatelabsllc"
url = f"https://github.com/{AUTHOR}/{REPO}@{BRANCH}"


class TestSkillIntentMatching(unittest.TestCase):
    skill = HomeAssistantSkill()

    test_intents_filename = getenv("INTENT_TEST_FILE", "test/test_intents.yaml")
    with open(test_intents_filename, encoding="utf-8") as f:
        valid_intents = safe_load(f)
    ha_intents = IntentContainer()
    for lang, intents in valid_intents.items():
        for name, utt in valid_intents[lang].items():
            if isinstance(utt[0], str):
                u = utt
            else:
                u = []
                for sentence, entity in utt[0].items():
                    if "entity" in entity[0].keys():
                        revised_intent = sentence.replace(entity[0].get("entity"), "{entity}")
                        if len(entity[0].keys()) > 1 and entity[0].get("color"):
                            revised_intent = revised_intent.replace(entity[0].get("color"), "{color}")
                        u.append(revised_intent)
                    elif "area" in entity[0].keys():
                        u.append(sentence.replace(entity[0].get("area"), "{area}"))
            ha_intents.add_intent(name, u)

    bus = FakeBus()
    test_skill_id = "test_skill.test"

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill.config_core["secondary_langs"] = list(cls.valid_intents.keys())
        cls.skill._startup(cls.bus, cls.test_skill_id)

    # def test_intents(self):
    #     for lang in self.valid_intents.keys():
    #         for intent, examples in self.valid_intents[lang].items():
    #             for utt in examples:
    #                 if isinstance(utt, str):
    #                     result = self.ha_intents.calc_intent(utt) or {}
    #                     self.assertTrue(result.get("conf", 0) >= 0.9)
    #                     self.assertEqual(result.get("name"), intent)
    #                 else:
    #                     u = list(utt.keys())[0]
    #                     result = self.ha_intents.calc_intent(u)
    #                     if len(utt[u]) > 1:
    #                         self.assertTrue(list(utt[u][1].values())[0] in u)

    def test_get_all_devices(self):
        self.skill.speak_dialog = Mock()
        self.skill.handle_rebuild_device_list(Message(msg_type="test"))
        self.skill.speak_dialog.assert_called_once_with("acknowledge")
