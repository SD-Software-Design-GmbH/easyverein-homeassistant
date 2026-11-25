"""Config flow: just the API token."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyVereinAuthError, EasyVereinClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema({vol.Required(CONF_TOKEN): str})


class EasyVereinConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _detail = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input:
            if token := await self._validate(user_input[CONF_TOKEN], errors):
                return self.async_create_entry(
                    title="easyVerein", data={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA,
            errors=errors,
            description_placeholders={"detail": self._detail},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input:
            if token := await self._validate(user_input[CONF_TOKEN], errors):
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=SCHEMA,
            errors=errors,
            description_placeholders={"detail": self._detail},
        )

    async def _validate(self, token: str, errors: dict[str, str]) -> str | None:
        """Returns the (possibly rotated) token, or None and fills `errors`."""
        client = EasyVereinClient(async_get_clientsession(self.hass), token.strip())
        try:
            return await client.refresh_token()
        except EasyVereinAuthError:
            errors["base"] = "invalid_auth"
        except aiohttp.ClientResponseError as err:
            _LOGGER.warning("easyVerein answered with an error: %r", err)
            self._detail = f"HTTP {err.status}"
            errors["base"] = "http_error"
        except aiohttp.ClientError as err:
            _LOGGER.warning("Cannot reach easyVerein: %r", err)
            self._detail = type(err).__name__
            errors["base"] = "cannot_connect"
        return None
