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

from icalendar.cal import Component

from calbot.bot import format_event
from calbot.ical import Event


def test_format_event():
    component = Component()
    component.add('summary', 'summary')
    component.add('dtstamp', datetime.datetime(2016, 6, 23, 19, 50, 35))
    component.add('location', 'location')
    component.add('description', 'description')
    event = Event(component)
    result = format_event(event)
    assert 'summary\nThursday, 23 June 2016, 19:50 UTC\nlocation\ndescription\n' == result, result
