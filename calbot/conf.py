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

TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
CALENDAR_URL = 'https://calendar.google.com/calendar/ical/aqclsibjm591jbbk875uio9k40%40group.calendar.google.com/public/basic.ics'
CHANNEL_ID = '@gelintestchannel'
# CALENDAR_URL = 'https://calendar.google.com/calendar/ical/rvsmtm05j6qc2126epnngu9kq0%40group.calendar.google.com/private-5d15121a99e8d543ae656471323b26e7/basic.ics'
# TODO read from config files


__all__ = ['Config']


logger = logging.getLogger('conf')


def events_file(vardir, user_id, cal_id):
    return os.path.join(vardir, user_id, cal_id, 'events.cfg')


class Config:
    """
    Main config, read from the file.
    """

    def __init__(self, vardir):
        self.vardir = vardir
        """path to var directory, where current state is stored"""
        self.token = TOKEN
        """the bot token"""
        self.interval = 3600
        """the interval to reread calendars, in seconds"""

    def add_calendar(self, user_id, url, channel_id):
        """
        Adds the calendar to the persisted list
        :param user_id: id of the user for which the calendar is persisted
        :param url: URL of the ical file
        :param channel_id: ID of the channel where to send calendar events
        :return: CalendarConfig instance
        """
        next_id = '1'     # TODO
        calendar = CalendarConfig(self, next_id, user_id, url, channel_id)
        return calendar

    def calendars(self):
        """
        Returns list of all known and monitoring calendars
        :return: list of CalendarConfig
        """
        return [CalendarConfig(self, '1', 'TEST', CALENDAR_URL, CHANNEL_ID)]   # TODO more calendars


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
        self.load_events()

    def load_events(self):
        config = ConfigParser()
        config.read(events_file(self.vardir, self.user_id, self.id))
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

    def save_events(self):
        """
        Saves all tracked events into persisted file
        :return: None
        """
        filename = events_file(self.vardir, self.user_id, self.id)
        caldir = os.path.dirname(filename)
        os.makedirs(caldir, exist_ok=True)
        with open(filename, 'wt') as file:
            config = ConfigParser()
            for event in self.events.values():
                config.add_section(event.id)
                config.set(event.id, "last_notified", str(event.last_notified))
            config.write(file)

    def save_calendar(self, calendar):
        """
        Saves the calendar as verified and persisted
        :param calendar: Calendar read from ical file
        :return: None
        """
        pass


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
