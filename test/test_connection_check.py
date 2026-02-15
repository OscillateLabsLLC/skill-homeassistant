import unittest
from unittest.mock import Mock
from ovos_bus_client import Message
from ovos_utils.messagebus import FakeBus
from skill_homeassistant import HomeAssistantSkill


class TestConnectionCheckUnit(unittest.TestCase):
    """Unit tests for the check_client_connection method in isolation."""
    
    def setUp(self):
        self.bus = FakeBus()
        self.skill = HomeAssistantSkill(skill_id="test_skill")
        self.skill._startup(self.bus, "test_skill")
        self.skill.speak_dialog = Mock()
        self.skill.gui = Mock()
        self.skill.log = Mock()
        # Mock the ha_client to control its behavior
        self.skill.ha_client = Mock()
        self.skill.ha_client.instance_available = False

    def test_check_connection_returns_true_when_already_available(self):
        """Test that check_client_connection returns True explicitly when already connected."""
        self.skill.ha_client.instance_available = True
        
        result = self.skill.check_client_connection()
        
        # Verify explicit True return (not None, not just truthy)
        self.assertIs(result, True)
        # Verify init_configuration is NOT called when already connected
        self.skill.ha_client.init_configuration.assert_not_called()
        # Verify no error side effects occurred
        self.skill.speak_dialog.assert_not_called()
        self.skill.gui.show_text.assert_not_called()
        self.skill.log.error.assert_not_called()

    def test_check_connection_returns_true_after_successful_init(self):
        """Test that check_client_connection initializes and returns True on success."""
        self.skill.ha_client.instance_available = False
        
        # Properly simulate what init_configuration does: sets instance_available to True
        def mock_init(*args, **kwargs):
            self.skill.ha_client.instance_available = True
            
        self.skill.ha_client.init_configuration.side_effect = mock_init
        
        result = self.skill.check_client_connection()
        
        # Verify explicit True return
        self.assertIs(result, True)
        # Verify init_configuration was called exactly once
        self.skill.ha_client.init_configuration.assert_called_once()

    def test_check_connection_returns_false_when_init_leaves_instance_unavailable(self):
        """Test that check_client_connection returns False when init succeeds but instance_available stays False.
        
        When init_configuration completes without error but instance_available remains False,
        check_client_connection raises an internal exception which triggers the error handling path.
        """
        self.skill.ha_client.instance_available = False
        
        # init_configuration completes without error, but instance_available stays False.
        # The method itself then raises an exception because the instance is still unavailable.
        def mock_init(*args, **kwargs):
            pass  # instance_available remains False
            
        self.skill.ha_client.init_configuration.side_effect = mock_init
        
        result = self.skill.check_client_connection()
        
        # Verify explicit False return
        self.assertIs(result, False)
        self.skill.ha_client.init_configuration.assert_called_once()
        # Verify error was logged (the internally raised exception hits the except block)
        self.skill.log.error.assert_called_once()
        # Verify error dialog was spoken
        self.skill.speak_dialog.assert_called_once_with("device.status", data={
            "device": "Home Assistant",
            "type": "server",
            "state": "not configured, check your skill settings or connection to Home Assistant instance."
        })
        # Verify GUI error message was shown
        self.skill.gui.show_text.assert_called_once_with(
            "Connection to Home Assistant is not configured or unavailable. Please check skill settings."
        )

    def test_check_connection_returns_false_on_exception(self):
        """Test that check_client_connection handles exceptions during init and returns False."""
        self.skill.ha_client.instance_available = False
        self.skill.ha_client.init_configuration.side_effect = Exception("Connection error")
        
        result = self.skill.check_client_connection()
        
        # Verify explicit False return
        self.assertIs(result, False)
        # Verify error was logged
        self.skill.log.error.assert_called_once()
        # Verify error dialog was spoken
        self.skill.speak_dialog.assert_called_once_with("device.status", data={
            "device": "Home Assistant",
            "type": "server",
            "state": "not configured, check your skill settings or connection to Home Assistant instance."
        })
        # Verify GUI error message
        self.skill.gui.show_text.assert_called_once_with(
            "Connection to Home Assistant is not configured or unavailable. Please check skill settings."
        )

    def test_check_connection_passes_settings_to_init(self):
        """Test that check_client_connection passes self.settings to init_configuration."""
        self.skill.ha_client.instance_available = False
        self.skill.settings = {"host": "test.local", "api_key": "secret"}
        
        def mock_init(*args, **kwargs):
            self.skill.ha_client.instance_available = True
            
        self.skill.ha_client.init_configuration.side_effect = mock_init
        
        result = self.skill.check_client_connection()
        
        # Verify settings were passed to init_configuration
        self.skill.ha_client.init_configuration.assert_called_once_with(self.skill.settings)
        self.assertIs(result, True)


