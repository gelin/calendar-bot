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
from datetime import datetime, date, timedelta
from urllib.request import urlopen
import pytz
import icalendar
from dateutil import rrule

from calbot.formatting import BlankFormat

__all__ = ['Calendar', 'sample_event']


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
        unnotified_events = filter_notified_events(future_events, config)
        sorted_events = sort_events(unnotified_events)
        self.events = list(sorted_events)
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
        """event (start) date"""
        self.time = None
        """event (start) time, can be None"""
        self.notify_datetime = None
        """calendar event datetime, relative to which to calculate notification moment,
        uses day_start if time for current event is None"""

        # DTSTART is always in UTC, not possible to get event-specific timezone
        # TODO: now iCal has TZID attribute for DTSTART and DTEND, need to take care on it
        dtstart = vevent.get('DTSTART').dt
        if isinstance(dtstart, datetime):
            dtstarttz = vevent.get('DTSTART').dt.astimezone(timezone)
            self.date = dtstarttz.date()
            self.time = dtstarttz.timetz()
        elif isinstance(dtstart, date):
            self.date = dtstart

        self.repeat_rule = None
        """event repeat rule, can be None"""
        if vevent.get('RRULE') is not None:
            self.repeat_rule = vevent.get('RRULE').to_ical().decode('utf-8')
            self.find_next_repeat_datetime(timezone)

        self.set_notify_datetime(timezone, day_start)

        self.location = str(vevent.get('LOCATION'))
        """the event location as string"""
        self.description = str(vevent.get('DESCRIPTION'))
        """the event description"""
        self.notified_for_advance = None
        """hours in advance for which this event should be notified"""

    def set_notify_datetime(self, timezone, day_start):
        if self.time is not None:
            self.notify_datetime = datetime.combine(self.date, self.time)
        else:
            self.notify_datetime = datetime.combine(self.date, day_start.replace(tzinfo=timezone))

    # TODO: replace with making clones of the event for the datetime inverval
    def find_next_repeat_datetime(self, timezone):
        if self.time is not None:
            rule = rrule.rrulestr(self.repeat_rule, dtstart=datetime.combine(self.date, self.time))
            next_datetime = rule.after(datetime.now(timezone))
            self.date = next_datetime.date()
            self.time = next_datetime.timetz()
        else:
            rule = rrule.rrulestr(self.repeat_rule, dtstart=self.date)
            next_date = rule.after(date.today())
            self.date = next_date

    def to_dict(self):
        """
        Converts the event to dict to be easy passed to format function.
        :return: dict of the event properties
        """
        return dict(title=self.title or BlankFormat(),
                    date=self.date or BlankFormat(),
                    time=self.time or BlankFormat(),
                    location=self.location or BlankFormat(),
                    description=self.description or BlankFormat())


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
        if now < event.notify_datetime <= end:
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
            if event.notify_datetime <= now + timedelta(hours=advance):
                event.notified_for_advance = advance
                yield event
                break


def sort_events(events):
    def sort_key(event):
        return event.notify_datetime
    return sorted(events, key=sort_key)


def _get_sample_event():
    component = icalendar.cal.Component()
    component.add('summary', 'This is sample event')
    component.add('location', 'It happens in the Milky Way')
    component.add('description', 'The sample event is to demonstrate how the event can be formatted')
    component.add('dtstart', datetime.now(tz=pytz.UTC))
    return Event(component, pytz.UTC)

sample_event = _get_sample_event()
