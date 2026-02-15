"""Home Assistant Connector Base Module.

This module provides the abstract base connector class for interacting with Home Assistant.
It defines the interface that concrete connector implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class HomeAssistantConnector(ABC):
    """Home Assistant Connector Abstract Base Class.

    Defines the interface for Home Assistant connector implementations.
    """

    def __init__(self, host, api_key, assist_only=True, verify_ssl=True, timeout=3):
        """Constructor

        Args:
            host (str): The host of the home assistant instance.
            api_key (str): The api key
            assist_only (bool): Whether to only pull entities exposed to Assist. Default True.
            verify_ssl (bool): Whether to verify SSL certificates. Default True.
            timeout (int): The timeout for requests. Default 3 seconds.
        """
        self.host = host
        self.api_key = api_key
        self.assist_only = assist_only
        self.event_listeners = {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    @abstractmethod
    def get_all_devices(self) -> List[dict]:
        """
        Get a list of all devices.
        """
        raise NotImplementedError

    @abstractmethod
    def get_device_state(self, entity_id: str):
        """
        Get the state of a device.
        Args:
            entity_id (str): HomeAssistant Device ID
        """
        raise NotImplementedError

    @abstractmethod
    def set_device_state(self, entity_id: str, state: str, attributes: Optional[dict] = None):
        """Set the state of a device.

        Args:
            entity_id (str): The id of the device.
            state (str): The state to set.
            attributes (dict): The attributes to set.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_devices_with_type(self, device_type):
        """Get all devices with a specific type.

        Args:
            device_type (str): The type of the device.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_devices_with_type_and_attribute(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_devices_with_type_and_attribute_in(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_devices_with_type_and_attribute_not_in(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        raise NotImplementedError

    @abstractmethod
    def turn_on(self, device_id, device_type):
        """Turn on a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
        """
        raise NotImplementedError

    @abstractmethod
    def turn_off(self, device_id, device_type):
        """Turn off a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
        """
        raise NotImplementedError

    @abstractmethod
    def call_function(self, device_id, device_type, function, arguments=None):
        """Call a function on a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
            function (str): The function to call.
            arguments (dict): The arguments to pass to the function.
        """
        raise NotImplementedError

    @abstractmethod
    def register_callback(self, device_id, callback):
        """Register a callback for device events.

        Args:
            device_id (str): The id of the device.
            callback (function): The callback to call.
        """
        raise NotImplementedError
