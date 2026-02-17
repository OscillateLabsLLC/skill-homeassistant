# Home Assistant Skill

[![Status: Active](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/OscillateLabsLLC/.github/blob/main/SUPPORT_STATUS.md)

Control your Home Assistant smart home devices through OVOS or Neon.AI voice assistants.

This unified skill replaces the legacy `neon-homeassistant-skill` and `ovos-PHAL-plugin-homeassistant`. **Note: Do not install this skill alongside the legacy versions.**

## Features

- Control lights (on/off, brightness, color)
- Control switches and outlets
- Monitor sensors
- Control covers (open/close, position)
- Silent mode for specific devices
- Support for Home Assistant Assist API

## Installation on Neon

You can `pip install neon-homeassistant-skill`, or handle the installation from the `~/.config/neon/neon.yaml` file if you prefer:

```yaml
skills:
  default_skills:
    - skill-homeassistant # Optionally with a version, such as skill-homeassistant==0.1.0
```

## Configuration

### Authentication Using a Long-lived Token

We recommend using a [long-lived token for Home Assistant](https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token). This provides persistent access without requiring re-authentication. Configure it in your skill settings file:

- OVOS: `~/.config/mycroft/skills/skill-homeassistant/settings.json`
- Neon: `~/.config/neon/skills/neon_homeassistant_skill/settings.json`

```json
{
  "api_key": "<HA_LONG_LIVED_TOKEN>",
  "host": "<HA_IP_OR_HOSTNAME>"
}
```

### Configuration Options

All available settings with their defaults:

```jsonc
{
  "host": "", // Home Assistant instance URL - required, no default
  "api_key": "", // Long-lived access token - required, no default
  "disable_intents": false, // Disable all Home Assistant intents. In most cases, you should just uninstall the skill instead of setting this to true.
  "silent_entities": [], // List of entities to control without voice confirmation
  "brightness_increment": 10, // Percentage to change brightness by
  "search_confidence_threshold": 0.5, // Minimum confidence for entity matching, from 0 to 1 (correlates to a percentage)
  "assist_only": true, // Only pull entities exposed to Home Assistant Assist
  "timeout": 5, // Timeout for Home Assistant API requests in seconds
  "log_level": "INFO" // Logging level (DEBUG, INFO, WARNING, ERROR)
}
```

### Hostname Considerations

Mycroft Mark II may not support `.local` hostnames (e.g., `homeassistant.local`). Options include:

1. Use the IP address of your Home Assistant instance (recommended for local access)
2. Use your Nabu Casa DNS if you have a subscription (requires internet connectivity)
3. Use a local DNS server that resolves to your Home Assistant instance

## Usage

### Voice Commands

#### Lights

- "Turn on/off [device name]"
- "Set [device name] brightness to [X] percent"
- "Increase/decrease [device name] brightness"
- "What color is [device name]?"
- "Set [device name] color to [color]"
- "What's the brightness of [device name]?"

#### Switches

- "Turn on/off [device name]"
- "Toggle [device name]"

#### Covers

- "Open/Close [device name]"
- "Set [device name] position to [X] percent"
- "Stop [device name]"

#### Sensors

- "What's the temperature in [sensor name]?"
- "What's the status of [sensor name]?"

#### Home Assistant Assist

- "Ask Home Assistant [command]" (passes command directly to HA Assist API)

### Silent Mode

Add devices to the `silent_entities` list to control them without voice feedback:

```json
{
  "silent_entities": ["light.kitchen", "switch.office"]
}
```

### Disabling Intents

If you don't want the skill's intents enabled (e.g., when shipping in a voice assistant image), set `disable_intents` to true:

```json
{
  "disable_intents": true
}
```

## Troubleshooting

### Common Issues

1. **Connection Failures**

   - Verify your Home Assistant instance is reachable
   - Check the host URL format (should include protocol, e.g., `https://`)
   - Ensure your token has the required permissions

2. **Entity Not Found**

   - Check if the entity is exposed to Home Assistant Assist
   - Verify the entity name matches exactly
   - Try using the entity's friendly name

3. **Authentication Issues**
   - For long-lived tokens: Verify the token is valid and not expired
   - For OAuth: Try re-authenticating with "connect to home assistant"

### Debug Mode

Enable debug logging for more detailed information:

```json
{
  "debug": true,
  "log_level": "DEBUG"
}
```

## Upcoming Features

- Vacuum functions
- HVAC functions
- Media player control
- Camera integration

## Contributing

Contributions are very welcome! Please read our contributing guidelines and submit pull requests to our GitHub repository.

## License

Apache License 2.0
