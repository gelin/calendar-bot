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


import datetime
import os

import pytz

from icalendar.cal import Component

from calbot.bot import format_event
from calbot.conf import CalendarConfig, Config
from calbot.ical import Event, Calendar, filter_future_events, filter_notified_events


def _get_component():
    component = Component()
    component.add('summary', 'summary')
    component.add('location', 'location')
    component.add('description', 'description')
    return component


def test_format_event():
    component = _get_component()
    component.add('dtstart', datetime.datetime(2016, 6, 23, 19, 50, 35, tzinfo=pytz.UTC))
    event = Event(component, pytz.UTC)
    result = format_event(event)
    assert 'summary\nThursday, 23 June 2016, 19:50 UTC\nlocation\ndescription\n' == result, result


def test_read_calendar():
    config = CalendarConfig(Config('test'), 'file://{}/test.ics'.format(os.path.dirname(__file__)))
    calendar = Calendar(config)
    assert pytz.timezone('Asia/Omsk') == calendar.timezone, calendar.timezone
    assert 'TEST' == calendar.name, calendar.name
    assert 'Just a test calendar' == calendar.description, calendar.description
    assert datetime.datetime(2016, 6, 24, 0, 0, 0, tzinfo=pytz.UTC) == calendar.all_events[0].date, calendar.all_events[0].date
    assert 'Событие по-русски' == calendar.all_events[0].title, calendar.all_events[0].title
    assert datetime.datetime(2016, 6, 23, 0, 0, 0, tzinfo=pytz.UTC) == calendar.all_events[1].date, calendar.all_events[1].date
    assert 'Event title' == calendar.all_events[1].title, calendar.all_events[1].title


def test_filter_future_events():
    timezone = pytz.UTC
    component_past = _get_component()
    component_past.add('dtstart', datetime.datetime.now(tz=timezone) - datetime.timedelta(hours=1))
    component_now = _get_component()
    component_now.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(minutes=10))
    component_future = _get_component()
    component_future.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(hours=2))
    events = [Event(component_past, timezone), Event(component_now, timezone), Event(component_future, timezone)]
    result = list(filter_future_events(events, 1))
    assert 1 == len(result), len(result)
    assert component_now.decoded('dtstart') == result[0].date, result


def test_filter_notified_events():
    timezone = pytz.UTC
    component_now = _get_component()
    component_now.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(minutes=5))
    component_future24 = _get_component()
    component_future24.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(hours=24, minutes=-5))
    component_future48 = _get_component()
    component_future48.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(hours=48, minutes=-5))

    class TestCalendarConfig:

        def __init__(self):
            self.advance = [24, 48]

        def event(self, id):
            return TestEventConfig()

    class TestEventConfig:

        def __init__(self):
            self.id = 1
            self.last_notified = 48

    events = [Event(component_now, timezone), Event(component_future24, timezone), Event(component_future48, timezone)]
    config = TestCalendarConfig()
    result = list(filter_notified_events(events, config))
    assert 2 == len(result), result
    assert component_now.decoded('dtstart') == result[0].date, result
    assert component_future24.decoded('dtstart') == result[1].date, result


def test_date_only_event():
    timezone = pytz.UTC
    component = _get_component()
    component.add('dtstart', datetime.date.today())
    event = Event(component, timezone, datetime.time(10, 0))
    assert isinstance(event.date, datetime.datetime), event.date.__class__.__name__
    assert 10 == event.date.hour, event.date
    assert 0 == event.date.minute, event.date
    assert pytz.UTC == event.date.tzinfo, event.date
