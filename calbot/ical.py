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
import datetime
from urllib.request import urlopen
import pytz
from icalendar import Calendar


logger = logging.getLogger('ical')


class Event:

    def __init__(self, vevent):
        self.uid = str(vevent.get('uid'))
        self.title = str(vevent.get('summary'))
        self.date = vevent.get('dtstart').dt        # TODO timestamp
        self.location = str(vevent.get('location'))
        self.description = str(vevent.get('description'))

    def to_dict(self):
        return dict(title=self.title, date=self.date, location=self.location, description=self.description)


def read_future_events(url, advance=48):
    # TODO put advance to config
    return filter_future_events(read_ical(url), advance)


def read_ical(url):
    logger.info('Retrieving %s', url)
    with urlopen(url) as f:
        ical = Calendar.from_ical(f.read())
        for component in ical.walk():
            if component.name == 'VEVENT':
                yield Event(component)


def filter_future_events(events, advance):
    now = datetime.datetime.now(tz=pytz.UTC)
    end = now + datetime.timedelta(hours=advance)
    for event in events:
        if event.date > now and event.date <= end:
            yield event
