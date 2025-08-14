"""Home Assistant Device Module.

This module provides the base device class for interacting with Home Assistant devices.
It defines common functionality for controlling devices and getting their state information.
"""

from ovos_utils.log import LOG
from webcolors import (  # TODO: Use ovos-color-parser when it's ready
    name_to_rgb,
    rgb_to_name,
)

from skill_homeassistant.ha_client.logic.connector import HomeAssistantConnector


class HomeAssistantDevice:
    """Home Assistant Device"""

    def __init__(  # pylint: disable=keyword-arg-before-vararg
        self,
        connector: HomeAssistantConnector,
        device_id,
        device_icon,
        device_name,
        device_state,
        device_attributes,
        device_area=None,
    ):
        """Initialize the device.

        Args:
            connector (HomeAssistantConnector): The connector to use.
            device_id (str): The id of the device.
            device_icon (str): The icon of the device.
            device_name (str): The name of the device.
            device_state (str): The state of the device.
            device_attributes (dict): The attributes of the device.
            device_area (str): Name of area device is in (None if no area)
        """
        self.connector = connector
        self.device_id = device_id
        self.device_icon = device_icon
        self.device_name = device_name
        self.device_state = device_state
        self.device_attributes = device_attributes
        self.device_area = device_area
        self.has_device_class = False
        self.device_class = None
        self.device_type = self.device_id.split(".")[0]
        self.query_device_class()
        self.connector.register_callback(self.device_id, self.callback_listener)

    def callback_listener(self, message):
        """Callback for when the device state changes."""
        event = message.get("event")
        event_type = event.get("event_type")
        if event_type == "state_changed":
            new_state = event.get("data").get("new_state")
            if new_state.get("entity_id") == self.device_id:
                self.device_state = new_state.get("state")
                self.device_attributes = new_state.get("attributes")

    def query_device_class(self):
        """Query the device class of the device."""
        if "device_class" in self.device_attributes:
            self.has_device_class = True
            self.device_class = self.device_attributes["device_class"]
        else:
            self.has_device_class = False
            self.device_class = None

    def get_has_device_class(self):
        """Get if the device has a device class."""
        return self.has_device_class

    def get_device_class(self):
        """Get the device class of the device."""
        return self.device_class

    def get_state(self):
        """Get the state of the device."""
        return self.device_state

    def get_state_json_object(self):
        """Get the state of the device as a json object."""
        return self.connector.get_device_state(self.device_id)

    def get_attribute(self, attribute):
        """Get an attribute of the device."""
        return self.device_attributes[attribute]

    def get_attributes(self):
        """Get the attributes of the device."""
        return self.device_attributes

    def get_id(self):
        """Get the id of the device."""
        return self.device_id

    def get_icon(self):
        """Get the icon of the device."""
        return self.device_icon

    def get_name(self):
        """Get the name of the device."""
        return self.device_name

    def get_supported_features(self):
        """Get the supported features of the device."""
        return self.device_attributes["supported_features"]

    def is_on(self):
        """Check if the device is on."""
        return self.device_state == "on"

    def is_off(self):
        """Check if the device is off."""
        return self.device_state == "off"

    def is_unavailable(self):
        """Check if the device is unavailable."""
        return self.device_state == "unavailable"

    def turn_on(self):
        """Turn on the device."""
        return self.connector.turn_on(self.device_id, self.device_type)

    def turn_off(self):
        """Turn off the device."""
        return self.connector.turn_off(self.device_id, self.device_type)

    def call_function(self, function_name, function_args=None):
        """Call a function of the device.

        Args:
            function_name (str): The name of the function to call.
            function_args (dict): The arguments to pass to the function.
        """
        return self.connector.call_function(self.device_id, self.device_type, function_name, function_args)

    def update_device(self):
        """Update the device."""
        device = self.connector.get_device_state(self.device_id)
        self.device_state = device["state"]
        self.device_attributes = device["attributes"]
        self.device_icon = device["attributes"].get("icon", "")
        self.device_name = device["attributes"].get("friendly_name", "")

    def set_device_attribute(self, device_id, attribute, value):
        """Set an attribute of the device.

        Args:
            device_id (str): The id of the device.
            attribute (str): The attribute to set.
            value (str): The value to set the attribute to.
        """
        device = self.get_state_json_object()
        attributes = device["attributes"]
        attributes[attribute] = value
        self.connector.set_device_state(device_id, device["state"], attributes)

    def poll(self):
        """Poll the device."""
        full_state_json = self.connector.get_device_state(self.device_id)
        if full_state_json:
            if full_state_json == "unavailable":
                LOG.warning(f"State unavailable for device: {self.device_id}")
            elif not isinstance(full_state_json, dict):
                LOG.error(f"({self.device_name}) Expected dict state but got: " f"{full_state_json}")
            else:
                self.device_state = full_state_json.get("state", "unknown")
                self.device_attributes = full_state_json.get("attributes", {})

    def get_device_display_model(self):
        """Get the display model of the device."""
        self.poll()
        return {
            "id": self.device_id,
            "name": self.device_name,
            "icon": self.device_icon,
            "state": self.device_state,
            "type": self.device_type,
            "attributes": self.device_attributes,
            "host": self.connector.host,
        }


