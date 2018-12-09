# -*- coding: utf-8 -*-
"""
Support for Riello's Besmart thermostats.
Be aware the thermostat may require more then 3 minute to refresh its states.

The thermostats support the season switch however this control will be managed with a 
different control.

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
from datetime import datetime, timedelta
import voluptuous as vol

from homeassistant.components.climate import (ClimateDevice,
    STATE_COOL, STATE_HEAT, STATE_MANUAL, STATE_AUTO, STATE_ECO, STATE_IDLE, STATE_UNKNOWN,
    ATTR_ENTITY_ID, ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_AWAY_MODE, SUPPORT_OPERATION_MODE, ATTR_OPERATION_LIST, SUPPORT_FAN_MODE,
    SUPPORT_AUX_HEAT)
from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_ROOM, ATTR_STATE,
                                 TEMP_CELSIUS, ATTR_TEMPERATURE, TEMP_FAHRENHEIT)

from homeassistant.const import STATE_ON, STATE_OFF

import homeassistant.helpers.config_validation as cv

import requests

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['switch', 'sensor']
REQUIREMENTS = ['requests']

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
    client = Besmart(config.get(CONF_USERNAME), config.get(CONF_PASSWORD))
    client.rooms() # force init
    add_devices([Thermostat(config.get(CONF_NAME), config.get(CONF_ROOM), client)])


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class Besmart(object):
    """Representation of a Besmart thermostat."""
    BASE_URL = 'http://www.besmart-home.com/Android_vokera_20160516/'
    LOGIN = 'login.php'
    ROOM_MODE = 'setRoomMode.php'
    ROOM_LIST = 'getRoomList.php?deviceId={0}'
    ROOM_DATA = 'getRoomData196.php?therId={0}&deviceId={1}'
    ROOM_PROGRAM = 'getProgram.php?roomId={0}'
    ROOM_TEMP = 'setRoomTemp.php'
    ROOM_ECON_TEMP = 'setEconTemp.php'
    ROOM_FROST_TEMP = 'setFrostTemp.php'
    ROOM_CONF_TEMP = 'setComfTemp.php'
 
    def __init__(self, username, password):
        """Initialize the thermostat."""
        self._username = username
        self._password = password
        self._device = None
        self._rooms = None
        self._timeout = 30
        self._s = requests.Session()
 
    def _fahToCent(self, temp):
        return str(round((temp - 32.0) / 1.8, 1))

    def _centToFah(self, temp):
        return str(round(32.0 + (temp * 1.8), 1))

    def login(self):
        try:
            resp = self._s.post(self.BASE_URL + self.LOGIN,  data={
                'un':self._username,
                'pwd': self._password,
                'version': '32'}, timeout=self._timeout)
            if resp.ok:
                self._device = resp.json()
        except requests.exceptions.HTTPError as ex:
            _LOGGER.error(ex)
            self._device = None

    def rooms(self):
        if not self._device:
            self.login()
        try:
            if self._device:
                resp = self._s.post(
                        self.BASE_URL + self.ROOM_LIST.format(self._device.get('deviceId')),
                        timeout=self._timeout)
                if resp.ok:
                    self._lastupdate = datetime.now()
                    self._rooms = dict((y.get('name').lower(), y) for y in filter(lambda x: x.get('id') != None, resp.json()))
                    return self._rooms
        except requests.exceptions.HTTPError as ex:
            _LOGGER.error(ex)
            self._device = None
        return None

    def roomdata(self, room):
        self.login()
        try:
            if self._device:
                resp = self._s.get(
                        self.BASE_URL + self.ROOM_DATA.format(
                            room.get('therId'),
                            self._device.get('deviceId')),
                        timeout=self._timeout)
                if resp.ok:
                    return resp.json()
        except requests.exceptions.HTTPError as ex:
            _LOGGER.error(ex)
            self._device = None
        return None

    def program(self, room):
        self.login()
        try:
            resp = self._s.get(
                    self.BASE_URL + self.ROOM_PROGRAM.format(room.get('id')),
                    timeout=self._timeout)
            if resp.ok:
                return resp.json()
        except requests.exceptions.HTTPError as ex:
            _LOGGER.error(ex)
            self._device = None
        return None

    def roomByName(self, name):
        if not self._rooms or datetime.now() - self._lastupdate > timedelta(seconds=120):
            self.rooms()

        if self._rooms:
            return self.roomdata(self._rooms.get(name.lower()))
        return None

    def setRoomMode(self, room_name, mode):
        room = self.roomByName(room_name)

        if self._device and room:
            data = {
                'deviceId': self._device.get('deviceId'),
                'therId': room.get('roomMark'),
                'mode': mode}

            resp = self._s.post(self.BASE_URL + self.ROOM_MODE,
                                data=data, timeout=self._timeout)
            if resp.ok:
                msg = resp.json()
                _LOGGER.debug("resp: {}".format(msg))
                if msg.get('error') == 1:
                    return True

        return None

    def setRoomConfortTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_CONF_TEMP)

    def setRoomECOTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_ECON_TEMP)

    def setRoomFrostTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_FROST_TEMP)

    def setRoomTemp(self, room_name, new_temp, url = None):
        url = url or self.ROOM_TEMP
        room = self.roomByName(room_name)
        new_temp = round(new_temp, 1)

        if room.get('unit') == '0':
            tpCInt, tpCIntFloat = str(new_temp).split('.')
        else:
            tpCInt, tpCIntFloat = self._fahToCent(new_temp).split('.')

        data = {
           'deviceId': self._device.get('deviceId'),
           'therId': room.get('therId'),
           'tempSet': tpCInt + "",
           'tempSetFloat': tpCIntFloat + "",
        }
        _LOGGER.debug("url: {}".format(self.BASE_URL + url))
        _LOGGER.debug("data: {}".format(data))
        resp = self._s.post(self.BASE_URL + url, data=data, timeout=self._timeout)
        if resp.ok:
            msg = resp.json()
            _LOGGER.debug("resp: {}".format(msg))
            if msg.get('error') == 1:
                return True

        return None


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class Thermostat(ClimateDevice):
    """Representation of a Besmart thermostat."""
    # BeSmart thModel = 5
    # BeSmart WorkMode
    AUTO = 0 # 'Auto'
    MANUAL = 1  # 'Manuale - Confort'
    ECONOMY = 2 # 'Holiday - Economy'
    PARTY = 3   # 'Party - Confort'
    IDLE = 4  # 'Spento - Antigelo'

    MODE_HA_TO_BESMART = {
        STATE_AUTO + ' - Confort': AUTO,
        STATE_AUTO + ' - Eco': AUTO,
        STATE_AUTO + ' - NoFrost': AUTO,
        STATE_MANUAL: MANUAL,
        STATE_ECO: ECONOMY,
        STATE_IDLE: IDLE
    }

    MODE_BESMART_TO_HA = {
        AUTO: STATE_AUTO,
        MANUAL: STATE_MANUAL,
        ECONOMY: STATE_ECO,
        PARTY: STATE_MANUAL,
        IDLE: STATE_IDLE
    }
    HA_OP_LIST = list(MODE_HA_TO_BESMART)

    # BeSmart Season
    SEASON_WINTER = 0
    SEASON_SUMMER = 1
    SEASON_HA_TO_BESMART = {
        STATE_COOL: SEASON_WINTER,
        STATE_HEAT: SEASON_SUMMER
    }

    def __init__(self, name, room, client):
        """Initialize the thermostat."""
        self._name = name
        self._room_name = room
        self._cl = client
        self._current_temp = 0
        self._current_state = self.IDLE
        self._current_operation = ''
        self._current_unit = 0
        self._tempSetMark = 0
        self._heating_state = False
        self._battery = 0
        self._frostT = 0
        self._saveT = 0
        self._comfT = 0
        self.update()

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

    def get_target_temperature(self):
        if self._current_state == self.AUTO:
            if self._tempSetMark == '2':
                return self._comfT
            elif self._tempSetMark == '1':
                return self._saveT
            else:
                return self._frostT
        elif self._current_state in (self.MANUAL, self.PARTY):
            return self._comfT
        elif self._current_state == self.ECONOMY:
            return self._saveT
        else:
            return self._frostT

    def update(self):
        """Update the data from the thermostat."""
        _LOGGER.debug("Update called")
        data = self._cl.roomByName(self._room_name)
        if data and data.get('error') == 0:
            # from Sunday (0) to Saturday (6)
            today = datetime.today().isoweekday() % 7
            # 48 slot per day
            index = datetime.today().hour * 2 + (1 if datetime.today().minute > 30 else 0)
            programWeek = data['programWeek']
            # delete programWeek to have less noise on debug output
            del data['programWeek']
            _LOGGER.debug(data)
            self._tempSetMark = programWeek[today][index]
            self._battery = data.get('battery', 0)
            self._frostT = float(data.get('frostT'))
            self._saveT = float(data.get('saveT'))
            self._comfT = float(data.get('comfT'))
            self._current_temp = float(data.get('tempNow'))
            self._heating_state = data.get('heating', '') == '1'
            self._current_state = int(data.get('mode'))
            self._current_unit = data.get('tempUnit')

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
        return self.get_target_temperature()

    @property
    def current_operation(self):
        """Return the current state of the thermostat."""
        state = self.MODE_BESMART_TO_HA.get(self._current_state, STATE_UNKNOWN)
        if state == 'auto':
            if self._tempSetMark == '2':
                return state + ' - Confort'
            elif self._tempSetMark == '1':
                return state + ' - Eco'
            else:
                return state + ' - NoFrost'
        return state

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self.HA_OP_LIST

    def set_operation_mode(self, operation_mode):
        """Set HVAC mode (comfort, home, sleep, Party, Off)."""

        mode = self.MODE_HA_TO_BESMART.get(operation_mode, self.AUTO)
        self._cl.setRoomMode(self._room_name, mode)
        _LOGGER.debug("Set operation mode=%s(%s)", str(operation_mode), str(mode))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("Set temperature=%s", str(temperature))
        if temperature is None:
            return
        else:
            if self._current_state == self.AUTO:
                if self._tempSetMark == '2':
                    self._cl.setRoomConfortTemp(self._room_name, temperature)
                elif self._tempSetMark == '1':
                    self._cl.setRoomECOTemp(self._room_name, temperature)
                else:
                    self._cl.setRoomFrostTemp(self._room_name, temperature)
            elif self._current_state in (self.MANUAL, self.PARTY):
                self._cl.setRoomConfortTemp(self._room_name, temperature)
            elif self._current_state == self.ECONOMY:
                self._cl.setRoomECOTemp(self._room_name, temperature)
            else:
                self._cl.setRoomFrostTemp(self._room_name, temperature)
