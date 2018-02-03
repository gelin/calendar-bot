# -*- coding: utf-8 -*-

# Copyright 2016 Denis Nelubin.
#
# This file is part of Calendar Bot.
#
# Calendar Bot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Calendar Bot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Calendar Bot.  If not, see http://www.gnu.org/licenses/.

"""
We have this hierarchy of data to be persisted.

@startuml

class User <<Runtime>> {
    chat_id
}

class UserConfig <<Persist>> {
    chat_id
    notification_format
    notification_language
    notification_advance_hours
}

User *- UserConfig

class Calendar <<Runtime>> {
    id
    url
    name
    timezone
    description
}

class CalendarConfig <<Persist>> {
    id
    url
    name
    notify_channel_id
    verified
    last_process_at
    last_process_error
}

Calendar *- CalendarConfig

class Event <<Runtime>> {
    id
    title
    date
    location
    description
}

class EventConfig <<Persist>> {
    id
    last_notified_advance
}

Event *- EventConfig

User *-- "*" Calendar
Calendar *-- "*" Event

@enduml

So, under `var` directory we have the following files and folders.

```
var/
    user1_chat_id/
        settings.cfg - general user config like notification format
        calendars.cfg - the list of user's calendars
        calendar1_id/
            events.cfg - the list of calendar events
        calendar2_id/
        ...
    user2_chat_id/
    ...
```
"""

from configparser import ConfigParser
import logging
import os
from datetime import time, datetime

__all__ = ['Config']

logger = logging.getLogger('conf')

DEFAULT_FORMAT = '''{title}
{date:%A, %d %B %Y}{time:, %H:%M %Z}
{location}
{description}'''

DEFAULT_ADVANCE = [48, 24]


class Config:
    """
    Main config, read from the file.
    """

    def __init__(self, configfile):
        """
        Creates the config
        :param configfile: location of main config file
        """
        config = ConfigParser()
        config.read(configfile)
        self.vardir = config.get('bot', 'vardir')
        """path to var directory, where current state is stored"""
        self.token = config.get('bot', 'token')
        """the bot token"""
        self.interval = config.getint('bot', 'interval', fallback=3600)
        """the interval to reread calendars, in seconds"""
        self.stats_interval = config.getint('bot', 'stats_interval', fallback=3600)
        """the interval to update statistics, in seconds"""
        self.bootstrap_retries = config.getint('bot', 'bootstrap_retries', fallback=0)
        """Whether the bootstrapping phase of the Updater will retry on failures on the Telegram server."""
        self.poll_interval = config.getfloat('polling', 'poll_interval', fallback=0.0)
        """Time to wait between polling updates from Telegram"""
        self.timeout = config.getfloat('polling', 'timeout', fallback=10.0)
        """Timeout in seconds for long polling"""
        self.read_latency = config.getfloat('polling', 'read_latency', fallback=2.0)
        """Additional timeout in seconds to allow the response from Telegram servers."""
        self.webhook = config.getboolean('webhook', 'webhook', fallback=False)
        """use webhook or not"""
        self.domain = config.get('webhook', 'domain', fallback=None)
        """public domain where the webhook of the bot is listening"""
        self.listen = config.get('webhook', 'listen', fallback='[::1]')
        """IP address to listen by webhook"""
        self.port = config.getint('webhook', 'port', fallback=5000)

    def user_calendars(self, user_id):
        """
        Returns list of calendars configured for the user
        :param user_id: id of the user to list calendars
        :return: list of CalendarConfig
        """
        for calendar in self.load_calendars(user_id):
            yield calendar

    def all_calendars(self):
        """
        Returns list of all known and monitoring calendars with events
        :return: list of CalendarConfig
        """
        for name in os.listdir(self.vardir):
            if os.path.isdir(os.path.join(self.vardir, name)):
                user_id = name
                for calendar in self.load_calendars(user_id):
                    calendar.load_events()
                    yield calendar

    def load_user(self, user_id):
        """
        Loads UserConfig
        :param user_id: ID of the user
        :return: UserConfig instance
        """
        parser = UserConfigFile(self.vardir, user_id).read_parser()
        return UserConfig.load(self, user_id, parser)

    def load_calendars(self, user_id):
        """
        Loads all calendars of the specified user.
        :param user_id: ID of the user
        :return: yields the CalendarConfig instances
        """
        user_config = self.load_user(user_id)
        calendar_parser = CalendarsConfigFile(self.vardir, user_id).read_parser()

        for section in calendar_parser.sections():
            if section != 'settings':
                calendar = CalendarConfig.load(user_config, calendar_parser, section)
                yield calendar

    def load_calendar(self, user_id, calendar_id):
        """
        Loads one calendar of the specified user.
        :param user_id: ID of the user
        :param calendar_id: ID of the calendar
        :return: the CalendarConfig instance
        """
        user_config = self.load_user(user_id)
        calendar_parser = CalendarsConfigFile(self.vardir, user_id).read_parser()

        if not calendar_parser.has_section(calendar_id):
            raise KeyError('Calendar %s not found' % calendar_id)

        calendar = CalendarConfig.load(user_config, calendar_parser, calendar_id)
        return calendar

    def add_calendar(self, user_id, url, channel_id):
        """
        Adds the calendar to the persisted list
        :param user_id: id of the user for which the calendar is persisted
        :param url: URL of the ical file
        :param channel_id: ID of the channel where to send calendar events
        :return: CalendarConfig instance
        """
        calendar_config_file = CalendarsConfigFile(self.vardir, user_id)
        calendar_parser = calendar_config_file.read_parser()
        user_parser = UserConfigFile(self.vardir, user_id).read_parser()
        user = UserConfig.load(self, user_id, user_parser)

        next_id = str(calendar_parser.getint('settings', 'last_id', fallback=0) + 1)
        if not calendar_parser.has_section('settings'):
            calendar_parser.add_section('settings')
        calendar_parser.set('settings', 'last_id', next_id)

        calendar = CalendarConfig.new(user, next_id, url, channel_id)
        calendar_parser.add_section(next_id)
        calendar_parser.set(next_id, 'url', url)
        calendar_parser.set(next_id, 'channel_id', channel_id)
        calendar_parser.set(next_id, 'verified', 'false')

        calendar_config_file.write(calendar_parser)

        return calendar

    def delete_calendar(self, user_id, calendar_id):
        """
        Deleted the calendar from the persisted list
        :param user_id: id of the user
        :param calendar_id: id of the calendar
        :return: None
        """
        config_file = CalendarsConfigFile(self.vardir, user_id)
        config_parser = config_file.read_parser()

        if not config_parser.has_section(calendar_id):
            raise KeyError('%s not found' % calendar_id)
        config_parser.remove_section(calendar_id)

        config_file.write(config_parser)


