# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring,logging-fstring-interpolation
from typing import Optional
from ovos_bus_client import Message
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill

from skill_homeassistant.ha_client import HomeAssistantClient


class HomeAssistantSkill(OVOSSkill):
    """Unified Home Assistant skill for OpenVoiceOS or Neon.AI."""

    _settings_defaults = {"silent_entities": set(), "disable_intents": False, "timeout": 5, "verify_ssl": True}
    _intents_enabled = True
    connected_intents = (
        "sensor.intent",
        "turn.on.intent",
        "turn.off.intent",
        "stop.intent",
        "lights.get.brightness.intent",
        "lights.set.brightness.intent",
        "lights.increase.brightness.intent",
        "lights.decrease.brightness.intent",
        "lights.get.color.intent",
        "lights.set.color.intent",
        "assist.intent",
    )

    def __init__(self, *args, bus=None, skill_id="", **kwargs):
        super().__init__(*args, bus=bus, skill_id=skill_id, **kwargs)

    @property
    def verify_ssl(self):
        """Return whether to verify SSL connections."""
        return self._get_setting("verify_ssl")

    @property
    def silent_entities(self):
        return set(self._get_setting("silent_entities"))

    @silent_entities.setter
    def silent_entities(self, value):
        self._set_setting("silent_entities", value)

    @property
    def disable_intents(self):
        setting = self._get_setting("disable_intents")
        self._handle_connection_state(setting)
        return setting

    @disable_intents.setter
    def disable_intents(self, value):
        self._set_setting("disable_intents", value)
        self._handle_connection_state(value)

    def initialize(self):
        self.client_config = self._get_client_config()  # pylint: disable=attribute-defined-outside-init
        self.ha_client = HomeAssistantClient(  # pylint: disable=attribute-defined-outside-init
            config=self.client_config, bus=self.bus
        )
        if self.disable_intents:
            self.log.info("User has indicated they do not want to use Home Assistant intents. Disabling.")
            self.disable_ha_intents()

    def _get_client_config(self) -> dict:
        if self.settings.get("host") and self.settings.get("api_key"):
            return {**self._settings_defaults, **self.settings}
        phal_config = self.config_core.get("PHAL", {}).get("ovos-PHAL-plugin-homeassistant")
        if phal_config:
            return {**self._settings_defaults, **phal_config, **self.settings}
        self.log.error(
            "No Home Assistant config found! Please set host and api_key "
            f"in the skill settings at {self.settings_path}."
        )
        return self._settings_defaults

    def _get_setting(self, setting_name):
        """Helper method to get a setting with its default value."""
        return self.settings.get(setting_name, self._settings_defaults[setting_name])

    def _set_setting(self, setting_name, value):
        """Helper method to set a setting."""
        self.settings[setting_name] = value

    def _handle_connection_state(self, disable_intents: bool):
        if self._intents_enabled and disable_intents is True:
            self.log.info(
                "Disabling Home Assistant intents by user request. To re-enable, set disable_intents to False."
            )
            self.disable_ha_intents()
        if not self._intents_enabled and disable_intents is False:
            self.log.info("Enabling Home Assistant intents by user request. To disable, set disable_intents to True.")
            self.enable_ha_intents()

    def enable_ha_intents(self):
        for intent in self.connected_intents:
            success = self.enable_intent(intent)
            if not success:
                self.log.error(f"Error registering intent: {intent}")
            else:
                self.log.info(f"Successfully registered intent: {intent}")
        self._intents_enabled = True

    def disable_ha_intents(self):
        for intent in self.connected_intents:
            self.intent_service.remove_intent(intent)
            try:
                assert self.intent_service.intent_is_detached(intent) is True
            except AssertionError:
                self.log.error(f"Error disabling intent: {intent}")
        self._intents_enabled = False

    # Handlers
    @intent_handler("get.all.devices.intent")
    def handle_rebuild_device_list(self, _: Message):
        self.ha_client.build_devices()
        self.speak_dialog("acknowledge")

    @intent_handler("enable.intent")
    def handle_enable_intent(self, _: Message):
        self.settings["disable_intents"] = False
        self.speak_dialog("enable")
        self.enable_ha_intents()

    @intent_handler("disable.intent")
    def handle_disable_intent(self, _: Message):
        self.settings["disable_intents"] = True
        self.speak_dialog("disable")
        self.disable_ha_intents()

    @intent_handler("sensor.intent")  # pragma: no cover
    def get_device_intent(self, message: Message):
        """Handle intent to get a single device status from Home Assistant."""
        self.log.info(message.data)
        device = message.data.get("entity", "")
        if device:
            device_data = self.ha_client.handle_get_device(Message("", {"device": device}))
            if device_data:
                self.speak_dialog(
                    "device.status",
                    data={
                        "device": device_data.get("attributes", {}).get("friendly_name", device_data.get("name")),
                        "type": device_data.get("type"),
                        "state": device_data.get("state"),
                    },
                )
            else:
                self.speak_dialog("device.not.found", {"device": device})
            self.log.info(f"Trying to get device status for {device}")
        else:
            self.speak_dialog("no.parsed.device")

    def _get_device_from_message(self, message: Message, require_device: bool = True) -> Optional[str]:
        """Extract and validate device from message data.

        Args:
            message: The message containing device data
            require_device: If True, speak no.parsed.device dialog when device is missing

        Returns:
            The device name or None if not found/invalid
        """
        device = message.data.get("entity", "")
        if not device and require_device:
            self.speak_dialog("no.parsed.device")
            return None
        return device or None

    def _handle_device_response(
        self, response: Optional[dict], device: str, success_dialog: str, success_data: Optional[dict] = None
    ) -> bool:
        """Handle standard device operation response.

        Args:
            response: The response from ha_client
            device: The device name
            success_dialog: Dialog to speak on success
            success_data: Additional data to pass to success dialog

        Returns:
            True if handled successfully, False otherwise
        """
        if not response or response.get("response"):
            self.speak_dialog("device.not.found", {"device": device})
            return False

        if device not in self.silent_entities:
            dialog_data = {"device": device}
            if success_data:
                dialog_data.update(success_data)
            self.speak_dialog(success_dialog, dialog_data)

        return True

    @intent_handler("turn.on.intent")  # pragma: no cover
    def handle_turn_on_intent(self, message: Message) -> None:
        """Handle turn on intent."""
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_turn_on(Message("", {"device": device}))
            if not self._handle_device_response(response, device, "device.turned.on"):
                self.log.info(f"Trying to turn on device {device}")

    @intent_handler("turn.off.intent")  # pragma: no cover
    @intent_handler("stop.intent")  # pragma: no cover
    def handle_turn_off_intent(self, message: Message) -> None:
        """Handle turn off intent."""
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_turn_off(Message("", {"device": device}))
            if not self._handle_device_response(response, device, "device.turned.off"):
                self.log.info(f"Trying to turn off device {device}")

    @intent_handler("lights.get.brightness.intent")  # pragma: no cover
    def handle_get_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_get_light_brightness(Message("", {"device": device}))
            if response and not response.get("response"):
                if brightness := response.get("brightness"):
                    self.speak_dialog("lights.current.brightness", data={"brightness": brightness, "device": device})
                    return
            self.speak_dialog("lights.status.not.available", data={"device": device})

    @intent_handler("lights.set.brightness.intent")  # pragma: no cover
    def handle_set_brightness_intent(self, message: Message):
        self.log.info(message.data)
        device = self._get_device_from_message(message)
        brightness = message.data.get("brightness")

        if device and brightness:
            response = self.ha_client.handle_set_light_brightness(
                Message(
                    "", {"device": device, "brightness": self._get_ha_value_from_percentage_brightness(brightness)}
                )
            )
            if self._handle_device_response(
                response,
                device,
                "lights.current.brightness",
                {"brightness": response.get("brightness")} if response else None,
            ):
                return
            self.log.info(f"Trying to set brightness of {brightness} for {device}")

    @intent_handler("lights.increase.brightness.intent")  # pragma: no cover
    def handle_increase_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_increase_light_brightness(Message("", {"device": device}))
            if self._handle_device_response(
                response,
                device,
                "lights.current.brightness",
                {"brightness": response.get("brightness")} if response else None,
            ):
                return
            self.log.info(f"Trying to increase brightness for {device}")

    @intent_handler("lights.decrease.brightness.intent")  # pragma: no cover
    def handle_decrease_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_decrease_light_brightness(Message("", {"device": device}))
            if self._handle_device_response(
                response,
                device,
                "lights.current.brightness",
                {"brightness": response.get("brightness")} if response else None,
            ):
                return
            self.log.info(f"Trying to decrease brightness for {device}")

    @intent_handler("lights.get.color.intent")  # pragma: no cover
    def handle_get_color_intent(self, message: Message):
        self.log.info(message.data)
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_get_light_color(Message("", {"device": device}))
            if response and not response.get("response"):
                if color := response.get("color"):
                    self.speak_dialog("lights.current.color", data={"color": color, "device": device})
                    return
            self.speak_dialog("lights.status.not.available", data={"device": device})

    @intent_handler("lights.set.color.intent")  # pragma: no cover
    def handle_set_color_intent(self, message: Message):
        self.log.info(message.data)
        device = self._get_device_from_message(message)
        color = message.data.get("color")

        if not color:
            self.speak_dialog("no.parsed.color")
            return

        if device:
            response = self.ha_client.handle_set_light_color(Message("", {"device": device, "color": color}))
            if self._handle_device_response(
                response, device, "lights.current.color", {"color": response.get("color")} if response else None
            ):
                return
            self.log.info(f"Trying to set color of {device}")

    @intent_handler("assist.intent")  # pragma: no cover
    def handle_assist_intent(self, message: Message):
        """Handle passthrough to Home Assistant's Assist API."""
        command = message.data.get("command")
        if command:
            self.ha_client.handle_assist_message(Message("", {"command": command}))
            self.speak_dialog("assist")
            self.log.info(f"Trying to pass message to Home Assistant's Assist API:\n{command}")
        else:
            self.speak_dialog("assist.not.understood")

    def _get_ha_value_from_percentage_brightness(self, brightness):
        return round(int(brightness)) / 100 * 255


