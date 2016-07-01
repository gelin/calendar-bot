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

    def __init__(self, config):
        self.url = config.url
        self.advance = config.advance
        self.name = None
        self.timezone = pytz.UTC
        self.description = None
        self.events = list(self.read_ical(self.url))

    def read_ical(self, url):
        logger.info('Getting %s', url)
        with urlopen(url) as f:
            vcalendar = icalendar.Calendar.from_ical(f.read())
            self.name = str(vcalendar.get('X-WR-CALNAME'))
            self.timezone = pytz.timezone(str(vcalendar.get('X-WR-TIMEZONE')))
            self.description = str(vcalendar.get('X-WR-CALDESC'))
            for component in vcalendar.walk():
                if component.name == 'VEVENT':
                    yield Event(component, self.timezone)


class Event:

    def __init__(self, vevent, timezone):
        self.id = str(vevent.get('UID'))
        self.title = str(vevent.get('SUMMARY'))
        self.date = vevent.get('DTSTART').dt.astimezone(timezone)
        self.location = str(vevent.get('LOCATION'))
        self.description = str(vevent.get('DESCRIPTION'))

    def to_dict(self):
        return dict(title=self.title, date=self.date, location=self.location, description=self.description)


def filter_future_events(events, max_advance):
    now = datetime.now(tz=pytz.UTC)
    end = now + timedelta(hours=max_advance)
    for event in events:
        if now < event.date <= end:
            yield event


def filter_notified_events(events, config):
    now = datetime.now(tz=pytz.UTC)
    for event in events:
        for advance in sorted(config.advance, reverse=True):
            notified = config.event(event.id)
            if notified is not None:
                if notified.last_notified is None or notified.last_notified <= advance:
                    continue
            if event.date <= now + timedelta(hours=advance):
                yield event
                continue
