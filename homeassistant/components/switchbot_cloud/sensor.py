"""Support for SwitchBot sensors."""
from __future__ import annotations

from switchbot_api import Device, Remote, SwitchBotAPI

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SwitchbotCloudData
from .const import DOMAIN
from .coordinator import SwitchBotCoordinator
from .entity import SwitchBotCloudEntity

SENSOR_TYPES: dict[str, SensorEntityDescription] = {
    "voltage": SensorEntityDescription(
        key="voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
    ),
    "electricCurrent": SensorEntityDescription(
        key="amperage",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "electricityOfDay": SensorEntityDescription(
        key="elecricityOfDay",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
    ),
    # This is documented by https://github.com/OpenWonderLabs/SwitchBotAPI#plug-mini-jp-1
    # to return a "daily total", but in my testing it reported momentary draw.
    "weight": SensorEntityDescription(
        key="dayWattsUsed",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Switchbot Cloud sensor based on a config entry."""
    data: SwitchbotCloudData = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for device, coordinator in data.devices.sensors:
        for sensor in SENSOR_TYPES:
            entities.append(_async_make_entity(data.api, device, coordinator, sensor))

    async_add_entities(entities)


class SwitchBotCloudSensor(SwitchBotCloudEntity, SensorEntity):
    """Representation of a Switchbot Cloud sensor."""

    def __init__(
        self,
        api: SwitchBotAPI,
        device: Device | Remote,
        coordinator: SwitchBotCoordinator,
        sensor: str,
    ) -> None:
        """Initialize the Switchbot sensor."""
        super().__init__(api, device, coordinator)

        self._sensor = sensor
        self._attr_unique_id = f"{super().unique_id}-{sensor}"
        self.entity_description = SENSOR_TYPES[sensor]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return

        value = self.coordinator.data.get(self._sensor)

        if self._sensor == "electricCurrent":
            value = value / 10  # type: ignore[operator]
            # The api returns values that seemed scale by a factor of 10. Plug with my kotatsu is reporting a 50A draw; which given a 40A breaker for my whole appartament, is rather impossible.

        self._attr_native_value = value

        self.async_write_ha_state()


@callback
def _async_make_entity(
    api: SwitchBotAPI,
    device: Device | Remote,
    coordinator: SwitchBotCoordinator,
    sensor: str,
) -> SwitchBotCloudSensor:
    return SwitchBotCloudSensor(api, device, coordinator, sensor)
