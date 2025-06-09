"""Home Assistant client"""

from copy import deepcopy
from typing import Optional

from ovos_bus_client import Message, MessageBusClient
from ovos_utils.log import LOG
from ovos_utils.parse import match_one

from skill_homeassistant.ha_client.constants import SUPPORTED_DEVICES
from skill_homeassistant.ha_client.logic.connector import HomeAssistantRESTConnector
from skill_homeassistant.ha_client.logic.utils import (
    check_if_device_type_is_group,
    get_percentage_brightness_from_ha_value,
    map_entity_to_device_type,
)


class HomeAssistantClient:
    """Home Assistant client, used by OpenVoiceOS or Neon.AI."""

    def __init__(self, config=None, bus: Optional[MessageBusClient] = None):
        """Initialize the plugin

        Args:
            config (dict): The plugin configuration
            bus (MessageBusClient, optional): The OVOS message bus
        """
        self.bus = bus
        self.config = config or {}
        self.oauth_client_id = None
        self.temporary_instance = None
        self.connector = None
        self.devices = []
        self.registered_devices = []  # Device objects
        self.registered_device_names = []  # Device friendly/entity names

        self.munged_id = "ovos-PHAL-plugin-homeassistant_homeassistant-phal-plugin"
        self.instance_available = False
        self.device_types = SUPPORTED_DEVICES
        self.brightness_increment = self.get_brightness_increment()

        # Register bus events if we have a bus
        if self.bus is not None:
            self._register_bus_events()

        self.init_configuration()

    def _register_bus_events(self) -> None:
        """Register message bus events. Only call if self.bus is not None."""
        assert self.bus is not None  # Help type checker understand bus cannot be None here
        self.bus.on("configuration.updated", self.init_configuration)
        self.bus.on("configuration.patch", self.init_configuration)

    def get_brightness_increment(self) -> int:
        """Get the brightness increment from the config

        Returns:
            int: The brightness increment
        """
        return self.config.get("brightness_increment", 10)

    @property
    def search_confidence_threshold(self) -> int:
        """Get the search confidence threshold from the config

        Returns:
            int: The search confidence threshold value, default 0.5
        """
        return self.config.get("search_confidence_threshold", 0.5)

    @property
    def toggle_automations(self) -> bool:
        """Get the toggle automations from the config

        Returns:
            bool: The toggle automations value, default False
        """
        return self.config.get("toggle_automations", False)

    # SETUP INSTANCE SUPPORT
    def validate_instance_connection(self, host, api_key, assist_only, verify_ssl):
        """Validate the connection to the Home Assistant instance

        Args:
            host (str): The Home Assistant instance URL
            api_key (str): The Home Assistant API key
            assist_only (bool): Whether to only pull entities exposed to Assist. Default True
            verify_ssl (bool): Whether to verify ssl certificates (True) or ignore ssl errors (False). Default True

        Returns:
            bool: True if the connection is valid, False otherwise
        """
        try:
            validator = HomeAssistantRESTConnector(host, api_key, assist_only, verify_ssl)

            validator.get_all_devices()

            return True

        except Exception as e:
            LOG.exception("Error validating Home Assistant connection", exc_info=e)
            return False

    # INSTANCE INIT OPERATIONS
    def init_configuration(self, *args, **kwargs):
        """Initialize instance configuration"""
        LOG.info(f"Initializing configuration with args: {args} and kwargs: {kwargs}")
        self.config["host"] = kwargs.get("configuration_host", self.config.get("host", ""))
        self.config["api_key"] = kwargs.get("configuration_api_key", self.config.get("api_key", ""))
        if args:
            LOG.warning(
                f"Received unexpected args: {args}, ignoring them in configuration initialization. Use kwargs instead."
            )
        configuration_host = self.config.get("host", "")
        configuration_api_key = self.config.get("api_key", "")
        configuration_assist_only = self.config.get("assist_only", True)
        configuration_verify_ssl = self.config.get("verify_ssl", True)
        if configuration_host != "" and configuration_api_key != "":
            self.instance_available = True  # TODO: Use the validator to check this
            self.connector = HomeAssistantRESTConnector(
                host=configuration_host,
                api_key=configuration_api_key,
                assist_only=configuration_assist_only,
                verify_ssl=configuration_verify_ssl,
                timeout=self.config.get("timeout", 3),
            )
            self.devices = self.connector.get_all_devices()
            self.registered_devices = []
            self.build_devices()
        else:
            self.instance_available = False

    def build_devices(self, *args, **kwargs):
        """Build the devices from the Home Assistant API"""
        LOG.info(f"Initializing configuration with args: {args} and kwargs: {kwargs}")
        for device in self.devices:
            device_type = map_entity_to_device_type(device["entity_id"])
            device_type_is_group = check_if_device_type_is_group(device.get("attributes", {}))
            if device_type is not None:
                if not device_type_is_group:
                    device_id = device["entity_id"]
                    device_name = device.get("attributes", {}).get("friendly_name", device_id)
                    device_icon = f"mdi:{device_type}"
                    device_state = device.get("state", None)
                    device_area = device.get("area_id", None)

                    device_attributes = device.get("attributes", {})
                    if device_type in self.device_types:
                        LOG.debug(f"Device added: {device_name} - {device_type} - {device_area}")
                        dev_args = [
                            self.connector,
                            device_id,
                            device_icon,
                            device_name,
                            device_state,
                            device_attributes,
                            device_area,
                        ]
                        self.registered_devices.append(self.device_types[device_type](*dev_args))
                        self.registered_device_names.append(device_name)
                    else:
                        LOG.warning(f"Device type {device_type} not supported; please file an issue on GitHub")
                else:
                    LOG.warning(f"Device type {device_type} is a group, not supported currently")

    def handle_get_devices(self):
        """Handle the get devices message

        Args:
            message (Message): The message object
        """
        # build a plain list of devices
        device_list = []
        for device in self.registered_devices:
            device_list.append(device.get_device_display_model())

        return {"devices": device_list}

    def handle_get_device(self, message: Message):
        """Handle the message to get a single device

        Args:
            message (Message): The message object
        """
        # Deprecate, this may not actually be used anywhere
        device_id = message.data.get("device_id", None)
        if device_id is not None:
            LOG.debug(f"Device ID provided in bus message: {device_id}")
            return self._return_device_response(device_id=device_id)

        # Device ID not provided, usually VUI
        device = message.data.get("device")
        device_result = self.fuzzy_match_name(self.registered_devices, device, self.registered_device_names)
        LOG.debug(f"No device ID, found device result: {device_result or 'None'}")
        if device_result:
            return self._return_device_response(device_id=device_result)

        # No device found
        LOG.debug(f"No Home Assistant device exists for {device}")

    def _return_device_response(self, *args, device_id, **kwargs):
        """Return the device representation to the bus

        Args:
            device_id (str): The device ID to lookup and return
        """
        LOG.warning(f"Received unnecessary args: {args}")
        LOG.warning(f"Received unnecessary kwargs: {kwargs}")
        for device in self.registered_devices:
            if device.device_id == device_id:
                return device.get_device_display_model()
        LOG.debug(f"No device found with device ID {device_id}")
        return {}

    def handle_turn_on(self, message):
        """Handle the turn on message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        if device_id is not None:
            for device in self.registered_devices:
                if device.device_id == device_id:
                    device.turn_on()
                    return {"device": spoken_device}
        # No device found
        LOG.debug(f"No Home Assistant device exists for {device_id}")
        return {}

    def handle_turn_off(self, message):
        """Handle the turn off message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        if device_id is not None:
            for device in self.registered_devices:
                if device.device_id == device_id:
                    device.turn_off()
                    return {"device": spoken_device}
        # No device found
        LOG.debug(f"No Home Assistant device exists for {device_id}")
        return {}

    def _gather_device_id(self, message):
        """Given a bus message, return the device ID and spoken device name for reference

        Args:
            message (Message): Bus message from GUI or other source

        Returns:
            Tuple[Optional[str], str]: original device ID or device search result or None, spoken device name (str)
        """
        device_id = message.data.get("device_id", None)
        device = message.data.get("device", None)
        spoken_device = deepcopy(device) or device_id
        if device_id is None and device is not None:
            device_id = self.fuzzy_match_name(self.registered_devices, device, self.registered_device_names)
            LOG.debug(f"No device ID, found device result: {device_id or 'None'}")
        return device_id, spoken_device

    def handle_call_supported_function(self, message):
        """Handle the call supported function message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        function_name = message.data.get("function_name", None)
        function_args = message.data.get("function_args", None)
        if device_id is not None and function_name is not None:
            for device in self.registered_devices:
                if device.device_id == device_id:
                    if function_args is not None:
                        response = device.call_function(function_name, function_args)
                    else:
                        response = device.call_function(function_name)
                    return {"device": spoken_device, "response": response}
        else:
            response = "Device id or function name not provided"
            LOG.error(response)
            return {"device": spoken_device, "response": response}

    def handle_get_light_brightness(self, message):
        """Handle the get light brightness message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        if device_id is not None:
            for device in self.registered_devices:
                if device.device_id == device_id:
                    return {
                        "device": spoken_device,
                        "brightness": get_percentage_brightness_from_ha_value(device.get_brightness()),
                    }
        else:
            response = "Device id not provided"
            LOG.error(response)
            return {"response": response}

    def handle_get_light_color(self, message):
        """Handle the get light color VUI message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        if device_id is not None:
            for device in self.registered_devices:
                if device.device_id == device_id:
                    color = device.get_spoken_color()
                    return {"device": spoken_device, "color": color}
        else:
            response = "Device id not provided"
            LOG.error(response)
            return {"device": spoken_device, "response": response}

    def handle_set_light_color(self, message):
        """Handle the set light color message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        color = message.data.get("color")
        for device in self.registered_devices:
            if device.device_id == device_id:
                device.set_color(color)
                return {"device": spoken_device, "color": color}
        response = "Device id not provided"
        LOG.error(response)
        return {"device": spoken_device, "response": response}

    def handle_set_light_brightness(self, message):
        """Handle the set light brightness message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        brightness = message.data.get("brightness")
        for device in self.registered_devices:
            if device.device_id == device_id:
                device.set_brightness(brightness)
                return {
                    "device": spoken_device,
                    "brightness": get_percentage_brightness_from_ha_value(brightness),
                }

        response = "Device id not provided"
        LOG.error(response)
        return {"device": spoken_device, "response": response}

    def handle_increase_light_brightness(self, message):
        """Handle the increase light brightness message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        for device in self.registered_devices:
            if device.device_id == device_id:
                device.increase_brightness(self.brightness_increment)
                return {
                    "device": spoken_device,
                    "brightness": get_percentage_brightness_from_ha_value(device.get_brightness()),
                }
        response = "Device id not provided"
        LOG.error(response)
        return {"device": spoken_device, "response": response}

    def handle_decrease_light_brightness(self, message):
        """Handle the decrease light brightness message

        Args:
            message (Message): The message object
        """
        device_id, spoken_device = self._gather_device_id(message)
        for device in self.registered_devices:
            if device.device_id == device_id:
                device.decrease_brightness(self.brightness_increment)
                return {
                    "device": spoken_device,
                    "brightness": get_percentage_brightness_from_ha_value(device.get_brightness()),
                }
        response = "Device id not provided"
        LOG.error(response)
        return {"device": spoken_device, "response": response}

    def handle_assist_message(self, message):
        """Handle a passthrough message to Home Assistant's Assist API.

        Args:
            message (Message): The message object

        Returns:
            dict: Response data from Assist API or None if failed
        """
        command: str = message.data.get("command")
        LOG.debug(f"Received Assist command: {command}")
        if self.connector:
            return self.connector.send_assist_command(command)
        return None

    # UTILS
    def fuzzy_match_name(self, devices_list, spoken_name, device_names) -> Optional[str]:
        """Given a list of device names, fuzzy match the spoken name to the most likely one.
        Returns the device id of the most likely match or None if no match is found.
        """
        device, score = match_one(spoken_name, device_names)
        if score > self.search_confidence_threshold:
            return devices_list[device_names.index(device)].device_id
        LOG.info(f"Device name '{spoken_name}' not found, closest match is '{device}' with confidence score {score}")
        LOG.info(f"Score of {score} is too low, returning None")
        return None