class TestConnectionCheckIntegration(unittest.TestCase):
    """Integration tests verifying check_client_connection works correctly with intent handlers."""
    
    def setUp(self):
        self.bus = FakeBus()
        self.skill = HomeAssistantSkill(skill_id="test_skill")
        self.skill._startup(self.bus, "test_skill")
        self.skill.speak_dialog = Mock()
        self.skill.gui = Mock()
        self.skill.log = Mock()
        # Mock the ha_client to control its behavior
        self.skill.ha_client = Mock()
        self.skill.ha_client.instance_available = False

    def test_turn_on_intent_aborts_on_connection_failure(self):
        """Test that handle_turn_on_intent aborts when connection check fails."""
        self.skill.ha_client.instance_available = False
        self.skill.ha_client.init_configuration.side_effect = Exception("Connection failed")
        
        message = Message("turn.on.intent", {"entity": "light.living_room"})
        self.skill.handle_turn_on_intent(message)
        
        # Verify ha_client.handle_turn_on was NOT called
        self.skill.ha_client.handle_turn_on.assert_not_called()
        # Verify error messages were shown
        self.skill.gui.show_text.assert_called_with(
            "Connection to Home Assistant is not configured or unavailable. Please check skill settings."
        )

    def test_turn_on_intent_proceeds_on_connection_success(self):
        """Test that handle_turn_on_intent flows through connection check, device parsing, and response handling."""
        self.skill.ha_client.instance_available = True
        self.skill.ha_client.handle_turn_on.return_value = {"state": "on"}

        message = Message("turn.on.intent", {"entity": "light.test"})
        self.skill.handle_turn_on_intent(message)
        
        # Verify the full flow: device was extracted from message, passed to ha_client
        self.skill.ha_client.handle_turn_on.assert_called_once()
        call_msg = self.skill.ha_client.handle_turn_on.call_args[0][0]
        self.assertEqual(call_msg.data["device"], "light.test")
        # Verify _handle_device_response ran and spoke the success dialog
        self.skill.speak_dialog.assert_called_once_with("device.turned.on", {"device": "light.test"})
        self.skill.gui.show_text.assert_called_once_with("light.test: Successfully turned on!")

    def test_get_device_intent_aborts_on_connection_failure(self):
        """Test that get_device_intent aborts when connection check fails."""
        self.skill.ha_client.instance_available = False
        self.skill.ha_client.init_configuration.side_effect = Exception("Connection failed")
        
        message = Message("sensor.intent", {"entity": "sensor.temperature"})
        self.skill.get_device_intent(message)
        
        # Verify ha_client.handle_get_device was NOT called
        self.skill.ha_client.handle_get_device.assert_not_called()
        # Verify error messages were shown
        self.skill.gui.show_text.assert_called_with(
            "Connection to Home Assistant is not configured or unavailable. Please check skill settings."
        )

    def test_get_device_intent_proceeds_on_connection_success(self):
        """Test that get_device_intent flows through connection check, retrieves device, and speaks status."""
        self.skill.ha_client.instance_available = True
        
        # Mock a successful device retrieval
        mock_device_data = {
            "state": "23.5",
            "type": "sensor",
            "attributes": {"friendly_name": "Living Room Temperature"}
        }
        self.skill.ha_client.handle_get_device.return_value = mock_device_data
        
        message = Message("sensor.intent", {"entity": "sensor.temperature"})
        self.skill.get_device_intent(message)
        
        # Verify ha_client.handle_get_device was called with correct device
        self.skill.ha_client.handle_get_device.assert_called_once()
        call_msg = self.skill.ha_client.handle_get_device.call_args[0][0]
        self.assertEqual(call_msg.data["device"], "sensor.temperature")
        # Verify speak_dialog was called with the correct device status data
        self.skill.speak_dialog.assert_called_once_with(
            "device.status",
            data={
                "device": "Living Room Temperature",
                "type": "sensor",
                "state": "23.5",
            },
        )
        # Verify GUI was updated with the correct status text
        self.skill.gui.show_text.assert_called_once_with(
            "Living Room Temperature (sensor) is 23.5"
        )


if __name__ == "__main__":
    unittest.main()
