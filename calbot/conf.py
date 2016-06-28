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


import logging


TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
CALENDAR_URL = 'https://calendar.google.com/calendar/ical/rvsmtm05j6qc2126epnngu9kq0%40group.calendar.google.com/private-5d15121a99e8d543ae656471323b26e7/basic.ics'
# TODO read from config files


__all__ = ['Config']


logger = logging.getLogger('conf')


class Config:

    def __init__(self, confdir):
        self.confdir = confdir
        self.token = TOKEN
        self.interval = 3600

    def calendars(self):
        return [CalendarConfig(CALENDAR_URL)]   # TODO more calendars


class CalendarConfig:

    def __init__(self, url):
        self.url = url
        self.advance = 48   # TODO read from files

    def events(self):
        return [EventConfig()]  # TODO read from files


class EventConfig:

    def __init__(self):
        self.notified_in_advance = 1    # TODO save and read from files

