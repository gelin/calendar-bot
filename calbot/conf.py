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
from datetime import time


__all__ = ['Config']


logger = logging.getLogger('conf')


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

    def load_calendars(self, user_id):
        config = ConfigParser(interpolation=None)
        config_file = CalendarsConfigFile(self.vardir, user_id)
        config_file.read(config)
        for section in config.sections():
            if section != 'settings':
                calendar = CalendarConfig(self,
                                          section,
                                          user_id,
                                          config.get(section, 'url'),
                                          config.get(section, 'channel_id'))
                calendar.verified = config.getboolean(section, 'verified')
                calendar.name = config.get(section, 'name', fallback=('Unknown' if calendar.verified else 'Unverified'))
                yield calendar

    def add_calendar(self, user_id, url, channel_id):
        """
        Adds the calendar to the persisted list
        :param user_id: id of the user for which the calendar is persisted
        :param url: URL of the ical file
        :param channel_id: ID of the channel where to send calendar events
        :return: CalendarConfig instance
        """
        config = ConfigParser(interpolation=None)
        config_file = CalendarsConfigFile(self.vardir, user_id)
        config_file.read(config)

        next_id = str(config.getint('settings', 'last_id', fallback=0) + 1)
        if not config.has_section('settings'):
            config.add_section('settings')
        config.set('settings', 'last_id', next_id)

        calendar = CalendarConfig(self, next_id, user_id, url, channel_id)
        config.add_section(next_id)
        config.set(next_id, 'url', url)
        config.set(next_id, 'channel_id', channel_id)
        config.set(next_id, 'verified', 'false')

        config_file.write(config)

        return calendar

    def delete_calendar(self, user_id, calendar_id):
        """
        Deleted the calendar from the persisted list
        :param user_id: id of the user
        :param calendar_id: id of the calendar
        :return: None
        """
        config = ConfigParser(interpolation=None)
        config_file = CalendarsConfigFile(self.vardir, user_id)
        config_file.read(config)
        if not config.has_section(calendar_id):
            raise KeyError('%s not found' % calendar_id)
        config.remove_section(calendar_id)
        config_file.write(config)


class CalendarConfig:
    """
    Current calendar state.
    """

    def __init__(self, config, id, user_id, url, channel_id):
        self.vardir = config.vardir
        """Base var directory"""
        self.interval = config.interval
        """Update interval for the calendar"""
        self.id = id
        """Current calendar ID"""
        self.user_id = user_id
        """Chat ID of the user to whom this calendar belongs to"""
        self.url = url
        """Url of the ical file to download"""
        self.name = None
        """Human readable name of the calendar"""
        self.channel_id = channel_id
        """Channel where to broadcast calendar events"""
        self.verified = False
        """Flag indicating should the calendar fetching errors be sent to user"""
        self.advance = [24, 48]     # TODO read from files
        """Array of the numbers: how many hours in advance notify about the event"""
        self.day_start = time(10, 0)
        """When the day starts if the event has no specified time"""
        self.events = {}
        """Dictionary of known configured events"""

    def load_events(self):
        config = ConfigParser(interpolation=None)
        EventsConfigFile(self.vardir, self.user_id, self.id).read(config)
        for event_id in config.sections():
            event = EventConfig(self, event_id)
            event.last_notified = config.getint(event_id, 'last_notified', fallback=None)
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

    def save_calendar(self, calendar):
        """
        Saves the calendar as verified and persisted
        :param calendar: Calendar read from ical file
        :return: None
        """
        config_file = CalendarsConfigFile(self.vardir, self.user_id)
        config = ConfigParser(interpolation=None)
        config_file.read(config)

        self.verified = True
        config.set(self.id, 'verified', 'true')
        self.name = calendar.name
        config.set(self.id, 'name', calendar.name)

        config_file.write(config)

    def save_events(self):
        """
        Saves all tracked events into persisted file
        :return: None
        """
        config_file = EventsConfigFile(self.vardir, self.user_id, self.id)
        config = ConfigParser(interpolation=None)
        for event in self.events.values():
            config.add_section(event.id)
            config.set(event.id, 'last_notified', str(event.last_notified))
        config_file.write(config)


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


class CalendarsConfigFile:
    """
    Reads and writes calendars config file.
    """

    def __init__(self, vardir, user_id):
        """
        Creates the config
        :param vardir: basic var dir
        :param user_id: user ID as string
        """
        self.path = os.path.join(vardir, user_id, 'calendars.cfg')

    def read(self, config):
        """
        Reads the configuration from the file
        :param config: ConfigParser to be read from the file
        :return: None
        """
        config.read(self.path)

    def write(self, config):
        """
        Writes the configuration to the file. Creates dirs and files if necessary
        :param config: ConfigParser to be written
        :return: None
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'wt') as file:
            config.write(file)


class EventsConfigFile:
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
        self.path = os.path.join(vardir, user_id, cal_id, 'events.cfg')

    def read(self, config):
        """
        Reads the configuration from the file
        :param config: ConfigParser to be read from the file
        :return: None
        """
        config.read(self.path)

    def write(self, config):
        """
        Writes the configuration to the file. Creates dirs and files if necessary
        :param config: ConfigParser to be written
        :return: None
        """
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'wt') as file:
            config.write(file)
