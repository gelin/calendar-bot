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
import pytz

from icalendar.cal import Component

from calbot.bot import format_event
from calbot.ical import Event, filter_future_events


def _get_component():
    component = Component()
    component.add('summary', 'summary')
    component.add('location', 'location')
    component.add('description', 'description')
    return component


def test_format_event():
    component = _get_component()
    component.add('dtstart', datetime.datetime(2016, 6, 23, 19, 50, 35, tzinfo=pytz.UTC))
    event = Event(component)
    result = format_event(event)
    assert 'summary\nThursday, 23 June 2016, 19:50 UTC\nlocation\ndescription\n' == result, result


def test_filter_future_events():
    component_past = _get_component()
    component_past.add('dtstart', datetime.datetime.now() - datetime.timedelta(hours=1))
    component_now = _get_component()
    component_now.add('dtstart', datetime.datetime.now() + datetime.timedelta(minutes=10))
    component_future = _get_component()
    component_future.add('dtstart', datetime.datetime.now() + datetime.timedelta(hours=2))
    events = [Event(component_past), Event(component_now), Event(component_future)]
    result = list(filter_future_events(events, 1))
    assert 1 == len(result), len(result)
    assert component_now.decoded('dtstart') == result[0].date, result