if __name__ == "__main__":
    # from ovos_utils.messagebus import FakeBus
    from ovos_bus_client.client import MessageBusClient  # pylint: disable=ungrouped-imports

    bus = MessageBusClient()
    bus.run_in_thread()
    skill = HomeAssistantSkill(bus=bus, skill_id="skill_homeassistant.test")
    skill.handle_turn_on_intent(Message("", {"entity": "nerd art"}))
    skill.handle_turn_off_intent(Message("", {"entity": "nerd art"}))
    skill.handle_turn_on_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.handle_turn_off_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.handle_get_brightness_intent(Message("", {"entity": "master bedroom light"}))
    skill.handle_get_brightness_intent(Message("", {"entity": ""}))
    skill.handle_get_brightness_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.handle_set_brightness_intent(Message("", {"entity": "master bedroom light", "brightness": 100}))
    skill.handle_set_brightness_intent(Message("", {"entity": "", "brightness": 100}))
    skill.handle_set_brightness_intent(Message("", {"entity": "FAKE DEVICE", "brightness": 100}))
    skill.handle_decrease_brightness_intent(Message("", {"entity": "office light"}))
    skill.handle_decrease_brightness_intent(Message("", {"entity": ""}))
    skill.handle_decrease_brightness_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.handle_increase_brightness_intent(Message("", {"entity": "office light"}))
    skill.handle_increase_brightness_intent(Message("", {"entity": ""}))
    skill.handle_increase_brightness_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.get_device_intent(Message("", {"entity": "kitchen light"}))
    skill.handle_get_color_intent(Message("", {"entity": "temperature light"}))
    skill.handle_get_color_intent(Message("", {"entity": ""}))
    skill.handle_get_color_intent(Message("", {"entity": "FAKE DEVICE"}))
    skill.handle_set_color_intent(Message("", {"entity": "temperature light", "color": "yellow"}))
    skill.handle_set_color_intent(Message("", {"entity": "", "color": "yellow"}))
    skill.handle_set_color_intent(Message("", {"entity": "FAKE DEVICE", "color": "yellow"}))
    skill.handle_assist_intent(Message("", {"command": "turn on nerd art"}))
    skill.handle_assist_intent(Message("", {"command": "turn off nerd art"}))
    print("BREAK")