class UserConfig:
    """
    Per-user configuration parameters.
    """

    def __init__(self, **kwargs):
        self.vardir = kwargs['vardir']
        """Base var directory"""
        self.interval = kwargs['interval']
        """Update interval for the calendar"""
        self.id = kwargs['user_id']
        """ID of the user"""
        self.format = kwargs['format']
        """Event message format for the user"""
        self.language = kwargs['language']
        """Language to format the event"""
        self.advance = kwargs['advance']
        """Array of hours for advance the calendar event"""
        self.config_parser = kwargs.get('config_parser', None)
        """ConfigParser from which this object was loaded, None if this is new a config"""

    @classmethod
    def new(cls, config, user_id):
        """
        Creates the new config, when there is nothing to read from settings.cfg file
        :param config: main config instance
        :param user_id: ID of the user
        :return: UserConfig instance
        """
        return cls(
            vardir=config.vardir,
            interval=config.interval,
            user_id=user_id,
            format=DEFAULT_FORMAT,
            language=None,
            advance=DEFAULT_ADVANCE,
        )

    @classmethod
    def load(cls, config, user_id, config_parser):
        """
        Loads the config from the ConfigParser
        :param config: main config instance
        :param user_id: ID of the user
        :param config_parser: ConfigParser which read the user settings.cfg file
        :return: UserConfig instance
        """
        return cls(
            vardir=config.vardir,
            interval=config.interval,
            user_id=user_id,
            format=config_parser.get('settings', 'format', fallback=DEFAULT_FORMAT),
            language=config_parser.get('settings', 'language', fallback=None),
            advance=list(
                map(int,
                    config_parser.get('settings', 'advance', fallback=' '.join(map(str, DEFAULT_ADVANCE))).split())
            ),
            config_parser=config_parser
        )

    def set_format(self, format):
        """
        Sets the event format for the user, writes it to settings.cfg of the user.
        :param format: new format
        :return: None
        """
        config_file = UserConfigFile(self.vardir, self.id)
        parser = self.config_parser or config_file.read_parser()
        if not parser.has_section('settings'):
            parser.add_section('settings')
        parser.set('settings', 'format', format)
        config_file.write(parser)
        self.format = format

    def set_language(self, language):
        """
        Sets the event format for the user, writes it to settings.cfg of the user.
        :param language: new language
        :return: None
        """
        config_file = UserConfigFile(self.vardir, self.id)
        parser = self.config_parser or config_file.read_parser()
        if not parser.has_section('settings'):
            parser.add_section('settings')
        parser.set('settings', 'language', language)
        config_file.write(parser)
        self.language = language

    def set_advance(self, hours):
        """
        Sets the list of hours to notify events in advance.
        :param hours: advance hours
        :return: None
        """
        config_file = UserConfigFile(self.vardir, self.id)
        parser = self.config_parser or config_file.read_parser()
        if not parser.has_section('settings'):
            parser.add_section('settings')
        int_hours = sorted(set(map(int, hours)), reverse=True)
        parser.set('settings', 'advance', ' '.join(map(str, int_hours)))
        config_file.write(parser)
        self.advance = int_hours


