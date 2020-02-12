"""
Support for the Beefweb player API for DeaDBeeF and foobar2000.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.beefweb/
"""
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, PLATFORM_SCHEMA, SUPPORT_PAUSE, SUPPORT_PLAY,
    SUPPORT_STOP, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_NAME, CONF_HOST, CONF_PORT, STATE_IDLE, STATE_PAUSED, STATE_PLAYING, STATE_OFF)

REQUIREMENTS = ['bravado==10.2.0']

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 8880
DEFAULT_NAME = 'Beefweb'

SUPPORT_BEEFWEB = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
                  SUPPORT_PLAY | SUPPORT_STOP
OPENAPI_SPEC = 'player-api.yml' # Put this in config/: https://github.com/hyperblast/beefweb/blob/master/docs/player-api.yml

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT): cv.port
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the beefweb platform."""
    name = config.get(CONF_NAME, DEFAULT_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT, DEFAULT_PORT)
    spec_path = hass.config.path(OPENAPI_SPEC)

    add_entities([BeefwebDevice(name, host, port, spec_path)])


class BeefwebDevice(MediaPlayerDevice):
    """Representation of a beefweb player."""

    def __init__(self, name, host, port, spec_path):
        """Initialize the beefweb device."""
        from bravado.client import SwaggerClient
        from bravado.swagger_model import load_file

        client = SwaggerClient.from_spec(load_file(spec_path))
        self._client = client
        self._name = name
        self._volume = None
        self._muted = None
        self._state = None
        self._media_position_updated_at = None
        self._media_position = None
        self._media_duration = None

        self._media_content_id = None

    def update(self):
        """Get the latest details from the device."""
        import math
        self._volume = self._volume if self._volume is not None else 10 ** -8

        # Cached values in case of IO failure
        default = {
            'player': self._client.get_model('PlayerState')(activeItem={
                'duration': self._media_duration,
                'position': self._media_position
            },
                playbackState='off',
                volume={
                    'isMuted': self._muted,
                    'value': 20 * math.log10(self._volume)
                })
        }

        state = self._client.player.getPlayerState().response(timeout=9, fallback_result=default).result['player']

        status = state.playbackState
        if status == 'playing':
            self._state = STATE_PLAYING
        elif status == 'paused':
            self._state = STATE_PAUSED
        elif status == 'stopped':
            self._state = STATE_IDLE
        else:
            self._state = STATE_OFF

        self._media_duration = state.activeItem['duration']
        position = state.activeItem['position']
        if position != self._media_position:
            self._media_position_updated_at = dt_util.utcnow()
            self._media_position = position

        self._volume = 10 ** (state.volume['value'] / 20)
        self._muted = state.volume['isMuted']

        self._media_content_id = str(state.activeItem['playlistIndex']) + ':' + str(state.activeItem['index'])

        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    # access_token

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def media_content_id(self):
        return self._media_content_id

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        return self._media_duration

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        return self._media_position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        return self._media_position_updated_at

    # media_image_url

    # media_image_hash

    # media_title

    # media_artist

    # media_album_name

    # media_album_artist

    # media_track

    # media_series_title

    # media_season

    # media_episode

    # media_channel

    # media_playlist

    # app_id

    # app_name

    # source

    # source_list

    # sound_mode

    # sound_mode_list

    # shuffle

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_BEEFWEB

    def turn_on(self):
        self.media_play()

    def turn_off(self):
        self.media_pause()

    def mute_volume(self, mute):
        """Mute the volume."""
        self._client.player.setPlayerState(isMuted=mute).response()
        self._muted = mute

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        import math

        self._client.player.setPlayerState(volume=20 * math.log10(volume)).response()
        self._volume = volume

    def media_play(self):
        """Send play command."""
        self._client.player.playCurrent().response()
        self._state = STATE_PLAYING

    def media_pause(self):
        """Send pause command."""
        self._client.player.pause().response()
        self._state = STATE_PAUSED

    def media_stop(self):
        """Send stop command."""
        self._client.player.stop().response()
        self._state = STATE_IDLE

    # media_previous_track

    # media_next_track

    def media_seek(self, position):
        """Seek the media to a specific location."""
        self._client.player.setPlayerState(position=position).response()

    # play_media

    # select_source

    # select_sound_mode

    # clear_playlist

    # set_shuffle
