# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring,logging-fstring-interpolation
from typing import Optional

from ovos_bus_client import Message
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill

from skill_homeassistant.ha_client import HomeAssistantClient


class HomeAssistantSkill(OVOSSkill):
    """Unified Home Assistant skill for OpenVoiceOS or Neon.AI."""

    _settings_defaults = {
        "host": "",
        "api_key": "",
        "silent_entities": set(),
        "disable_intents": False,
        "timeout": 5,
        "verify_ssl": True,
    }
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
        self.gui.show_text("Rebuilding device list from Home Assistant")

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
        if not self.check_client_connection():
            return
        device = message.data.get("entity", "")
        if device:
            device_data = self.ha_client.handle_get_device(Message("", {"device": device}))
            if device_data:
                device_name = device_data.get("attributes", {}).get("friendly_name", device_data.get("name"))
                device_type = device_data.get("type")
                device_state = device_data.get("state")
                self.speak_dialog(
                    "device.status",
                    data={
                        "device": device_name,
                        "type": device_type,
                        "state": device_state,
                    },
                )
                self.gui.show_text(f"{device_name} ({device_type}) is {device_state}")
            else:
                self.speak_dialog("device.not.found", {"device": device})
                self.gui.show_text(f"Could not find device {device}")
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
        self,
        response: Optional[dict],
        device: str,
        success_dialog: str,
        success_data: Optional[dict] = None,
        success_message: str = "Successful operation!",
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
            self.gui.show_text(f"Could not find device {device}")
            return False

        if device not in self.silent_entities:
            dialog_data = {"device": device}
            if success_data:
                dialog_data.update(success_data)
            self.speak_dialog(success_dialog, dialog_data)

        self.gui.show_text(f"{device}: {success_message}")
        return True
    
    def check_client_connection(self):
        if not self.ha_client.instance_available:
            try:
                self.ha_client.init_configuration(self.settings)
                if not self.ha_client.instance_available:
                    raise Exception("Home Assistant instance is not available")
                return True
            except Exception as e:
                self.log.error(f"Error initializing Home Assistant client: {e}")
                self.gui.show_text("Connection to Home Assistant is not configured or unavailable. Please check skill settings.")
                self.speak_dialog("device.status", data={
                    "device": "Home Assistant",
                    "type": "server",
                    "state": "not configured, check your skill settings or connection to Home Assistant instance."
                    })
                return False
        return True

    @intent_handler("turn.on.intent")  # pragma: no cover
    def handle_turn_on_intent(self, message: Message) -> None:
        """Handle turn on intent."""
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_turn_on(Message("", {"device": device}))
            if not self._handle_device_response(
                response, device, "device.turned.on", success_message="Successfully turned on!"
            ):
                self.log.info(f"Trying to turn on device {device}")

    @intent_handler("turn.off.intent")  # pragma: no cover
    @intent_handler("stop.intent")  # pragma: no cover
    def handle_turn_off_intent(self, message: Message) -> None:
        """Handle turn off intent."""
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_turn_off(Message("", {"device": device}))
            if not self._handle_device_response(
                response, device, "device.turned.off", success_message="Successfully turned off/stopped!"
            ):
                self.log.info(f"Trying to turn off device {device}")

    @intent_handler("lights.get.brightness.intent")  # pragma: no cover
    def handle_get_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_get_light_brightness(Message("", {"device": device}))
            if response and not response.get("response"):
                if brightness := response.get("brightness"):
                    self.speak_dialog(
                        "lights.current.brightness",
                        data={"brightness": brightness, "device": device},
                    )
                    self.gui.show_text(f"{device}: Current brightness {brightness}")
                    return
            self.speak_dialog("lights.status.not.available", data={"device": device})
            self.gui.show_text(f"{device} not found in Home Assistant.")

    @intent_handler("lights.set.brightness.intent")  # pragma: no cover
    def handle_set_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
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
                success_message=f"Brightness set to {brightness}",
            ):
                return
            self.log.info(f"Trying to set brightness of {brightness} for {device}")

    @intent_handler("lights.increase.brightness.intent")  # pragma: no cover
    def handle_increase_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_increase_light_brightness(Message("", {"device": device}))
            brightness = response.get("brightness", "unknown percentage")
            if self._handle_device_response(
                response,
                device,
                "lights.current.brightness",
                {"brightness": brightness} if response else None,
                success_message=f"Increased brightness to {brightness}",
            ):
                return
            self.log.info(f"Trying to increase brightness for {device}")

    @intent_handler("lights.decrease.brightness.intent")  # pragma: no cover
    def handle_decrease_brightness_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_decrease_light_brightness(Message("", {"device": device}))
            brightness = response.get("brightness", "unknown percentage")
            if self._handle_device_response(
                response,
                device,
                "lights.current.brightness",
                {"brightness": brightness},
                success_message=f"Decreased brightness to {brightness}",
            ):
                return
            self.log.info(f"Trying to decrease brightness for {device}")

    @intent_handler("lights.get.color.intent")  # pragma: no cover
    def handle_get_color_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        if device := self._get_device_from_message(message):
            response = self.ha_client.handle_get_light_color(Message("", {"device": device}))
            if response and not response.get("response"):
                if color := response.get("color"):
                    self.speak_dialog("lights.current.color", data={"color": color, "device": device})
                    self.gui.show_text(f"{device}: Current color {color}")
                    return
            self.speak_dialog("lights.status.not.available", data={"device": device})
            self.gui.show_text(f"Could not get color of {device}")

    @intent_handler("lights.set.color.intent")  # pragma: no cover
    def handle_set_color_intent(self, message: Message):
        self.log.info(message.data)
        if not self.check_client_connection():
            return
        device = self._get_device_from_message(message)
        color = message.data.get("color")

        if not color:
            self.speak_dialog("no.parsed.color")
            return

        color = color.strip()
        if color.startswith("to "):
            color = color[3:].strip()

        if device:
            response = self.ha_client.handle_set_light_color(Message("", {"device": device, "color": color}))
            color = response.get("color", "unknown")
            if self._handle_device_response(
                response,
                device,
                "lights.current.color",
                {"color": color},
                success_message=f"Set color to {color}",
            ):
                return
            self.log.info(f"Trying to set color of {device}")

    @intent_handler("assist.intent")  # pragma: no cover
    def handle_assist_intent(self, message: Message):
        """Handle passthrough to Home Assistant's Assist API."""
        if not self.check_client_connection():
            return
        command = message.data.get("command")
        if command:
            self.ha_client.handle_assist_message(Message("", {"command": command}))
            self.speak_dialog("assist")
            self.log.info(f"Trying to pass message to Home Assistant's Assist API:\n{command}")
            self.gui.show_text(f"Sending message to Assist: {command}")
        else:
            self.speak_dialog("assist.not.understood")

    def _get_ha_value_from_percentage_brightness(self, brightness):
        return round(int(brightness)) / 100 * 255
