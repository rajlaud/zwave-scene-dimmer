"""The ZWave Scene Dimmer integration."""
import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant

from .const import DEFAULT_DELAY, DEFAULT_STEP, DOMAIN

_SCENE_SCHEMA = vol.Schema(
    {
        vol.Required("start_scene_id"): int,
        vol.Required("stop_scene_id"): int,
        vol.Optional("start_scene_data"): int,
        vol.Optional("stop_scene_data"): int,
    }
)

_DIMMER_SCHEMA = vol.Schema(
    {
        vol.Required("light_id"): cv.entity_id,
        vol.Required("bright"): _SCENE_SCHEMA,
        vol.Required("dim"): _SCENE_SCHEMA,
        vol.Optional("step", default=DEFAULT_STEP): int,
        vol.Optional("delay", default=DEFAULT_DELAY): float,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: {"delay": float, cv.entity_id: _DIMMER_SCHEMA}}, extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


def _scenes(dimmer):
    """Parse configuration into tuples."""
    start_tuple = (dimmer.get("start_scene_id"), dimmer.get("start_scene_data"))
    stop_tuple = (dimmer.get("stop_scene_id"), dimmer.get("stop_scene_data"))
    return (start_tuple, stop_tuple)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the ZWave Scene Dimmer component."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = []

    dimmers = config.get(DOMAIN, {})

    for entity_id in dimmers:
        _LOGGER.debug("Setting up dimmer: %s", entity_id)
        dimmer = dimmers.get(entity_id)
        dim_tuples = _scenes(dimmer.get("dim"))
        bright_tuples = _scenes(dimmer.get("bright"))
        dim = Dimmer(
            hass,
            entity_id,
            dimmer.get("light_id"),
            bright_tuples,
            dim_tuples,
            dimmer.get("step"),
            dimmer.get("delay"),
        )
        await dim.start_listening()
        hass.data[DOMAIN].append(dim)
    return True


class Dimmer:
    """A class to dim or brighten between two scenes."""

    def __init__(
        self, hass, switch_id, light_id, bright_scenes, dim_scenes, step, delay
    ):
        """Initialize Dimmer. All parameters required."""
        self.hass = hass
        self.bright = False
        self.dim = False
        self.switch_id = switch_id
        self.light_id = light_id
        self.scenes = {
            bright_scenes[0]: lambda: self.start("bright"),
            bright_scenes[1]: lambda: self.stop("bright"),
            dim_scenes[0]: lambda: self.start("dim"),
            dim_scenes[1]: lambda: self.stop("dim"),
        }
        self.step = int(step)
        self.delay = delay

    async def scene_listener(self, event):
        """Consume zwave scene events."""
        switch_id = event.data.get("entity_id")
        scene_id = event.data.get("scene_id")
        scene_data = event.data.get("scene_data")
        timestamp = event.data.get("time_fired")

        if switch_id != self.switch_id:
            _LOGGER.debug("Ignoring switch_id: %s", switch_id)
            return

        scene = (scene_id, scene_data)
        if scene in self.scenes:
            _LOGGER.debug("Got scene: %s at timestamp: %s", scene, timestamp)
            await self.scenes[scene]()
            return

        _LOGGER.debug("Ignoring scene: %s", (scene_id, scene_data))

    async def start(self, cmd):
        """Start brightening or dimming."""
        if cmd == "bright":
            self.bright = True
        else:
            self.dim = True

        self.hass.async_create_task(self.adjust_task(cmd))

    async def stop(self, cmd):
        """Stop brightening or dimming."""
        if cmd == "bright":
            self.bright = False
        else:
            self.dim = False

    async def adjust_task(self, cmd):
        """Adjust light until told to stop."""
        count = 0
        while self.bright if cmd == "bright" else self.dim:
            step = self.step if cmd == "bright" else -self.step
            data = {"entity_id": self.light_id, "brightness_step": step}
            await self.hass.services.async_call("light", "turn_on", data, blocking=True)
            count += 1
            await asyncio.sleep(self.delay)
        _LOGGER.debug("Called %s %s times", count, cmd)

    async def start_listening(self):
        """Begin listening for zwave scene events."""
        _LOGGER.debug("Activated scene listener for: %s", self.switch_id)
        self.hass.bus.async_listen("zwave.scene_activated", self.scene_listener)
