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
import shutil

from icalendar.cal import Component

from calbot.formatting import normalize_locale, format_event
from calbot.conf import CalendarConfig, Config, UserConfig, UserConfigFile, DEFAULT_FORMAT, CalendarsConfigFile
from calbot.ical import Event, Calendar, filter_future_events, filter_notified_events, sort_events
from calbot.stats import update_stats, get_stats


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
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    result = format_event(user_config, event)
    assert 'summary\nThursday, 23 June 2016, 19:50 UTC\nlocation\ndescription' == result, result


def test_read_calendar():
    config = CalendarConfig.new(
        UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
        '1', 'file://{}/test.ics'.format(os.path.dirname(__file__)), 'TEST')
    calendar = Calendar(config)
    assert pytz.timezone('Asia/Omsk') == calendar.timezone, calendar.timezone
    assert 'Тест' == calendar.name, calendar.name
    assert 'Just a test calendar' == calendar.description, calendar.description
    assert datetime.date(2016, 6, 24) == calendar.all_events[0].date, calendar.all_events[0].date
    assert datetime.time(6, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')) == calendar.all_events[0].time, calendar.all_events[0].time
    assert 'Событие по-русски' == calendar.all_events[0].title, calendar.all_events[0].title
    assert datetime.date(2016, 6, 23) == calendar.all_events[1].date, calendar.all_events[1].date
    assert datetime.time(6, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')) == calendar.all_events[1].time, calendar.all_events[1].time
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
    assert component_now.decoded('dtstart') == result[0].notify_datetime, result


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
    assert component_now.decoded('dtstart') == result[0].notify_datetime, result
    assert component_future24.decoded('dtstart') == result[1].notify_datetime, result


def test_date_only_event():
    timezone = pytz.UTC
    component = _get_component()
    component.add('dtstart', datetime.date.today())
    event = Event(component, timezone, datetime.time(10, 0))
    assert isinstance(event.date, datetime.date), event.date.__class__.__name__
    assert event.time is None, event.time
    assert 10 == event.notify_datetime.hour, event.date
    assert 0 == event.notify_datetime.minute, event.date
    assert pytz.UTC == event.notify_datetime.tzinfo, event.date


def test_default_user_confg():
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    assert user_config.vardir == 'var'
    assert user_config.interval == 3600
    assert user_config.id == 'TEST'
    assert user_config.format == DEFAULT_FORMAT
    assert user_config.language is None
    assert user_config.advance == [48, 24]


def test_default_calendar_config():
    calendar_config = CalendarConfig.new(
        UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
        '1', 'file://{}/test.ics'.format(os.path.dirname(__file__)), 'TEST')
    assert calendar_config.advance == [48, 24]


def test_set_format():
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    user_config.set_format("TEST FORMAT")
    assert user_config.format == "TEST FORMAT", user_config.format
    config_file = UserConfigFile('var', 'TEST')
    user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
    assert user_config.format == "TEST FORMAT", user_config.format
    shutil.rmtree('var/TEST')


def test_set_language():
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    user_config.set_language("TEST_LANGUAGE")
    assert user_config.language == "TEST_LANGUAGE", user_config.language
    config_file = UserConfigFile('var', 'TEST')
    user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
    assert user_config.language == "TEST_LANGUAGE", user_config.language
    shutil.rmtree('var/TEST')


def test_format_event_ru():
    component = _get_component()
    component.add('dtstart', datetime.datetime(2016, 6, 23, 19, 50, 35, tzinfo=pytz.UTC))
    event = Event(component, pytz.UTC)
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    user_config.language = 'ru_RU.UTF-8'
    result = format_event(user_config, event)
    assert 'summary\nЧетверг, 23 Июнь 2016, 19:50 UTC\nlocation\ndescription' == result, result


def test_normalize_locale():
    result = normalize_locale('it')
    assert 'it_IT.UTF-8' == result, result


def test_set_advance():
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    user_config.set_advance(['1', '3', '2', '3'])
    assert user_config.advance == [3, 2, 1], user_config.advance
    config_file = UserConfigFile('var', 'TEST')
    user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
    assert user_config.advance == [3, 2, 1], user_config.advance
    shutil.rmtree('var/TEST')


def test_sort_events():
    timezone = pytz.UTC
    component_past = _get_component()
    component_past.add('dtstart', datetime.datetime.now(tz=timezone) - datetime.timedelta(hours=1))
    component_now = _get_component()
    component_now.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(minutes=10))
    component_future = _get_component()
    component_future.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(hours=2))
    events = [Event(component_future, timezone), Event(component_now, timezone), Event(component_past, timezone)]
    result = list(sort_events(events))
    assert events[2] == result[0], result
    assert events[1] == result[1], result
    assert events[0] == result[2], result


def test_format_date_only_event():
    timezone = pytz.UTC
    component = _get_component()
    component.add('dtstart', datetime.date(2016, 6, 23))
    event = Event(component, timezone, datetime.time(10, 0))
    user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
    result = format_event(user_config, event)
    assert 'summary\nThursday, 23 June 2016\nlocation\ndescription' == result, result


def test_save_calendar():
    calendar_config = CalendarConfig.new(
        UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
        '1', 'file://{}/test.ics'.format(os.path.dirname(__file__)), 'TEST')
    calendar = Calendar(calendar_config)
    calendar_config.save_calendar(calendar)
    config_file = CalendarsConfigFile('var', 'TEST')
    calendar_config = CalendarConfig.load(
        UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
        config_file.read_parser(),
        '1')
    assert calendar_config.name == 'Тест', calendar_config.name
    shutil.rmtree('var/TEST')


def test_update_stats():
    config = Config('calbot.cfg.sample')
    update_stats(config)
    stats1 = get_stats(config)
    calendar_config = CalendarConfig.new(
        UserConfig.new(config, 'TEST'),
        '1', 'file://{}/test.ics'.format(os.path.dirname(__file__)), 'TEST')
    calendar = Calendar(calendar_config)
    calendar_config.save_calendar(calendar)
    update_stats(config)
    stats2 = get_stats(config)
    assert (stats2.users - stats1.users) == 1, '%i -> %i' % (stats1.users, stats2.users)
    assert (stats2.calendars - stats1.calendars) == 1, '%i -> %i' % (stats1.calendars, stats2.calendars)
    assert stats2.events == stats1.events, '%i -> %i' % (stats1.events, stats2.events)
    shutil.rmtree('var/TEST')
