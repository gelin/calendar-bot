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

import logging
from datetime import time

TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
CALENDAR_URL = 'https://calendar.google.com/calendar/ical/aqclsibjm591jbbk875uio9k40%40group.calendar.google.com/public/basic.ics'
# TODO read from config files


__all__ = ['Config']


logger = logging.getLogger('conf')


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

    def calendars(self):
        """
        Returns list of all known and monitoring calendars
        :return: list of CalendarConfig
        """
        return [CalendarConfig(CALENDAR_URL)]   # TODO more calendars


class CalendarConfig:
    """
    Current calendar state.
    """

    def __init__(self, url):
        self.url = url
        """url of the ical file to download"""
        self.advance = [24, 48]     # TODO read from files
        """array of the numbers: how many hours in advance notify about the event"""
        self.day_start = time(10, 0)    # when the day starts when the event has no specified time

    def event(self, id):
        """
        Returns the calendar event by it's id
        :param id: id of the event
        :return: the EventConfig instance
        """
        return EventConfig()        # TODO read from files


class EventConfig:
    """
    Current calendar event state.
    """

    def __init__(self):
        self.id = 1                 # TODO save and read from files
        """the event id, as it was read from the ical file"""
        self.last_notified = None   # TODO save and read from files
        """the last notification made for this event, as hours in advance, the integer or None"""