class CalendarConfig:
    """
    Current persisted calendar state.
    """

    def __init__(self, **kwargs):
        self.vardir = kwargs['vardir']
        """Base var directory"""
        self.interval = kwargs['interval']
        """Update interval for the calendar"""
        self.id = kwargs['cal_id']
        """Current calendar ID"""
        self.user_id = kwargs['user_id']
        """Chat ID of the user to whom this calendar belongs to"""
        self.url = kwargs['url']
        """Url of the ical file to download"""
        self.name = kwargs['name']
        """Human readable name of the calendar"""
        self.channel_id = kwargs['channel_id']
        """Channel where to broadcast calendar events"""
        self.verified = kwargs['verified']
        """Flag indicating should the calendar fetching errors be sent to user"""
        self.format = kwargs['format']
        """Format string for the event"""
        self.language = kwargs['language']
        """Language for the event"""
        self.advance = kwargs['advance']
        """Array of the numbers: how many hours in advance notify about the event"""
        self.day_start = time(10, 0)
        """When the day starts if the event has no specified time"""
        self.events = {}
        """Dictionary of known configured events"""
        self.last_process_at = kwargs.get('last_process_at')
        """Moment when the calendar was processed last time"""
        self.last_process_error = kwargs.get('last_process_error')
        """Error message if last processing failed with an error"""

    @classmethod
    def new(cls, user_config, cal_id, url, channel_id):
        """
        Creates the new calendar config, for just added calendar by an /add command
        :param user_config: UserConfig instance
        :param cal_id: ID for this calendar
        :param url: URL of the calendar
        :param channel_id: ID of the channel where to post calendar events
        :return: CalendarConfig instance
        """
        return cls(
            vardir=user_config.vardir,
            interval=user_config.interval,
            user_id=user_config.id,
            format=user_config.format,
            language=user_config.language,
            advance=user_config.advance,
            cal_id=cal_id,
            url=url,
            name=None,
            channel_id=channel_id,
            verified=False,
            )

    @classmethod
    def load(cls, user_config, config_parser, cal_id):
        """
        Creates the calendar config from the calendar.cfg file already read to ConfigParser
        :param user_config: UserConfig instance
        :param config_parser: ConfigParser which read calendars.cfg file
        :param cal_id: ID of the calendar, used as name of the section in ConfigParser
        :return: CalendarConfig instance
        """
        section = cal_id
        verified = config_parser.getboolean(section, 'verified', fallback=False)
        return cls(
            vardir=user_config.vardir,
            interval=user_config.interval,
            user_id=user_config.id,
            format=user_config.format,
            language=user_config.language,
            advance=user_config.advance,
            cal_id=cal_id,
            url=config_parser.get(section, 'url'),
            name=config_parser.get(section, 'name', fallback=('Unknown' if verified else 'Unverified')),
            channel_id=config_parser.get(section, 'channel_id'),
            verified=verified,
            last_process_at=config_parser.get(section, 'last_process_at', fallback=None),
            last_process_error=config_parser.get(section, 'last_process_error', fallback=None),
            )

    def load_events(self):
        """
        Loads the calendar events from the events.cfg file.
        :return: None
        """
        config_parser = EventsConfigFile(self.vardir, self.user_id, self.id).read_parser()

        for event_id in config_parser.sections():
            event = EventConfig(self, event_id)
            event.last_notified = config_parser.getint(event_id, 'last_notified', fallback=None)
            self.events[event_id] = event

    def event(self, id):
        """
        Returns the persisted state of calendar event by it's id
        :param id: id of the event
        :return: the EventConfig instance, read from persisted storage or a new one
        """
        try:
            return self.events[id]
        except KeyError:
            event = EventConfig(self, id)
            self.events[id] = event
            return event

    def event_notified(self, event):
        """
        Marks the event in config as notified.
        Copies data from the ical event object
        :param event: runtime event processed by ical module
        :return: None
        """
        config_event = self.event(event.id)
        config_event.last_notified = event.notified_for_advance

    def _create_section(self, config_parser):
        if not config_parser.has_section(self.id):
            config_parser.add_section(self.id)
            config_parser.set(self.id, 'url', self.url)
            config_parser.set(self.id, 'channel_id', self.channel_id)

    def _update_last_process(self, config_parser, error=None):
        self.last_process_at = datetime.utcnow().isoformat()
        config_parser.set(self.id, 'last_process_at', self.last_process_at)
        self.last_process_error = error
        config_parser.set(self.id, 'last_process_error', str(self.last_process_error))

    def save_calendar(self, calendar):
        """
        Saves the calendar as verified and persisted
        :param calendar: Calendar read from ical file
        :return: None
        """
        config_file = CalendarsConfigFile(self.vardir, self.user_id)
        config_parser = config_file.read_parser()

        self._create_section(config_parser)

        self.verified = True
        config_parser.set(self.id, 'verified', 'true')
        self.name = calendar.name
        config_parser.set(self.id, 'name', calendar.name)

        self._update_last_process(config_parser)

        config_file.write(config_parser)

    def save_events(self):
        """
        Saves all tracked events into persisted file
        :return: None
        """
        config_file = EventsConfigFile(self.vardir, self.user_id, self.id)
        config_parser = ConfigParser(interpolation=None)

        for event in self.events.values():
            config_parser.add_section(event.id)
            if type(event.last_notified) is int:
                config_parser.set(event.id, 'last_notified', str(event.last_notified))

        config_file.write(config_parser)

        self.save_error(None)

    def save_error(self, exception):
        config_file = CalendarsConfigFile(self.vardir, self.user_id)
        config_parser = config_file.read_parser()
        self._create_section(config_parser)
        self._update_last_process(config_parser, exception)
        config_file.write(config_parser)


