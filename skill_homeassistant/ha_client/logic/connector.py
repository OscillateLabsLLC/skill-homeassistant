"""Home Assistant REST Connector Module.

This module provides the REST API connector implementation for interacting with
Home Assistant. It makes HTTP calls to control devices and get state information.
"""

import json

import requests
from ovos_utils.log import LOG

from skill_homeassistant.ha_client.logic.base import HomeAssistantConnector


class HomeAssistantRESTConnector(HomeAssistantConnector):
    """Home Assistant REST Connector"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Authorization": "Bearer " + self.api_key,
            "content-type": "application/json",
        }

    def register_callback(self, device_id, callback):
        self.event_listeners[device_id] = callback

    def get_all_devices(self):
        """Get all devices from home assistant."""
        url = self.host + "/api/states"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            LOG.exception(f"Error connecting to Home Assistant at {self.host}")
            return []
        except requests.exceptions.RequestException:
            LOG.exception("Error fetching devices")
            return []

    def get_device_state(self, entity_id):
        """Get the state of a device."""
        url = self.host + "/api/states/" + entity_id
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            LOG.exception(f"Error connecting to Home Assistant at {self.host}")
            return []
        except requests.exceptions.RequestException:
            LOG.exception("Error fetching device state")
            return {}

    def set_device_state(self, entity_id, state, attributes=None):
        """Set the state of a device.

        Args:
            entity_id (str): The id of the device.
            state (str): The state to set.
            attributes (dict): The attributes to set.
        """
        url = self.host + "/api/states/" + entity_id
        payload = {"state": state, "attributes": attributes}
        response = requests.post(
            url, data=json.dumps(payload), headers=self.headers, timeout=self.timeout, verify=self.verify_ssl
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            LOG.exception("Error setting device state")
            return None

    def get_all_devices_with_type(self, device_type):
        """Get all devices with a specific type.

        Args:
            device_type (str): The type of the device.
        """
        devices = self.get_all_devices()
        return [device for device in devices if device["entity_id"].startswith(device_type)]

    def get_all_devices_with_type_and_attribute(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        devices = self.get_all_devices()
        return [
            device
            for device in devices
            if device["entity_id"].startswith(device_type) and device["attributes"][attribute] == value
        ]

    def get_all_devices_with_type_and_attribute_in(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        devices = self.get_all_devices()
        return [
            device
            for device in devices
            if device["entity_id"].startswith(device_type) and device["attributes"][attribute] in value
        ]

    def get_all_devices_with_type_and_attribute_not_in(self, device_type, attribute, value):
        """Get all devices with a specific type and attribute.

        Args:
            device_type (str): The type of the device.
            attribute (str): The attribute to check.
            value (str): The value of the attribute.
        """
        devices = self.get_all_devices()
        return [
            device
            for device in devices
            if device["entity_id"].startswith(device_type) and device["attributes"][attribute] not in value
        ]

    def turn_on(self, device_id, device_type):
        """Turn on a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
        """
        url = self.host + "/api/services/" + device_type + "/turn_on"
        payload = {"entity_id": device_id}
        response = requests.post(
            url, data=json.dumps(payload), headers=self.headers, timeout=self.timeout, verify=self.verify_ssl
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            LOG.exception("Error turning on device")
            return None

    def turn_off(self, device_id, device_type):
        """Turn off a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
        """
        url = self.host + "/api/services/" + device_type + "/turn_off"
        payload = {"entity_id": device_id}
        response = requests.post(
            url, data=json.dumps(payload), headers=self.headers, timeout=self.timeout, verify=self.verify_ssl
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            LOG.exception("Error turning off device")
            return None

    def call_function(self, device_id, device_type, function, arguments=None):
        """Call a function on a device.

        Args:
            device_id (str): The id of the device.
            device_type (str): The type of the device.
            function (str): The function to call.
            arguments (dict): The arguments to pass to the function.
        """
        url = self.host + "/api/services/" + device_type + "/" + function
        payload = {"entity_id": device_id}
        if arguments:
            for key, value in arguments.items():
                payload[key] = value

        response = requests.post(
            url, data=json.dumps(payload), headers=self.headers, timeout=self.timeout, verify=self.verify_ssl
        )

        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            LOG.exception("Error calling function")
            return None

    def send_assist_command(self, command, arguments=None):
        """Send a command to the Home Assistant Assist websocket endpoint.

        Args:
            command (string): Spoken command to send to Home Assistant.
            arguments (dict, optional): Additional arguments to send. HA currently only supports 'language'
        """
        arguments = arguments or {}
        url = self.host + "/api/conversation/process"
        payload = {
            "text": command,
            "language": arguments.get("language", "en"),
        }
        response = requests.post(
            url, data=json.dumps(payload), headers=self.headers, timeout=self.timeout, verify=self.verify_ssl
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            LOG.exception("Error sending Assist command")
            return None
