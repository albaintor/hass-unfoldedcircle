"""Helper functions for Unfolded Circle Devices"""

import asyncio
import logging

from homeassistant.core import HomeAssistant
from urllib.parse import urljoin, urlparse

from homeassistant.helpers.network import get_url, NoURLAvailableError

from custom_components.unfoldedcircle.const import DEFAULT_HASS_URL
from pyUnfoldedCircleRemote.dock_websocket import DockWebsocket
from pyUnfoldedCircleRemote.remote import Remote

_LOGGER = logging.getLogger(__name__)


def get_ha_websocket_url(hass: HomeAssistant) -> str:
    try:
        hass_url: str = get_url(hass)
    except NoURLAvailableError:
        hass_url = DEFAULT_HASS_URL
    url = urlparse(hass_url)
    return urljoin(f"ws://{url.netloc}", "/api/websocket")


async def validate_dock_password(remote_api: Remote, user_info) -> bool:
    """Validate"""
    dock = remote_api.get_dock_by_id(user_info.get("id"))

    websocket = DockWebsocket(
        dock._ws_endpoint,
        api_key=dock.apikey,
        dock_password=user_info.get("password"),
    )
    try:
        return await asyncio.create_task(websocket.is_password_valid())
    except Exception as ex:
        _LOGGER.error("Error occurred when validating dock: %s %s", dock.name, ex)
