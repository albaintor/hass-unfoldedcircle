"""The IntelliFire integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.error import HTTPError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .pyUnfoldedCircleRemote.remote import Remote

from . import RemoteWebsocket
from .const import DEVICE_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class UnfoldedCircleRemoteCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for an Unfolded Circle Remote device."""
    # List of events to subscribe to the websocket
    subscribe_events: dict[str, bool]

    def __init__(self, hass: HomeAssistant, unfolded_circle_remote_device) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            name=DOMAIN,
            logger=_LOGGER,
            # update_interval=DEVICE_SCAN_INTERVAL,
        )
        self.hass = hass
        self.api: Remote = unfolded_circle_remote_device
        self.data = {}
        self.remote_websocket = RemoteWebsocket(self.api.endpoint, self.api.apikey)
        self.websocket_task = None
        self.subscribe_events = {}

    async def init_websocket(self):
        # await self.api.update()
        # Check which events to listen according to enabled entities
        # HA BUG TO INVESTIGATE
        self.subscribe_events["entity_activity"] = True
        self.subscribe_events["activity_groups"] = True
        self.subscribe_events["battery_status"] = True
        #self.subscribe_events["ambient_light"] = True

        self.remote_websocket.events_to_subscribe = ["software_updates", *list(self.subscribe_events.keys())]
        _LOGGER.debug("Unfolded Circle Remote events list to subscribe %s", self.remote_websocket.events_to_subscribe)
        self.websocket_task = asyncio.create_task(
            self.remote_websocket.init_websocket(self.receive_data, self.reconnection_ws))

    def update(self, message: any):
        try:
            # TODO Avoid requesting more data : missing software updates (message format ?)
            # await self.api.update()
            # Update internal data from the message
            self.api.update_from_message(message)
            # Trigger update of entities
            self.async_set_updated_data(vars(self.api))
            asyncio.create_task(self._async_update_data()).result()
        except Exception as ex:
            _LOGGER.error("Unfolded Circle Remote error while updating entities", ex)

    def reconnection_ws(self):
        _LOGGER.debug("Unfolded Circle Remote coordinator refresh data after a period of disconnection")

        async def refresh():
            await self.api.update()
            await self._async_update_data()

        asyncio.run(refresh())
        # asyncio.run(self._async_update_data())

    def receive_data(self, message: any):
        _LOGGER.debug("Unfolded Circle Remote coordinator received data %s", message)
        self.update(message)
        # asyncio.run(self.update(message))
        # asyncio.create_task(self.update(message)).result()

    async def _async_update_data(self) -> dict[str, Any]:
        """Get the latest data from the Unfolded Circle Remote."""
        _LOGGER.debug("Unfolded Circle Remote _async_update_data")
        try:
            # await self.api.update()
            self.data = vars(self.api)
            _LOGGER.debug("Unfolded Circle Remote Data Update values")
            return vars(self.api)
        except HTTPError as err:
            if err.code == 401:
                raise ConfigEntryAuthFailed(err) from err
            raise UpdateFailed(
                f"Error communicating with Unfolded Circle Remote API {err}"
            ) from err
        except Exception as ex:
            raise UpdateFailed(
                f"Error communicating with Unfolded Circle Remote API {ex}"
            ) from ex

    async def close_websocket(self):
        try:
            if self.websocket_task:
                self.websocket_task.cancel()
            if self.remote_websocket:
                await self.remote_websocket.close_websocket()
        except Exception as ex:
            _LOGGER.error("Unfolded Circle Remote while closing websocket", ex)
