"""Guardrails for intent file size and matching.

Padatious expands every (a|b|c) group into separate training samples and uses
other intents' samples as negatives, so training cost grows superlinearly with
total sample count. These tests keep the expansion budget from creeping back up
(same approach as skill-musicassistant#30) and verify the kept phrasings still
match their intents.
"""

from pathlib import Path

import pytest
from ovos_utils.bracket_expansion import expand_template
from padacioso import IntentContainer

LOCALE_DIR = Path(__file__).parent.parent / "skill_homeassistant" / "locale"

# Hard ceilings - raise these only with a measured justification
MAX_SAMPLES_PER_LOCALE = 600
MAX_SAMPLES_PER_FILE = 200

# pl-pl currently expands to ~8,815 samples and needs a Polish speaker to
# prune it - exempted until issue #52 is resolved
BUDGETED_LOCALES = ["en-us", "es-es", "fr-fr", "da-dk", "sv-se"]


def _intent_lines(path: Path):
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _expansion_counts(lang: str):
    intent_dir = LOCALE_DIR / lang / "intents"
    return {
        f.name: sum(len(expand_template(line)) for line in _intent_lines(f))
        for f in sorted(intent_dir.glob("*.intent"))
    }


class TestExpansionBudget:
    @pytest.mark.parametrize("lang", BUDGETED_LOCALES)
    def test_locale_total_under_budget(self, lang):
        counts = _expansion_counts(lang)
        total = sum(counts.values())
        assert total <= MAX_SAMPLES_PER_LOCALE, (
            f"{lang} intents expand to {total} Padatious samples "
            f"(budget {MAX_SAMPLES_PER_LOCALE}): {counts}"
        )

    @pytest.mark.parametrize("lang", BUDGETED_LOCALES)
    def test_no_single_file_dominates(self, lang):
        for name, count in _expansion_counts(lang).items():
            assert count <= MAX_SAMPLES_PER_FILE, (
                f"{lang}/{name} expands to {count} samples (budget {MAX_SAMPLES_PER_FILE}) "
                "- prune alternation groups instead of enumerating combinations"
            )

    @pytest.mark.parametrize("lang", BUDGETED_LOCALES + ["pl-pl"])
    def test_no_glued_tokens(self, lang):
        """A bracket group directly against a word or slot ((|to){command}) trains
        glued garbage tokens like "to{command}"."""
        intent_dir = LOCALE_DIR / lang / "intents"
        for f in sorted(intent_dir.glob("*.intent")):
            for line in _intent_lines(f):
                for sample in expand_template(line):
                    for token in sample.split():
                        assert not (
                            "{" in token and not token.startswith("{")
                        ), f"{lang}/{f.name}: {line!r} trains glued token {token!r}"


class TestIntentMatching:
    """Exact-pattern matching for the phrasings the intent files keep.

    Uses padacioso (regex, deterministic). Padatious additionally generalizes
    beyond these patterns at runtime; this suite covers the guaranteed floor.
    """

    @pytest.fixture(scope="class")
    def container(self):
        container = IntentContainer()
        intent_dir = LOCALE_DIR / "en-us" / "intents"
        for f in sorted(intent_dir.glob("*.intent")):
            container.add_intent(f.stem, _intent_lines(f))
        return container

    @pytest.mark.parametrize(
        "utterance,intent",
        [
            ("turn on the kitchen light", "turn.on"),
            ("turn my lamp on", "turn.on"),
            ("can you turn on the fan please", "turn.on"),
            ("I'd like to turn on the porch light", "turn.on"),
            ("turn off the kitchen light", "turn.off"),
            ("turn my lamp off", "turn.off"),
            ("would you turn the fan off please", "turn.off"),
            ("what is the temperature of the living room sensor", "sensor"),
            ("tell me the status of the garage door", "sensor"),
            ("is the front door open", "sensor"),
            ("has the basement sensor detected moisture", "sensor"),
            ("increase the brightness of the office light", "lights.increase.brightness"),
            ("make my desk lamp brighter", "lights.increase.brightness"),
            ("decrease the brightness of the office light", "lights.decrease.brightness"),
            ("dim the bedroom light", "lights.decrease.brightness"),
            ("what is the brightness of the kitchen light", "lights.get.brightness"),
            ("what is the color of the kitchen light", "lights.get.color"),
            ("set the brightness of the office light to 50 percent", "lights.set.brightness"),
            ("change my lamp color to red", "lights.set.color"),
            ("stop the vacuum", "stop"),
            ("tell home assistant to restart the server", "assist"),
            ("Enable Home Assistant", "enable"),
            ("Disable Home Assistant", "disable"),
            ("rebuild device list", "get.all.devices"),
        ],
    )
    def test_utterance_matches_intent(self, container, utterance, intent):
        result = container.calc_intent(utterance)
        assert result.get("name") == intent, f"{utterance!r} -> {result}"

    def test_slots_extracted(self, container):
        result = container.calc_intent("set the brightness of the office light to 50")
        assert result["entities"].get("entity") == "office light"
        assert result["entities"].get("brightness") == "50"
