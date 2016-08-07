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
from datetime import datetime, timedelta
from urllib.request import urlopen
import pytz
import icalendar


__all__ = ['Calendar']


logger = logging.getLogger('ical')


class Calendar:
    """
    Calendar, as it was read from ical file.
    """

    def __init__(self, config):
        self.url = config.url
        """url of the ical file, from persisted config"""
        self.advance = config.advance
        """array of the numbers: how many hours in advance notify about the event, from persisted config"""
        self.day_start = config.day_start
        """when the day starts if the event has no specified time, from persisted config"""
        self.name = None
        """name of the calendar, from ical file"""
        self.timezone = pytz.UTC
        """timezone of the calendar, from ical file"""
        self.description = None
        """description of the calendar, from ical file"""
        self.all_events = list(self.read_ical(self.url))
        """list of all calendar events, from ical file"""
        future_events = filter_future_events(self.all_events, max(self.advance))
        self.events = list(filter_notified_events(future_events, config))
        """list of calendar events which should be notified, filtered from ical file"""

    def read_ical(self, url):
        """
        Reads ical file from url.
        :param url: url to read
        :return: it's generator, yields each event read from ical
        """
        # TODO also filter past events to avoid reading of the whole calendar
        logger.info('Getting %s', url)
        with urlopen(url) as f:
            vcalendar = icalendar.Calendar.from_ical(f.read())
            self.name = str(vcalendar.get('X-WR-CALNAME'))
            self.timezone = pytz.timezone(str(vcalendar.get('X-WR-TIMEZONE')))
            self.description = str(vcalendar.get('X-WR-CALDESC'))
            for component in vcalendar.walk():
                if component.name == 'VEVENT':
                    yield Event(component, self.timezone, self.day_start)


class Event:
    """
    Calendar event as it was read from ical file.
    """

    def __init__(self, vevent, timezone, day_start=None):
        self.id = str(vevent.get('UID'))
        """unique id of the event"""
        self.title = str(vevent.get('SUMMARY'))
        """title of the event"""
        self.date = None
        """calendar event datetime"""
        try:
            self.date = vevent.get('DTSTART').dt.astimezone(timezone)
        except:
            self.date = datetime.combine(vevent.get('DTSTART').dt, day_start.replace(tzinfo=timezone))
        self.location = str(vevent.get('LOCATION'))
        """the event location as string"""
        self.description = str(vevent.get('DESCRIPTION'))
        """the event description"""
        self.notified_for_advance = None
        """hours in advance for which this event should be notified"""

    def to_dict(self):
        """
        Converts the event to dict to be easy passed to format function.
        :return: dict of the event properties
        """
        return dict(title=self.title, date=self.date, location=self.location, description=self.description)


def filter_future_events(events, max_advance):
    """
    Filters only events which are after now and before the max_advance value
    :param events: iterable of events
    :param max_advance: future point, from now in hours, until lookup the events
    :return: it's generator, yields each filtered event
    """
    now = datetime.now(tz=pytz.UTC)
    end = now + timedelta(hours=max_advance)
    for event in events:
        if now < event.date <= end:
            yield event


def filter_notified_events(events, config):
    """
    Filters events which were already notified.
    Uses the array expected notification advances from the config.
    For each filtered event sets the advance it should be notified for (notified_for_advance).
    :param events: iterable of events
    :param config: CalendarConfig
    :return: it's generator, yields each filtered event
    """
    now = datetime.now(tz=pytz.UTC)
    for event in events:
        for advance in sorted(config.advance, reverse=True):
            notified = config.event(event.id)
            last_notified = notified is not None and notified.last_notified
            if last_notified is not None and last_notified <= advance:
                continue
            if event.date <= now + timedelta(hours=advance):
                event.notified_for_advance = advance
                yield event
                break

