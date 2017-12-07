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
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD, CONF_ROOM,
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


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Toon thermostats."""

    add_devices([Thermostat(config.get(CONF_NAME), config.get(CONF_USERNAME),
                            config.get(CONF_PASSWORD), config.get(CONF_ROOM))])


# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class Thermostat(ClimateDevice):
    """Representation of a Toon thermostat."""
    BASE_URL = 'http://www.besmart-home.com/Android_vokera_20160516/'
    LOGIN = 'login.php'
    ROOMLIST = 'getRoomList.php?deviceId={0}'

    def __init__(self, name, username, password, room):
        """Initialize the thermostat."""
        self._data = None
        self._name = name
        self._username = username
        self._password = password
        self._room = room
        self._current_temp = 0
        self._current_setpoint = 0
        self._current_state = -1
        self._current_operation = ''
        self._set_state = 0
        self._heating_state = False
        self._operation_list = ['Auto', 'Confort', 'Holiday', 'Party', 'Off']
        self._s = requests.Session()
        self._device = None
        _LOGGER.debug("Init called")
        self.update()

    def read(self):
        if not self._device:
                resp = self._s.post(self.BASE_URL + self.LOGIN,  data={
                    'un':self._username,
                    'pwd': self._password,
                    'version': '32'})
                if resp.ok:
                    self._device = resp.json()

        resp = self._s.post(self.BASE_URL + self.ROOMLIST.format(self._device.get('deviceId')))
        if resp.ok:
            rooms = resp.json()
            for room in rooms:
                if room.get('id') and room.get('name').lower() == self._room.lower():
                    return room

        return None

    @property
    def state(self):
        """Return the state of the thermostat."""
        if self._heating_state:
            return STATE_ON

        return STATE_OFF

    # @property
    # def should_poll(self):
    #     """Polling needed for thermostat."""
    #     _LOGGER.debug("Should_Poll called")
    #     return True

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (
            SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE | SUPPORT_AUX_HEAT)
#            SUPPORT_TARGET_TEMPERATURE_HIGH | SUPPORT_TARGET_TEMPERATURE_LOW |
#            SUPPORT_AWAY_MODE)

    def update(self):
        """Update the data from the thermostat."""
        data = self.read()
        self._current_setpoint = float(data.get('tempSet'))
        self._current_temp = float(data.get('tempNow'))
        self._heating_state = data.get('heating', '') == '1'
        self._current_state = int(data.get('workMode'))
        self._current_unit = data.get('unit')
        _LOGGER.debug("Update called")
        _LOGGER.debug(data)

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
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        _LOGGER.debug("XXXXXXXX")
        _LOGGER.debug(self._heating_state)
        return self._heating_state

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._current_setpoint

    @property
    def current_operation(self):
        """Return the current state of the thermostat."""
        state = self._current_state
        if state in (0, 1, 2, 3, 4):
            return self._operation_list[state]
        else:
            return STATE_UNKNOWN

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self._operation_list

    def set_operation_mode(self, operation_mode):
        """Set HVAC mode (comfort, home, sleep, away, holiday)."""
        if operation_mode == "Auto":
            mode = 0
        elif operation_mode == "Confort":
            mode = 1
        elif operation_mode == "Holiday":
            mode = 2
        elif operation_mode == "Party":
            mode = 3
        elif operation_mode == "Off":
            mode = 4

        # self._data = self.do_api_request(BASE_URL.format(
        #     self._host,
        #     self._port,
        #     '/happ_thermstat?action=changeSchemeState'
        #     '&state=2&temperatureState='+str(mode)))
        #
        _LOGGER.debug("Set operation mode=%s(%s)", str(operation_mode),
                      str(mode))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)*100
        if temperature is None:
            return
        else:
            pass
            # self._data = self.do_api_request(BASE_URL.format(
            #     self._host,
            #     self._port,
            #     '/happ_thermstat?action=setSetpoint'
            #     '&Setpoint='+str(temperature)))
            _LOGGER.debug("Set temperature=%s", str(temperature))
 

