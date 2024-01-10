"""Support for SwitchBot switch."""
from math import floor
from typing import Any

from switchbot_api import (
    CeilingLightCommands,
    CommonCommands,
    Device,
    PowerState,
    Remote,
    SwitchBotAPI,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from . import SwitchbotCloudData
from .const import DOMAIN
from .coordinator import SwitchBotCoordinator
from .entity import SwitchBotCloudEntity

BRIGHTNESS_SCALE = (1, 100)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SwitchBot Cloud entry."""
    data: SwitchbotCloudData = hass.data[DOMAIN][config.entry_id]
    async_add_entities(
        _async_make_entity(data.api, device, coordinator)
        for device, coordinator in data.devices.lights
    )


class SwitchbotCloudLightEntity(SwitchBotCloudEntity, LightEntity):
    """A SwitchBot Cloud Light."""

    _device: SwitchBotCloudEntity
    _attr_name = None

    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP

    _attr_min_color_temp_kelvin = 2700
    _attr_max_color_temp_kelvin = 6500

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if ATTR_BRIGHTNESS in kwargs:
            hass_brightness = kwargs[ATTR_BRIGHTNESS]
            brightness = floor(brightness_to_value(BRIGHTNESS_SCALE, hass_brightness))

            await self.send_command(
                CeilingLightCommands.SET_BRIGHTNESS, "command", str(brightness)
            )

            self._attr_brightness = hass_brightness

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            await self.send_command(
                CeilingLightCommands.SET_COLOR_TEMPERATURE,
                "command",
                str(kwargs[ATTR_COLOR_TEMP_KELVIN]),
            )

            self._attr_color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]

        if len(kwargs) == 0:
            await self.send_command(CommonCommands.ON)

        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self.send_command(CommonCommands.OFF)
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return

        self._attr_is_on = self.coordinator.data.get("power") == PowerState.ON.value

        cloudBrigthness: float = self.coordinator.data.get("brightness", 0)
        attrBrightness = value_to_brightness(BRIGHTNESS_SCALE, cloudBrigthness)
        self._attr_brightness = attrBrightness

        temperature = self.coordinator.data.get("colorTemperature")
        self._attr_color_temp_kelvin = temperature

        self.async_write_ha_state()


@callback
def _async_make_entity(
    api: SwitchBotAPI, device: Device | Remote, coordinator: SwitchBotCoordinator
) -> SwitchbotCloudLightEntity:
    return SwitchbotCloudLightEntity(api, device, coordinator)