class HomeAssistantLight(HomeAssistantDevice):
    """Home Assistant Light"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_brightness(self):
        """Get the brightness of the light."""
        return self.device_attributes.get("brightness", 0)

    def get_color_mode(self):
        """Get the color mode of the light."""
        return self.device_attributes.get("color_mode", "unknown")

    def get_color_temp(self):
        """Get the color temperature of the light."""
        return self.device_attributes.get("color_temp", 0)

    def get_effect(self):
        """Get the effect of the light."""
        return self.device_attributes.get("effect", "none")

    def get_effect_list(self):
        """Get the effect list of the light."""
        return self.device_attributes.get("effect_list", [])

    def get_hs_color(self):
        """Get the hs color of the light."""
        return self.device_attributes.get("hs_color", [0, 0])

    def get_max_mireds(self):
        """Get the max mireds of the light."""
        return self.device_attributes.get("max_mireds", 0)

    def get_min_mireds(self):
        """Get the min mireds of the light."""
        return self.device_attributes.get("min_mireds", 0)

    def get_rgb_color(self):
        """Get the rgb color of the light."""
        return self.device_attributes.get("rgb_color", [0, 0, 0])

    def get_spoken_color(self):
        """Get the spoken color value of the light."""
        color = tuple(self.get_rgb_color())
        try:
            color = rgb_to_name(color)
        except ValueError:
            color = f"RGB code {color[0]}, {color[1]}, {color[2]}"
        return color

    def get_supported_color_modes(self):
        """Get the supported color modes of the light."""
        return self.device_attributes.get("supported_color_modes", [])

    def get_xy_color(self):
        """Get the xy color of the light."""
        return self.device_attributes.get("xy_color", [0, 0])

    def set_brightness(self, brightness):
        """Set the brightness of the light.

        Args:
            brightness (int): The brightness to set the light to.
        """
        LOG.debug(f"Setting brightness to {brightness}")
        self.call_function("turn_on", {"brightness": brightness})
        self.update_device()

    def increase_brightness(self, brightness_increment: int = 10) -> int:
        """Increase the brightness of the light by the brightness increment."""
        bumped_value = self.call_function("turn_on", {"brightness_step_pct": brightness_increment})
        self.update_device()
        return bumped_value

    def decrease_brightness(self, brightness_increment: int = 10) -> int:
        """Decrease the brightness of the light by the brightness increment."""
        decreased_value = self.call_function("turn_on", {"brightness_step_pct": -brightness_increment})
        self.update_device()
        return decreased_value

    def set_color(self, color):
        """Set the color of the light.

        Args:
            color (str): The color to set the light to.
        """
        rgb = name_to_rgb(color)
        LOG.debug(f"Setting color to [{rgb.red}, {rgb.green}, {rgb.blue}]")
        self.set_rgb_color([rgb.red, rgb.green, rgb.blue])
        self.update_device()

    def set_color_mode(self, color_mode):
        """Set the color mode of the light.

        Args:
            color_mode (str): The color mode to set the light to.
        """
        self.call_function("set_color_mode", {"color_mode": color_mode})
        self.update_device()

    def set_color_temp(self, color_temp):
        """Set the color temperature of the light.

        Args:
            color_temp (int): The color temperature to set the light to.
        """
        self.call_function("set_color_temp", {"color_temp": color_temp})
        self.update_device()

    def set_effect(self, effect):
        """Set the effect of the light.

        Args:
            effect (str): The effect to set the light to.
        """
        self.call_function("set_effect", {"effect": effect})
        self.update_device()

    def set_hs_color(self, hs_color):
        """Set the hs color of the light.

        Args:
            hs_color (list): The hs color to set the light to.
        """
        self.call_function("set_hs_color", {"hs_color": hs_color})
        self.update_device()

    def set_rgb_color(self, rgb_color):
        """Set the rgb color of the light.

        Args:
            rgb_color (list): The rgb color to set the light to.
        """
        self.call_function("turn_on", {"rgb_color": rgb_color})
        self.update_device()

    def set_xy_color(self, xy_color):
        """Set the xy color of the light.

        Args:
            xy_color (list): The xy color to set the light to.
        """
        self.call_function("set_xy_color", {"xy_color": xy_color})
        self.update_device()


class HomeAssistantSwitch(HomeAssistantDevice):
    """Home Assistant Switch"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HomeAssistantSensor(HomeAssistantDevice):
    """Home Assistant Sensor"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_device_class(self):
        """Get the device class of the sensor."""
        return self.device_attributes.get("device_class", "unknown")

    def get_last_reset(self):
        """Get the last reset of the sensor."""
        return self.device_attributes.get("last_reset", "unknown")

    def get_native_value(self):
        """Get the native value of the sensor."""
        return self.device_attributes.get("native_value", "unknown")

    def get_native_unit_of_measurement(self):
        """Get the native unit of measurement of the sensor."""
        return self.device_attributes.get("native_unit_of_measurement", "unknown")

    def get_state_class(self):
        """Get the state class of the sensor."""
        return self.device_attributes.get("state_class", "unknown")

    def get_suggested_unit_of_measurement(self):
        """Get the suggested unit of measurement of the sensor."""
        return self.device_attributes.get("suggested_unit_of_measurement", "unknown")


class HomeAssistantBinarySensor(HomeAssistantDevice):
    """Home Assistant Binary Sensor"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_device_class(self):
        """Get the device class of the binary sensor."""
        return self.device_attributes.get("device_class", "unknown")


