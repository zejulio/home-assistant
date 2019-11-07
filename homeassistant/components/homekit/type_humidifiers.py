"""Class to hold all humidifier accessories."""
import logging

from pyhap.const import CATEGORY_HUMIDIFIER

from homeassistant.components.humidity.const import (
    ATTR_HUMIDITY,
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDIFIER_ACTIONS,
    ATTR_HUMIDIFIER_MODE,
    ATTR_HUMIDIFIER_MODES,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    CURRENT_HUMIDIFIER_DRY,
    CURRENT_HUMIDIFIER_HUMIDIFY,
    CURRENT_HUMIDIFIER_IDLE,
    CURRENT_HUMIDIFIER_OFF,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DOMAIN,
    HUMIDIFIER_MODE_OFF,
    HUMIDIFIER_MODE_DRY,
    HUMIDIFIER_MODE_HUMIDIFY,
    HUMIDIFIER_MODE_HUMIDIFY_DRY,
    SERVICE_SET_HUMIDIFIER_MODE,
    SERVICE_SET_HUMIDITY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)

from . import TYPES
from .accessories import HomeAccessory, debounce
from .const import (
    CHAR_ACTIVE,
    CHAR_DEHUMIDIFIER_THRESHOLD_HUMIDITY,
    CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER,
    CHAR_CURRENT_HUMIDITY,
    CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
    CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
    PROP_MAX_VALUE,
    PROP_MIN_STEP,
    PROP_MIN_VALUE,
    SERV_HUMIDIFIER_DEHUMIDIFIER,
)

_LOGGER = logging.getLogger(__name__)

HC_HASS_TO_HOMEKIT = {
    HUMIDIFIER_MODE_HUMIDIFY_DRY: 0,
    HUMIDIFIER_MODE_HUMIDIFY: 1,
    HUMIDIFIER_MODE_DRY: 2,
}
HC_HOMEKIT_TO_HASS = {c: s for s, c in HC_HASS_TO_HOMEKIT.items()}
HC_DEFAULT_MODE = 0

HC_HASS_TO_HOMEKIT_ACTION = {
    CURRENT_HUMIDIFIER_OFF: 0,
    CURRENT_HUMIDIFIER_IDLE: 1,
    CURRENT_HUMIDIFIER_HUMIDIFY: 2,
    CURRENT_HUMIDIFIER_DRY: 3,
}


