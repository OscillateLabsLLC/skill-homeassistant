# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring
import unittest
from unittest.mock import Mock, patch, MagicMock

import requests

from skill_homeassistant.ha_client.logic.connector import HomeAssistantRESTConnector


class TestHomeAssistantRESTConnector(unittest.TestCase):
    """Tests for HomeAssistantRESTConnector"""

    def setUp(self):
        self.connector = HomeAssistantRESTConnector(
            host="http://homeassistant.local",
            api_key="test_api_key",
            verify_ssl=True,
            timeout=3,
        )

    def test_init_sets_headers(self):
        """Test that __init__ properly sets headers with API key."""
        self.assertEqual(
            self.connector.headers,
            {
                "Authorization": "Bearer test_api_key",
                "content-type": "application/json",
            },
        )

    def test_register_callback(self):
        """Test registering a callback for device events."""
        callback = Mock()
        self.connector.register_callback("light.living_room", callback)
        self.assertEqual(self.connector.event_listeners["light.living_room"], callback)

    # --- get_all_devices tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_all_devices_success(self, mock_get):
        """Test successful retrieval of all devices."""
        mock_response = Mock()
        mock_response.json.return_value = [{"entity_id": "light.test", "state": "on"}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.connector.get_all_devices()

        self.assertEqual(result, [{"entity_id": "light.test", "state": "on"}])
        mock_get.assert_called_once_with(
            "http://homeassistant.local/api/states",
            headers=self.connector.headers,
            timeout=3,
            verify=True,
        )

    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_all_devices_connection_error(self, mock_get):
        """Test get_all_devices handles ConnectionError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = self.connector.get_all_devices()

        self.assertEqual(result, [])

    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_all_devices_request_exception(self, mock_get):
        """Test get_all_devices handles RequestException."""
        mock_get.side_effect = requests.exceptions.RequestException("Request failed")

        result = self.connector.get_all_devices()

        self.assertEqual(result, [])

    # --- get_device_state tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_device_state_success(self, mock_get):
        """Test successful retrieval of device state."""
        mock_response = Mock()
        mock_response.json.return_value = {"entity_id": "light.test", "state": "on"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.connector.get_device_state("light.test")

        self.assertEqual(result, {"entity_id": "light.test", "state": "on"})
        mock_get.assert_called_once_with(
            "http://homeassistant.local/api/states/light.test",
            headers=self.connector.headers,
            timeout=3,
            verify=True,
        )

    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_device_state_connection_error(self, mock_get):
        """Test get_device_state handles ConnectionError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = self.connector.get_device_state("light.test")

        self.assertEqual(result, [])

    @patch("skill_homeassistant.ha_client.logic.connector.requests.get")
    def test_get_device_state_request_exception(self, mock_get):
        """Test get_device_state handles RequestException."""
        mock_get.side_effect = requests.exceptions.RequestException("Request failed")

        result = self.connector.get_device_state("light.test")

        self.assertEqual(result, {})

    # --- set_device_state tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_set_device_state_success(self, mock_post):
        """Test successful setting of device state."""
        mock_response = Mock()
        mock_response.json.return_value = {"entity_id": "light.test", "state": "on"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.set_device_state("light.test", "on", {"brightness": 255})

        self.assertEqual(result, {"entity_id": "light.test", "state": "on"})

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_set_device_state_without_attributes(self, mock_post):
        """Test setting device state without attributes."""
        mock_response = Mock()
        mock_response.json.return_value = {"entity_id": "light.test", "state": "off"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.set_device_state("light.test", "off", None)

        self.assertEqual(result, {"entity_id": "light.test", "state": "off"})

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_set_device_state_request_exception(self, mock_post):
        """Test set_device_state handles RequestException."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Request failed")
        mock_post.return_value = mock_response

        result = self.connector.set_device_state("light.test", "on", None)

        self.assertIsNone(result)

    # --- get_all_devices_with_type tests ---
    @patch.object(HomeAssistantRESTConnector, "get_all_devices")
    def test_get_all_devices_with_type(self, mock_get_all):
        """Test filtering devices by type."""
        mock_get_all.return_value = [
            {"entity_id": "light.living_room", "state": "on"},
            {"entity_id": "switch.kitchen", "state": "off"},
            {"entity_id": "light.bedroom", "state": "off"},
        ]

        result = self.connector.get_all_devices_with_type("light")

        self.assertEqual(len(result), 2)
        self.assertTrue(all(d["entity_id"].startswith("light") for d in result))

    # --- get_all_devices_with_type_and_attribute tests ---
    @patch.object(HomeAssistantRESTConnector, "get_all_devices")
    def test_get_all_devices_with_type_and_attribute(self, mock_get_all):
        """Test filtering devices by type and attribute value."""
        mock_get_all.return_value = [
            {"entity_id": "light.living_room", "state": "on", "attributes": {"friendly_name": "Living Room"}},
            {"entity_id": "light.bedroom", "state": "off", "attributes": {"friendly_name": "Bedroom"}},
        ]

        result = self.connector.get_all_devices_with_type_and_attribute("light", "friendly_name", "Living Room")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_id"], "light.living_room")

    # --- get_all_devices_with_type_and_attribute_in tests ---
    @patch.object(HomeAssistantRESTConnector, "get_all_devices")
    def test_get_all_devices_with_type_and_attribute_in(self, mock_get_all):
        """Test filtering devices by type and attribute in list."""
        mock_get_all.return_value = [
            {"entity_id": "light.living_room", "state": "on", "attributes": {"area": "downstairs"}},
            {"entity_id": "light.bedroom", "state": "off", "attributes": {"area": "upstairs"}},
            {"entity_id": "light.kitchen", "state": "on", "attributes": {"area": "downstairs"}},
        ]

        result = self.connector.get_all_devices_with_type_and_attribute_in("light", "area", ["downstairs", "basement"])

        self.assertEqual(len(result), 2)

    # --- get_all_devices_with_type_and_attribute_not_in tests ---
    @patch.object(HomeAssistantRESTConnector, "get_all_devices")
    def test_get_all_devices_with_type_and_attribute_not_in(self, mock_get_all):
        """Test filtering devices by type and attribute not in list."""
        mock_get_all.return_value = [
            {"entity_id": "light.living_room", "state": "on", "attributes": {"area": "downstairs"}},
            {"entity_id": "light.bedroom", "state": "off", "attributes": {"area": "upstairs"}},
            {"entity_id": "light.kitchen", "state": "on", "attributes": {"area": "downstairs"}},
        ]

        result = self.connector.get_all_devices_with_type_and_attribute_not_in("light", "area", ["downstairs"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_id"], "light.bedroom")

    # --- turn_on tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_turn_on_success(self, mock_post):
        """Test successful turn_on call."""
        mock_response = Mock()
        mock_response.json.return_value = [{"entity_id": "light.test", "state": "on"}]
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.turn_on("light.test", "light")

        self.assertEqual(result, [{"entity_id": "light.test", "state": "on"}])
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("/api/services/light/turn_on", call_args[0][0])

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_turn_on_request_exception(self, mock_post):
        """Test turn_on handles RequestException."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Request failed")
        mock_post.return_value = mock_response

        result = self.connector.turn_on("light.test", "light")

        self.assertIsNone(result)

    # --- turn_off tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_turn_off_success(self, mock_post):
        """Test successful turn_off call."""
        mock_response = Mock()
        mock_response.json.return_value = [{"entity_id": "light.test", "state": "off"}]
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.turn_off("light.test", "light")

        self.assertEqual(result, [{"entity_id": "light.test", "state": "off"}])
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("/api/services/light/turn_off", call_args[0][0])

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_turn_off_request_exception(self, mock_post):
        """Test turn_off handles RequestException."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Request failed")
        mock_post.return_value = mock_response

        result = self.connector.turn_off("light.test", "light")

        self.assertIsNone(result)

    # --- call_function tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_call_function_without_arguments(self, mock_post):
        """Test call_function without additional arguments."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.call_function("light.test", "light", "toggle")

        self.assertEqual(result, {"result": "ok"})

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_call_function_with_arguments(self, mock_post):
        """Test call_function with additional arguments."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.call_function(
            "light.test", "light", "turn_on", {"brightness": 128, "color_name": "red"}
        )

        self.assertEqual(result, {"result": "ok"})
        # Verify the payload includes the arguments
        call_args = mock_post.call_args
        import json
        payload = json.loads(call_args[1]["data"])
        self.assertEqual(payload["brightness"], 128)
        self.assertEqual(payload["color_name"], "red")

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_call_function_request_exception(self, mock_post):
        """Test call_function handles RequestException."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Request failed")
        mock_post.return_value = mock_response

        result = self.connector.call_function("light.test", "light", "toggle")

        self.assertIsNone(result)

    # --- send_assist_command tests ---
    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_send_assist_command_success(self, mock_post):
        """Test successful send_assist_command call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {"speech": {"plain": {"speech": "Turned on the kitchen light"}}}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.send_assist_command("turn on kitchen light")

        self.assertIsNotNone(result)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("/api/conversation/process", call_args[0][0])

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_send_assist_command_with_language(self, mock_post):
        """Test send_assist_command with custom language."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": {"speech": {}}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.send_assist_command("enciende la luz", {"language": "es"})

        self.assertIsNotNone(result)
        import json
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        self.assertEqual(payload["language"], "es")

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_send_assist_command_default_language(self, mock_post):
        """Test send_assist_command uses default language when not specified."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": {"speech": {}}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.connector.send_assist_command("turn on light")

        import json
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]["data"])
        self.assertEqual(payload["language"], "en")

    @patch("skill_homeassistant.ha_client.logic.connector.requests.post")
    def test_send_assist_command_request_exception(self, mock_post):
        """Test send_assist_command handles RequestException."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException("Request failed")
        mock_post.return_value = mock_response

        result = self.connector.send_assist_command("turn on light")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
