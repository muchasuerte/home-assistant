# -*- coding: utf-8 -*-
"""
Support for Riello's Besmart thermostats.

configuration.yaml

climate:
  - platform: Besmart
    name: Besmart Thermostat
    username: USERNAME
    password: 10080
    room: Soggiorno
    scan_interval: 10

logging options:

logger:
  default: info
  logs:
    custom_components.climate.besmart: debug
"""
import logging
import voluptuous as vol

from homeassistant.components.climate import (ClimateDevice,
    ATTR_ENTITY_ID, ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_AWAY_MODE, SUPPORT_OPERATION_MODE, ATTR_OPERATION_LIST, SUPPORT_FAN_MODE,
    SUPPORT_AUX_HEAT, SUPPORT_TARGET_TEMPERATURE_HIGH, SUPPORT_TARGET_TEMPERATURE_LOW)
from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_ROOM, ATTR_STATE,
                                 TEMP_CELSIUS, ATTR_TEMPERATURE, TEMP_FAHRENHEIT)

from homeassistant.const import STATE_ON, STATE_OFF

import homeassistant.helpers.config_validation as cv

import requests

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Besmart Thermostat'
DEFAULT_TIMEOUT = 3

ATTR_MODE = 'mode'
STATE_UNKNOWN = 'unknown'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_ROOM): cv.string,
})

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE)
#            SUPPORT_TARGET_TEMPERATURE_HIGH | SUPPORT_TARGET_TEMPERATURE_LOW |
#            SUPPORT_AWAY_MODE)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Besmart thermostats."""

    add_devices([Thermostat(config.get(CONF_NAME), config.get(CONF_USERNAME),
                            config.get(CONF_PASSWORD), config.get(CONF_ROOM))])


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class Thermostat(ClimateDevice):
    """Representation of a Besmart thermostat."""
    BASE_URL = 'http://www.besmart-home.com/Android_vokera_20160516/'
    LOGIN = 'login.php'
    ROOM_MODE = 'setRoomMode.php'
    ROOM_LIST = 'getRoomList.php?deviceId={0}'
    ROOM_TEMP = 'setRoomTemp.php'
    ROOM_ECON_TEMP = 'setEconTemp.php'
    ROOM_FROST_TEMP = 'setFrostTemp.php'
    ROOM_CONF_TEMP = 'setComfTemp.php'
    AUTO = 'Auto'
    MANUAL_CONFORT = 'Manuale - Confort'
    HOLIDAY_ECONOMY = 'Holiday - Economy'
    PARTY_CONFORT = 'Party - Confort'
    SPENTO_ANTIGELO = 'Spento - Antigelo'

    def __init__(self, name, username, password, room):
        """Initialize the thermostat."""
        self._name = name
        self._username = username
        self._password = password
        self._room = room
        self._current_temp = 0
        self._current_setpoint = 0
        self._current_state = -1
        self._current_operation = ''
        self._current_unit = 0
        self._tempSetMark = 0
        self._operation_list = [self.AUTO,
                                self.MANUAL_CONFORT,
                                self.HOLIDAY_ECONOMY,
                                self.PARTY_CONFORT,
                                self.SPENTO_ANTIGELO]
        self._heating_state = False
        self._s = requests.Session()
        self._device = None
        self._roomData = None
        _LOGGER.debug("Init called")
        self.update()

    def _login(self):
        if not self._device:
            resp = self._s.post(self.BASE_URL + self.LOGIN,  data={
                'un':self._username,
                'pwd': self._password,
                'version': '32'})
            if resp.ok:
                self._device = resp.json()

    def _fahToCent(self, temp):
        return str(round((temp - 32.0) / 1.8, 1))

    def _centToFah(self, temp):
        return str(round(32.0 + (temp * 1.8), 1))

    def _read(self):
        self._login()

        resp = self._s.post(self.BASE_URL + self.ROOM_LIST.format(self._device.get('deviceId')))
        if resp.ok:
            rooms = resp.json()
            for room in rooms:
                if room.get('id') and room.get('name').lower() == self._room.lower():
                    self._roomData = room
                    return room

        return None

    def _setRoomMode(self, mode):
        if not self._device:
            self._login()

        if not self._roomData:
            self._read()

        if self._device and self._roomData:
            data = {
                'therId': self._roomData.get('therId'),
                'deviceId': self._device.get('deviceId'),
                'mode': mode}

            resp = self._s.post(self.BASE_URL + self.ROOM_MODE, data=data)
            if resp.ok:
                msg = resp.json()
                _LOGGER.debug("resp: {}".format(msg))
                if msg.get('error') == 1:
                    return True

        return None

    def _setRoomTemp(self, new_temp):
        if not self._device:
            self._login()

        if not self._roomData:
            self._read()

        url = self.BASE_URL + self.ROOM_TEMP
        thModel = self._roomData.get('thModel')
        if thModel == '3' or thModel == '5':
            if self._tempSetMark == 0:
                url = self.BASE_URL + self.ROOM_FROST_TEMP
            elif self._tempSetMark == 1:
                url = self.BASE_URL + self.ROOM_ECON_TEMP
            elif self._tempSetMark == 2:
                url = self.BASE_URL + self.ROOM_CONF_TEMP

        if self._current_unit == '0':
            tpCInt, tpCIntFloat = str(new_temp).split('.')
        else:
            tpCInt, tpCIntFloat = self._fahToCent(new_temp).split('.')

        data = {
           'therId': self._roomData.get('therId'),
           'deviceId': self._device.get('deviceId'),
           'tempSet': tpCInt + "",
           'tempSetFloat': tpCIntFloat + "",
        }
        _LOGGER.debug("url: {}".format(url))
        _LOGGER.debug("data: {}".format(data))
        resp = self._s.post(url, data=data)
        if resp.ok:
            msg = resp.json()
            _LOGGER.debug("resp: {}".format(msg))
            if msg.get('error') == 1:
                return True

        return None

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.2

    @property
    def state(self):
        """Return the state of the thermostat."""
        if self._heating_state:
            return STATE_ON

        return STATE_OFF

    @property
    def should_poll(self):
        """Polling needed for thermostat."""
        _LOGGER.debug("Should_Poll called")
        return True

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def update(self):
        """Update the data from the thermostat."""
        _LOGGER.debug("Update called")
        data = self._read()
        if data:
            self._current_setpoint = float(data.get('tempSet'))
            self._current_temp = float(data.get('tempNow'))
            self._heating_state = data.get('heating', '') == '1'
            self._current_state = int(data.get('workMode'))
            self._current_unit = data.get('unit')
            _LOGGER.debug(data)
            if self._current_state == 0:
                pass # Automode
            elif self._current_state == 1:  # Manual - Confort
                self._tempSetMark = 2
            elif self._current_state == 2:  # Holiday - Economy
                self._tempSetMark = 1
            elif self._current_state == 3:  # Party - Confort
                self._tempSetMark = 2
            elif self._current_state == 4:  # Spento - Antigelo
                self._tempSetMark = 0
            elif self._current_state == 5:
                self._tempSetMark = 3

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_MODE: self._current_state,
        }

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        if self._current_unit == '0':
            return TEMP_CELSIUS
        else:
            return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._current_setpoint

    @property
    def current_operation(self):
        """Return the current state of the thermostat."""
        state = self._current_state
        if state in {0, 1, 2, 3, 4}:
            return self._operation_list[state]
        else:
            return STATE_UNKNOWN

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self._operation_list

    def set_operation_mode(self, operation_mode):
        """Set HVAC mode (comfort, home, sleep, Party, Off)."""

        if operation_mode.startswith(self.AUTO):
            mode = 0
        elif operation_mode == self.MANUAL_CONFORT:
            mode = 1
        elif operation_mode == self.HOLIDAY_ECONOMY:
            mode = 2
        elif operation_mode == self.PARTY_CONFORT:
            mode = 3
        elif operation_mode == self.SPENTO_ANTIGELO:
            mode = 4

        self._setRoomMode(mode)
        _LOGGER.debug("Set operation mode=%s(%s)", str(operation_mode), str(mode))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("Set temperature=%s", str(temperature))
        if temperature is None:
            return
        else:
            self._setRoomTemp(temperature)
            _LOGGER.debug("Set temperature=%s", str(temperature))