@TYPES.register("HumidifierDehumidifier")
class HumidifierDehumidifier(HomeAccessory):
    """Generate a HumidifierDehumidifier accessory for a humidity."""

    def __init__(self, *args):
        """Initialize a HumidifierDehumidifier accessory object."""
        super().__init__(*args, category=CATEGORY_HUMIDIFIER)
        self._flag_humidifier_dehumidifier = False
        self._flag_humidity = False
        self._flag_active = False
        self._last_active_mode = HC_DEFAULT_MODE
        min_humidity, max_humidity = self.get_humidity_range()

        self.chars = []

        target_humidity_char = CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY
        modes = self.hass.states.get(self.entity_id).attributes.get(ATTR_HUMIDIFIER_MODES)
        if modes and HUMIDIFIER_MODE_DRY in modes and HUMIDIFIER_MODE_HUMIDIFY not in modes:
            target_humidity_char = CHAR_DEHUMIDIFIER_THRESHOLD_HUMIDITY

        self.chars.append(target_humidity_char)

        serv_humidifier_dehumidifier = self.add_preload_service(SERV_HUMIDIFIER_DEHUMIDIFIER, self.chars)

        # Current and target mode characteristics
        self.char_current_humidifier_dehumidifier = serv_humidifier_dehumidifier.configure_char(
            CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER, value=0
        )
        self.char_target_humidifier_dehumidifier = serv_humidifier_dehumidifier.configure_char(
            CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER, value=0, setter_callback=self.set_humidifier_dehumidifier
        )

        # Current and target humidity characteristics
        self.char_current_humidity = serv_humidifier_dehumidifier.configure_char(
            CHAR_CURRENT_HUMIDITY, value=45
        )

        self.char_target_humidity = serv_humidifier_dehumidifier.configure_char(
            target_humidity_char,
            value=45,
            properties={
                PROP_MIN_VALUE: min_humidity,
                PROP_MAX_VALUE: max_humidity,
                PROP_MIN_STEP: 1,
            },
            setter_callback=self.set_target_humidity,
        )

        # Active/inactive characteristics
        self.char_active = serv_humidifier_dehumidifier.configure_char(
            CHAR_ACTIVE, value=False, setter_callback=self.set_active
        )

    def get_humidity_range(self):
        """Return min and max humidity range."""
        max_humidity = self.hass.states.get(self.entity_id).attributes.get(ATTR_MAX_HUMIDITY)
        max_humidity = round(max_humidity if max_humidity else DEFAULT_MAX_HUMIDITY)

        min_humidity = self.hass.states.get(self.entity_id).attributes.get(ATTR_MIN_HUMIDITY)
        min_humidity = round(min_humidity if min_humidity else DEFAULT_MIN_HUMIDITY)

        return min_humidity, max_humidity

    def set_humidifier_dehumidifier(self, value):
        """Change operation mode to value if call came from HomeKit."""
        _LOGGER.debug("%s: Set humidifier-dehumidifier to %d", self.entity_id, value)
        self._flag_humidifier_dehumidifier = True
        hass_value = HC_HOMEKIT_TO_HASS[value]
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_HUMIDIFIER_MODE: hass_value}
        self.call_service(
            DOMAIN, SERVICE_SET_HUMIDIFIER_MODE, params, hass_value
        )

    @debounce
    def set_target_humidity(self, humidity):
        """Set target humidity to value if call came from HomeKit."""
        _LOGGER.debug("%s: Set target humidity to %.1f%%", self.entity_id, humidity)
        self._flag_humidity = True
        params = {ATTR_ENTITY_ID: self.entity_id, ATTR_HUMIDITY: humidity}
        self.call_service(
            DOMAIN,
            SERVICE_SET_HUMIDITY,
            params,
            f"{humidity}%",
        )

    def set_active(self, value):
        """Turn device on or off if call came from HomeKit."""
        _LOGGER.debug("%s: Set switch state to %s", self.entity_id, value)
        self._flag_active = True
        params = {ATTR_ENTITY_ID: self.entity_id}
        service = SERVICE_TURN_ON if value else SERVICE_TURN_OFF
        self.call_service(DOMAIN, service, params)

    def update_state(self, new_state):
        """Update humidifier state after state changed."""
        # Update current humidity
        current_humidity = new_state.attributes.get(ATTR_CURRENT_HUMIDITY)
        if isinstance(current_humidity, (int, float)):
            self.char_current_humidity.set_value(current_humidity)

        # Update target humidity
        target_humidity = new_state.attributes.get(ATTR_HUMIDITY)
        if isinstance(target_humidity, (int, float)):
            if not self._flag_humidity:
                self.char_target_humidity.set_value(target_humidity)
        self._flag_humidity = False

        # Update target operation mode
        humidifier_mode = new_state.state
        if humidifier_mode:
            if not self._flag_humidifier_dehumidifier:
                if humidifier_mode != HUMIDIFIER_MODE_OFF:
                    self._last_active_mode = (
                        HC_HASS_TO_HOMEKIT[humidifier_mode]
                        if humidifier_mode in HC_HASS_TO_HOMEKIT
                        else HC_DEFAULT_MODE
                    )
                self.char_target_humidifier_dehumidifier.set_value(self._last_active_mode)
            if not self._flag_active:
                self.char_active.set_value(humidifier_mode != HUMIDIFIER_MODE_OFF)
        self._flag_humidifier_dehumidifier = False
        self._flag_active = False

        # Set current operation mode for supported hygrostats
        if humidifier_mode and humidifier_mode == HUMIDIFIER_MODE_OFF:
            humidifier_action = CURRENT_HUMIDIFIER_OFF
        else:
            humidifier_action = new_state.attributes.get(ATTR_HUMIDIFIER_ACTIONS)
        if humidifier_action:
            self.char_current_humidifier_dehumidifier.set_value(
                HC_HASS_TO_HOMEKIT_ACTION[humidifier_action]
            )