class HomeAssistantCover(HomeAssistantDevice):
    """Home Assistant Cover"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def open(self):
        """Open the cover."""
        self.call_function("open")

    def close(self):
        """Close the cover."""
        self.call_function("close")

    def set_position(self, position):
        """Set the position of the cover.

        Args:
            position (int): The position to set the cover to.
        """
        self.call_function("set_position", {"position": position})
        self.update_device()

    def stop(self):
        """Stop the cover."""
        self.call_function("stop")

    def is_opening(self):
        """Check if the cover is opening."""
        return self.device_state == "opening"

    def is_closing(self):
        """Check if the cover is closing."""
        return self.device_state == "closing"

    def is_open(self):
        """Check if the cover is open."""
        return self.device_state == "open"

    def is_closed(self):
        """Check if the cover is closed."""
        return self.device_state == "closed"

    def get_position(self):
        """Get the position of the cover."""
        return self.device_attributes["current_position"]


class HomeAssistantMediaPlayer(HomeAssistantDevice):
    """Home Assistant Media Player"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_media_title(self):
        """Get the media title of the media player."""
        return self.device_attributes["media_title"]

    def get_media_artist(self):
        """Get the media artist of the media player."""
        return self.device_attributes["media_artist"]

    def get_media_album_name(self):
        """Get the media album name of the media player."""
        return self.device_attributes["media_album_name"]

    def get_media_series_title(self):
        """Get the media series title of the media player."""
        return self.device_attributes["media_series_title"]

    def get_media_season(self):
        """Get the media season of the media player."""
        return self.device_attributes["media_season"]

    def get_media_episode(self):
        """Get the media episode of the media player."""
        return self.device_attributes["media_episode"]

    def get_media_channel(self):
        """Get the media channel of the media player."""
        return self.device_attributes["media_channel"]

    def get_media_content_id(self):
        """Get the media content id of the media player."""
        return self.device_attributes["media_content_id"]

    def get_media_content_type(self):
        """Get the media content type of the media player."""
        return self.device_attributes["media_content_type"]

    def get_media_duration(self):
        """Get the media duration of the media player."""
        return self.device_attributes["media_duration"]

    def get_media_position(self):
        """Get the media position of the media player."""
        return self.device_attributes["media_position"]

    def get_media_position_updated_at(self):
        """Get the media position updated at of the media player."""
        return self.device_attributes["media_position_updated_at"]

    def get_is_volume_muted(self):
        """Get the is volume muted of the media player."""
        return self.device_attributes["is_volume_muted"]

    def get_volume_level(self):
        """Get the volume level of the media player."""
        return self.device_attributes["volume_level"]

    def get_app_id(self):
        """Get the app id of the media player."""
        return self.device_attributes["app_id"]

    def get_app_name(self):
        """Get the app name of the media player."""
        return self.device_attributes["app_name"]