class EventConfig:
    """
    Current calendar event state.
    """

    def __init__(self, calendar, id):
        self.id = id
        """the event id, as it was read from the ical file"""
        self.cal_id = calendar.id
        """ID of the calendar to which this event belongs to"""
        self.user_id = calendar.user_id
        """Chat ID of the user to whom the calendar belongs to"""
        self.last_notified = None
        """the last notification made for this event, as hours in advance, the integer or None"""


class ConfigFile:
    """
    Reads and writes a config file.
    """

    def __init__(self, file_path):
        """
        Creates the config
        :param file_path: path to the config file
        """
        self.path = file_path

    def read(self, parser):
        """
        Reads the configuration from the file
        :param parser: ConfigParser to be read from the file
        :return: None
        """
        parser.read(self.path, encoding='UTF-8')

    def read_parser(self):
        """
        Creates the new ConfigParser and read values from file to it
        :return: ConfigParser instance
        """
        parser = ConfigParser(interpolation=None)
        self.read(parser)
        return parser

    def write(self, parser):
        """
        Writes the configuration to the file. Creates dirs and files if necessary
        :param parser: ConfigParser to be written
        :return: None
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'wt', encoding='UTF-8') as file:
            parser.write(file)


class UserConfigFile(ConfigFile):
    """
    Reads and writes user settings config file.
    """

    def __init__(self, vardir, user_id):
        """
        Creates the config
        :param vardir: basic var dir
        :param user_id: user ID as string
        """
        super().__init__(os.path.join(vardir, user_id, 'settings.cfg'))


class CalendarsConfigFile(ConfigFile):
    """
    Reads and writes calendars config file.
    """

    def __init__(self, vardir, user_id):
        """
        Creates the config
        :param vardir: basic var dir
        :param user_id: user ID as string
        """
        super().__init__(os.path.join(vardir, user_id, 'calendars.cfg'))


class EventsConfigFile(ConfigFile):
    """
    Reads and writes events config file.
    """

    def __init__(self, vardir, user_id, cal_id):
        """
        Creates the config
        :param vardir: basic var dir
        :param user_id: user ID as string
        :param cal_id: ID of the calendar
        """
        super().__init__(os.path.join(vardir, user_id, cal_id, 'events.cfg'))
