"""Test different accessory types: Thermostats."""
from collections import namedtuple

import pytest

from pyhap.const import CATEGORY_HUMIDIFIER

from homeassistant.components.humidifier.const import (
    ATTR_HUMIDITY,
    ATTR_CURRENT_HUMIDITY,
    ATTR_HUMIDIFIER_ACTION,
    ATTR_OPERATION_MODE,
    ATTR_OPERATION_MODES,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    ATTR_WATER_LEVEL,
    CURRENT_HUMIDIFIER_DRY,
    CURRENT_HUMIDIFIER_HUMIDIFY,
    CURRENT_HUMIDIFIER_IDLE,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DOMAIN,
    OPERATION_MODE_DRY,
    OPERATION_MODE_HUMIDIFY,
    OPERATION_MODE_HUMIDIFY_DRY,
    OPERATION_MODE_OFF,
)
from homeassistant.components.homekit.const import (
    ATTR_VALUE,
    PROP_MAX_VALUE,
    PROP_MIN_STEP,
    PROP_MIN_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES

from tests.common import async_mock_service
from tests.components.homekit.common import patch_debounce


@pytest.fixture(scope="module")
def cls():
    """Patch debounce decorator during import of type_humidifiers."""
    patcher = patch_debounce()
    patcher.start()
    _import = __import__(
        "homeassistant.components.homekit.type_humidifiers",
        fromlist=["HumidifierDehumidifier"],
    )
    patcher_tuple = namedtuple("Cls", ["hygrostat"])
    yield patcher_tuple(hygrostat=_import.HumidifierDehumidifier)
    patcher.stop()


async def test_hygrostat(hass, hk_driver, cls, events):
    """Test if accessory and HA are updated accordingly."""
    entity_id = "humidifier.test"

    hass.states.async_set(entity_id, OPERATION_MODE_OFF)
    await hass.async_block_till_done()
    acc = cls.hygrostat(hass, hk_driver, "HumidifierDehumidifier", entity_id, 2, None)
    await hass.async_add_job(acc.run)
    await hass.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == CATEGORY_HUMIDIFIER

    assert acc.char_current_humidifier_dehumidifier.value == 0
    assert acc.char_target_humidifier_dehumidifier.value == 0
    assert acc.char_current_humidity.value == 45.0
    assert acc.char_target_humidity.value == 45.0
    assert acc.char_active.value is False

    assert acc.char_target_humidity.properties[PROP_MAX_VALUE] == DEFAULT_MAX_HUMIDITY
    assert acc.char_target_humidity.properties[PROP_MIN_VALUE] == DEFAULT_MIN_HUMIDITY
    assert acc.char_target_humidity.properties[PROP_MIN_STEP] == 1.0

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY,
        {
            ATTR_HUMIDITY: 47.0,
            ATTR_CURRENT_HUMIDITY: 32.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_HUMIDIFY,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 47.0
    assert acc.char_current_humidifier_dehumidifier.value == 2
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert acc.char_current_humidity.value == 32.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY,
        {
            ATTR_HUMIDITY: 37.0,
            ATTR_CURRENT_HUMIDITY: 38.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_IDLE,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 37.0
    assert acc.char_current_humidifier_dehumidifier.value == 1
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert acc.char_current_humidity.value == 38.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_DRY,
        {
            ATTR_HUMIDITY: 30.0,
            ATTR_CURRENT_HUMIDITY: 35.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_DRY,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 30.0
    assert acc.char_current_humidifier_dehumidifier.value == 3
    assert acc.char_target_humidifier_dehumidifier.value == 2
    assert acc.char_current_humidity.value == 35.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_DRY,
        {
            ATTR_HUMIDITY: 40.0,
            ATTR_CURRENT_HUMIDITY: 39.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_IDLE,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 40.0
    assert acc.char_current_humidifier_dehumidifier.value == 1
    assert acc.char_target_humidifier_dehumidifier.value == 2
    assert acc.char_current_humidity.value == 39.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_OFF,
        {ATTR_HUMIDITY: 42.0, ATTR_CURRENT_HUMIDITY: 38.0},
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 42.0
    assert acc.char_current_humidifier_dehumidifier.value == 0
    assert acc.char_target_humidifier_dehumidifier.value == 2
    assert acc.char_current_humidity.value == 38.0
    assert acc.char_active.value is False

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY_DRY,
        {
            ATTR_OPERATION_MODES: [OPERATION_MODE_HUMIDIFY, OPERATION_MODE_DRY],
            ATTR_HUMIDITY: 42.0,
            ATTR_CURRENT_HUMIDITY: 38.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_HUMIDIFY,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 42.0
    assert acc.char_current_humidifier_dehumidifier.value == 2
    assert acc.char_target_humidifier_dehumidifier.value == 0
    assert acc.char_current_humidity.value == 38.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY_DRY,
        {
            ATTR_OPERATION_MODES: [OPERATION_MODE_HUMIDIFY, OPERATION_MODE_DRY],
            ATTR_HUMIDITY: 42.0,
            ATTR_CURRENT_HUMIDITY: 45.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_DRY,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 42.0
    assert acc.char_current_humidifier_dehumidifier.value == 3
    assert acc.char_target_humidifier_dehumidifier.value == 0
    assert acc.char_current_humidity.value == 45.0
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY_DRY,
        {
            ATTR_OPERATION_MODES: [OPERATION_MODE_HUMIDIFY, OPERATION_MODE_DRY],
            ATTR_HUMIDITY: 42.0,
            ATTR_CURRENT_HUMIDITY: 42.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_IDLE,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_target_humidity.value == 42.0
    assert acc.char_current_humidifier_dehumidifier.value == 1
    assert acc.char_target_humidifier_dehumidifier.value == 0
    assert acc.char_current_humidity.value == 42.0
    assert acc.char_active.value is True

    # Set from HomeKit
    call_set_humidity = async_mock_service(hass, DOMAIN, "set_humidity")
    call_set_operation_mode = async_mock_service(hass, DOMAIN, "set_operation_mode")

    await hass.async_add_job(acc.char_target_humidity.client_update_value, 39.0)
    await hass.async_block_till_done()
    assert call_set_humidity
    assert call_set_humidity[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_set_humidity[0].data[ATTR_HUMIDITY] == 39.0
    assert acc.char_target_humidity.value == 39.0
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] == "39.0%"

    await hass.async_add_job(
        acc.char_target_humidifier_dehumidifier.client_update_value, 1
    )
    await hass.async_block_till_done()
    assert call_set_operation_mode
    assert call_set_operation_mode[0].data[ATTR_ENTITY_ID] == entity_id
    assert (
        call_set_operation_mode[0].data[ATTR_OPERATION_MODE] == OPERATION_MODE_HUMIDIFY
    )
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] == OPERATION_MODE_HUMIDIFY


async def test_humidifier_water_level(hass, hk_driver, cls, events):
    """Test if water level is updated accordingly."""
    entity_id = "humidifier.test"

    hass.states.async_set(entity_id, OPERATION_MODE_OFF, {ATTR_SUPPORTED_FEATURES: 0})
    await hass.async_block_till_done()
    acc = cls.hygrostat(hass, hk_driver, "HumidifierDehumidifier", entity_id, 2, None)
    await hass.async_add_job(acc.run)
    await hass.async_block_till_done()

    assert acc.char_water_level == None

    entity_id = "humidifier.test1"

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY,
        {
            ATTR_HUMIDITY: 47.0,
            ATTR_CURRENT_HUMIDITY: 32.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_HUMIDIFY,
            ATTR_SUPPORTED_FEATURES: 17,
            ATTR_WATER_LEVEL: 70,
        },
    )
    await hass.async_block_till_done()
    acc = cls.hygrostat(hass, hk_driver, "HumidifierDehumidifier", entity_id, 2, None)
    await hass.async_add_job(acc.run)
    await hass.async_block_till_done()

    assert acc.char_water_level.value == 70.0

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY,
        {
            ATTR_HUMIDITY: 47.0,
            ATTR_CURRENT_HUMIDITY: 32.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_HUMIDIFY,
            ATTR_SUPPORTED_FEATURES: 17,
            ATTR_WATER_LEVEL: 65,
        },
    )
    await hass.async_block_till_done()

    assert acc.char_water_level.value == 65.0


async def test_hygrostat_power_state(hass, hk_driver, cls, events):
    """Test if accessory and HA are updated accordingly."""
    entity_id = "humidifier.test"

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_HUMIDIFY,
        {
            ATTR_OPERATION_MODE: OPERATION_MODE_HUMIDIFY,
            ATTR_HUMIDITY: 43.0,
            ATTR_CURRENT_HUMIDITY: 38.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_HUMIDIFY,
        },
    )
    await hass.async_block_till_done()
    acc = cls.hygrostat(hass, hk_driver, "HumidifierDehumidifier", entity_id, 2, None)
    await hass.async_add_job(acc.run)
    await hass.async_block_till_done()

    assert acc.char_current_humidifier_dehumidifier.value == 2
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert acc.char_active.value is True

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_OFF,
        {
            ATTR_OPERATION_MODE: OPERATION_MODE_HUMIDIFY,
            ATTR_HUMIDITY: 43.0,
            ATTR_CURRENT_HUMIDITY: 38.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_IDLE,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_current_humidifier_dehumidifier.value == 0
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert acc.char_active.value is False

    hass.states.async_set(
        entity_id,
        OPERATION_MODE_OFF,
        {
            ATTR_OPERATION_MODE: OPERATION_MODE_OFF,
            ATTR_HUMIDITY: 43.0,
            ATTR_CURRENT_HUMIDITY: 38.0,
            ATTR_HUMIDIFIER_ACTION: CURRENT_HUMIDIFIER_IDLE,
        },
    )
    await hass.async_block_till_done()
    assert acc.char_current_humidifier_dehumidifier.value == 0
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert acc.char_active.value is False

    # Set from HomeKit
    call_turn_on = async_mock_service(hass, DOMAIN, "turn_on")

    await hass.async_add_job(acc.char_active.client_update_value, True)
    await hass.async_block_till_done()
    assert call_turn_on
    assert call_turn_on[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert len(events) == 1

    call_turn_off = async_mock_service(hass, DOMAIN, "turn_off")

    await hass.async_add_job(acc.char_active.client_update_value, False)
    await hass.async_block_till_done()
    assert call_turn_off
    assert call_turn_off[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_target_humidifier_dehumidifier.value == 1
    assert len(events) == 2


async def test_hygrostat_get_humidity_range(hass, hk_driver, cls):
    """Test if humidity range is evaluated correctly."""
    entity_id = "humidifier.test"

    hass.states.async_set(entity_id, OPERATION_MODE_OFF)
    await hass.async_block_till_done()
    acc = cls.hygrostat(hass, hk_driver, "HumidifierDehumidifier", entity_id, 2, None)

    hass.states.async_set(
        entity_id, OPERATION_MODE_OFF, {ATTR_MIN_HUMIDITY: 40, ATTR_MAX_HUMIDITY: 45}
    )
    await hass.async_block_till_done()
    assert acc.get_humidity_range() == (40, 45)