class HomeAssistantClimate(HomeAssistantDevice):
    """Home Assistant Climate"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_temperature(self, temperature):
        """Set the temperature of the climate device.

        Args:
            temperature (float): The temperature to set the climate device to.
        """
        self.call_function("set_temperature", {"temperature": temperature})
        self.update_device()

    def set_hvac_mode(self, hvac_mode):
        """Set the hvac mode of the climate device.

        Args:
            hvac_mode (str): The hvac mode to set the climate device to.
        """
        self.call_function("set_hvac_mode", {"hvac_mode": hvac_mode})
        self.update_device()

    def set_fan_mode(self, fan_mode):
        """Set the fan mode of the climate device.

        Args:
            fan_mode (str): The fan mode to set the climate device to.
        """
        self.call_function("set_fan_mode", {"fan_mode": fan_mode})
        self.update_device()

    def set_swing_mode(self, swing_mode):
        """Set the swing mode of the climate device.

        Args:
            swing_mode (str): The swing mode to set the climate device to.
        """
        self.call_function("set_swing_mode", {"swing_mode": swing_mode})
        self.update_device()

    def set_preset_mode(self, preset_mode):
        """Set the preset mode of the climate device.

        Args:
            preset_mode (str): The preset mode to set the climate device to.
        """
        self.call_function("set_preset_mode", {"preset_mode": preset_mode})
        self.update_device()

    def set_aux_heat(self, aux_heat):
        """Set the aux heat of the climate device.

        Args:
            aux_heat (bool): The aux heat to set the climate device to.
        """
        self.call_function("set_aux_heat", {"aux_heat": aux_heat})
        self.update_device()

    def set_humidity(self, humidity):
        """Set the humidity of the climate device.

        Args:
            humidity (float): The humidity to set the climate device to.
        """
        self.call_function("set_humidity", {"humidity": humidity})
        self.update_device()

    def set_target_humidity(self, target_humidity):
        """ Set the target humidity of the climate device.\

        Args:
            target_humidity (float): The target humidity to set the climate device to.
        """
        self.call_function("set_target_humidity", {"target_humidity": target_humidity})
        self.update_device()

    def set_target_temp_low(self, target_temp_low):
        """Set the target temp low of the climate device.

        Args:
            target_temp_low (float): The target temp low to set the climate device to.
        """
        self.call_function("set_target_temp_low", {"target_temp_low": target_temp_low})
        self.update_device()

    def set_target_temp_high(self, target_temp_high):
        """Set the target temp high of the climate device.

        Args:
            target_temp_high (float): The target temp high to set the climate device to.
        """
        self.call_function("set_target_temp_high", {"target_temp_high": target_temp_high})
        self.update_device()

    def get_current_temperature(self):
        """Get the current temperature of the climate device."""
        return self.device_attributes["current_temperature"]

    def get_current_humidity(self):
        """Get the current humidity of the climate device."""
        return self.device_attributes["current_humidity"]

    def get_temperature(self):
        """Get the temperature of the climate device."""
        return self.device_attributes["temperature"]

    def get_target_temp_low(self):
        """Get the target temp low of the climate device."""
        return self.device_attributes["target_temp_low"]

    def get_target_temp_high(self):
        """Get the target temp high of the climate device."""
        return self.device_attributes["target_temp_high"]

    def get_humidity(self):
        """Get the humidity of the climate device."""
        return self.device_attributes["humidity"]

    def get_target_humidity(self):
        """Get the target humidity of the climate device."""
        return self.device_attributes["target_humidity"]

    def get_min_temp(self):
        """Get the min temp of the climate device."""
        return self.device_attributes["min_temp"]

    def get_max_temp(self):
        """Get the max temp of the climate device."""
        return self.device_attributes["max_temp"]

    def get_target_temp_step(self):
        """Get the target temp step of the climate device."""
        return self.device_attributes["target_temp_step"]

    def get_hvac_mode(self):
        """Get the hvac mode of the climate device."""
        return self.device_attributes["hvac_mode"]

    def get_hvac_modes(self):
        """Get the hvac modes of the climate device."""
        return self.device_attributes["hvac_modes"]

    def get_fan_mode(self):
        """Get the fan mode of the climate device."""
        return self.device_attributes["fan_mode"]


class HomeAssistantVacuum(HomeAssistantDevice):
    """Home Assistant Vacuum"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self):
        """Start the vacuum."""
        self.call_function("start")

    def pause(self):
        """Pause the vacuum."""
        self.call_function("pause")

    def stop(self):
        """Stop the vacuum."""
        self.call_function("stop")

    def return_to_base(self):
        """Return the vacuum to base."""
        self.call_function("return_to_base")

    def set_fan_speed(self, fan_speed):
        """Set the fan speed of the vacuum.

        Args:
            fan_speed (str): The fan speed to set the vacuum to.
        """
        self.set_device_attribute(self.device_id, "fan_speed", fan_speed)
        self.update_device()

    def send_command(self, command, params):
        """Send a command to the vacuum.

        Args:
            command (str): The command to send to the vacuum.
            params (dict): The parameters to send to the vacuum.
        """
        self.call_function("send_command", {"command": command, "params": params})

    def get_battery_level(self):
        """Get the battery level of the vacuum."""
        return self.device_attributes["battery_level"]

    def get_fan_speed(self):
        """Get the fan speed of the vacuum."""
        return self.device_attributes["fan_speed"]

    def get_fan_speed_list(self):
        """Get the fan speed list of the vacuum."""
        return self.device_attributes["fan_speed_list"]

    def get_status(self):
        """Get the status of the vacuum."""
        return self.device_attributes["status"]


class HomeAssistantCamera(HomeAssistantDevice):
    """Home Assistant Camera"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HomeAssistantScene(HomeAssistantDevice):
    """Home Assistant Scene"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def turn_off(self):
        LOG.warning("Request to turn off a scene. This is not supported - scenes can only be activated.")
        return


class HomeAssistantAutomation(HomeAssistantDevice):
    """Home Assistant Automation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def turn_off(self):
        LOG.warning("Request to turn off an automation. This is not supported, as it will disable it instead.")
        return
