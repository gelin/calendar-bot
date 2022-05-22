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
import unittest
import pytz
import shutil
from dateutil.parser import parse

from icalendar.cal import Component

from calbot.formatting import normalize_locale, format_event, strip_tags
from calbot.conf import CalendarConfig, Config, UserConfig, UserConfigFile, DEFAULT_FORMAT, CalendarsConfigFile
from calbot.ical import Event, Calendar, filter_notified_events, sort_events
from calbot.stats import update_stats, get_stats


def _get_component():
    component = Component()
    component.add('summary', 'summary')
    component.add('location', 'location')
    component.add('description', 'description')
    return component


class CalbotTestCase(unittest.TestCase):

    def test_format_event(self):
        component = _get_component()
        component.add('dtstart', datetime.datetime(2016, 6, 23, 19, 50, 35, tzinfo=pytz.UTC))
        event = Event.from_vevent(component, pytz.UTC)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        result = format_event(user_config, event)
        self.assertEqual(
            'summary\n'
            'Thursday, 23 June 2016, 19:50 UTC\n'
            'location\n'
            'description',
            result)

    # TODO: fix event time assertion
    def test_read_calendar(self):
        config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/test.ics'.format(os.path.dirname(__file__)), 'TEST')

        calendar = Calendar(config)
        self.assertEqual(pytz.timezone('Asia/Omsk'), calendar.timezone)
        self.assertEqual('Тест', calendar.name)
        self.assertEqual('Just a test calendar', calendar.description)

        for e in calendar.all_events:
            print(e)
        self.assertEqual(2, len(calendar.all_events))
        # events in the past are skipped, daily event is repeated for 48 hours to future

        # event in the past, skipped
        # event = calendar.all_events[0]
        # self.assertEqual(datetime.date(2016, 6, 24), event.date)
        # self.assertEqual(datetime.time(6, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')), event.time)
        # self.assertEqual('Событие по-русски', event.title)

        # event in the past, skipped
        # event = calendar.all_events[1]
        # self.assertEqual(datetime.date(2016, 6, 23), event.date)
        # self.assertEqual(datetime.time(6, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')), event.time)
        # self.assertEqual('Event title', event.title)

        today = datetime.date.today()
        event = calendar.all_events[0]
        self.assertEqual(today + datetime.timedelta(days=1), event.date)
        self.assertEqual(datetime.time(10, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')), event.time)
        self.assertEqual('Daily event', event.title)
        event = calendar.all_events[1]
        self.assertTrue(today + datetime.timedelta(days=2), event.date)
        self.assertEqual(datetime.time(10, 0, 0, tzinfo=pytz.timezone('Asia/Omsk')), event.time)
        self.assertEqual('Daily event', event.title)

    def test_filter_notified_events(self):
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

        events = [Event.from_vevent(component_now, timezone), Event.from_vevent(component_future24, timezone),
                  Event.from_vevent(component_future48, timezone)]
        config = TestCalendarConfig()
        result = list(filter_notified_events(events, config))
        self.assertEqual(2, len(result))
        self.assertEqual(component_now.decoded('dtstart'), result[0].notify_datetime)
        self.assertEqual(component_future24.decoded('dtstart'), result[1].notify_datetime)

    def test_date_only_event(self):
        timezone = pytz.UTC
        component = _get_component()
        component.add('dtstart', datetime.date.today())
        event = Event.from_vevent(component, timezone, datetime.time(10, 0))
        self.assertTrue(isinstance(event.date, datetime.date))
        self.assertIsNone(event.time)
        self.assertEqual(10, event.notify_datetime.hour)
        self.assertEqual(0, event.notify_datetime.minute)
        self.assertEqual(pytz.UTC, event.notify_datetime.tzinfo)

    def test_default_user_config(self):
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        self.assertEqual('var', user_config.vardir)
        self.assertEqual('TEST', user_config.id)
        self.assertEqual(DEFAULT_FORMAT, user_config.format)
        self.assertIsNone(user_config.language)
        self.assertEqual([48, 24], user_config.advance)
        self.assertEqual(3, user_config.errors_count_threshold)

    def test_default_calendar_config(self):
        calendar_config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/test.ics'.format(os.path.dirname(__file__)), 'TEST')
        self.assertEqual([48, 24], calendar_config.advance)
        self.assertEqual(3, calendar_config.errors_count_threshold)
        self.assertEqual(0, calendar_config.last_errors_count)
        self.assertTrue(calendar_config.enabled)

    def test_set_format(self):
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.set_format("TEST FORMAT")
        self.assertEqual('TEST FORMAT', user_config.format)
        config_file = UserConfigFile('var', 'TEST')
        user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
        self.assertEqual('TEST FORMAT', user_config.format)
        shutil.rmtree('var/TEST')

    def test_set_language(self):
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.set_language("TEST_LANGUAGE")
        self.assertEqual('TEST_LANGUAGE', user_config.language)
        config_file = UserConfigFile('var', 'TEST')
        user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
        self.assertEqual('TEST_LANGUAGE', user_config.language)
        shutil.rmtree('var/TEST')

    def test_format_event_ru(self):
        component = _get_component()
        component.add('dtstart', datetime.datetime(2016, 6, 23, 19, 50, 35, tzinfo=pytz.UTC))
        event = Event.from_vevent(component, pytz.UTC)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'summary\n'
            'Четверг, 23 июня 2016, 19:50 UTC\n'
            'location\n'
            'description',
            result)

    def test_normalize_locale(self):
        result = normalize_locale('it')
        self.assertEqual('it_IT.UTF-8', result)

    def test_set_advance(self):
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.set_advance(['1', '3', '2', '3'])
        self.assertEqual([3, 2, 1], user_config.advance)
        config_file = UserConfigFile('var', 'TEST')
        user_config = UserConfig.load(Config('calbot.cfg.sample'), 'TEST', config_file.read_parser())
        self.assertEqual([3, 2, 1], user_config.advance)
        shutil.rmtree('var/TEST')

    def test_sort_events(self):
        timezone = pytz.UTC
        component_past = _get_component()
        component_past.add('dtstart', datetime.datetime.now(tz=timezone) - datetime.timedelta(hours=1))
        component_now = _get_component()
        component_now.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(minutes=10))
        component_future = _get_component()
        component_future.add('dtstart', datetime.datetime.now(tz=timezone) + datetime.timedelta(hours=2))
        events = [Event.from_vevent(component_future, timezone), Event.from_vevent(component_now, timezone),
                  Event.from_vevent(component_past, timezone)]
        result = list(sort_events(events))
        self.assertEqual(events[2], result[0])
        self.assertEqual(events[1], result[1])
        self.assertEqual(events[0], result[2])

    def test_format_date_only_event(self):
        timezone = pytz.UTC
        component = _get_component()
        component.add('dtstart', datetime.date(2016, 6, 23))
        event = Event.from_vevent(component, timezone, datetime.time(10, 0))
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        result = format_event(user_config, event)
        self.assertEqual(
            'summary\n'
            'Thursday, 23 June 2016\n'
            'location\n'
            'description',
            result)

    def test_save_calendar(self):
        calendar_config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/test.ics'.format(os.path.dirname(__file__)), 'TEST')
        calendar = Calendar(calendar_config)
        calendar_config.save_calendar(calendar)
        config_file = CalendarsConfigFile('var', 'TEST')
        calendar_config = CalendarConfig.load(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            config_file.read_parser(),
            '1')
        self.assertEqual('Тест', calendar_config.name)
        self.assertEqual(3, calendar_config.errors_count_threshold)
        self.assertEqual(0, calendar_config.last_errors_count)
        self.assertTrue(calendar_config.enabled)
        shutil.rmtree('var/TEST')

    def test_update_stats(self):
        config = Config('calbot.cfg.sample')
        update_stats(config)
        stats1 = get_stats(config)
        calendar_config = CalendarConfig.new(
            UserConfig.new(config, 'TEST'),
            '1', 'file://{}/test/test.ics'.format(os.path.dirname(__file__)), 'TEST')
        calendar = Calendar(calendar_config)
        calendar_config.save_calendar(calendar)
        update_stats(config)
        stats2 = get_stats(config)
        self.assertEqual(1, (stats2.users - stats1.users))
        self.assertEqual(1, (stats2.calendars - stats1.calendars))
        self.assertEqual(stats2.events, stats1.events)
        shutil.rmtree('var/TEST')

    def test_calendar_save_error(self):
        calendar_config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/test.ics'.format(os.path.dirname(__file__)), 'TEST')
        now = datetime.datetime.utcnow()
        calendar_config.save_error(Exception('TEST ERROR'))
        config_file = CalendarsConfigFile('var', 'TEST')
        calendar_config = CalendarConfig.load(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            config_file.read_parser(),
            '1')
        self.assertTrue(parse(calendar_config.last_process_at) > now)
        self.assertEqual('TEST ERROR', calendar_config.last_process_error)
        self.assertEqual(3, calendar_config.errors_count_threshold)
        self.assertEqual(1, calendar_config.last_errors_count)
        self.assertTrue(calendar_config.enabled)

        now = datetime.datetime.utcnow()
        calendar_config.save_error(Exception('TEST ERROR 2'))
        calendar_config = CalendarConfig.load(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            config_file.read_parser(),
            '1')
        calendar_config.save_error(Exception('TEST ERROR 3'))
        calendar_config = CalendarConfig.load(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            config_file.read_parser(),
            '1')
        self.assertTrue(parse(calendar_config.last_process_at) > now)
        self.assertEqual('TEST ERROR 3', calendar_config.last_process_error)
        self.assertEqual(3, calendar_config.last_errors_count)
        self.assertFalse(calendar_config.enabled)

        shutil.rmtree('var/TEST')

    def test_format_event_html(self):
        component = Component()
        component.add('summary', '<b>summary</b>')
        component.add('location', '<i>location</i>')
        component.add('description',
                      '<b>description</b>'
                      '<br>'
                      '<br>&nbsp;<a href="link.html">link</a>')
        component.add('dtstart', datetime.datetime(2018, 2, 3, 13, 3, 4, tzinfo=pytz.UTC))
        event = Event.from_vevent(component, pytz.UTC)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'summary\n'
            'Суббота, 03 февраля 2018, 13:03 UTC\n'
            'location\n'
            'description'
            '\n'
            '\n link (link.html)',
            result)

    def test_format_event_blanks(self):
        component = Component()
        component.add('dtstart', datetime.datetime(2018, 2, 3, 13, 3, 4, tzinfo=pytz.UTC))
        event = Event.from_vevent(component, pytz.UTC)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'None\n'
            'Суббота, 03 февраля 2018, 13:03 UTC\n'
            'None\n'
            'None',
            result)

    def test_strip_tags_href(self):
        result = strip_tags('<a href="http://example.com">example</a>\n'
            '<a href="http://example.com">http://example.com</a>\n'
            '<a href="http://example.com">example.com</a>\n'
            '<a href="https://vk.com/away.php?to=http:%2F%2Fmlomsk.1der.link">mlomsk.1der.link/telegram/chat</a>\n')
        self.assertEqual('example (http://example.com)\n'
            'http://example.com\n'
            'example.com\n'
            'mlomsk.1der.link/telegram/chat\n', result)

    def test_format_event_real_html_tags_br_and_a(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '10 февраля в 11:00 пройдет 5-я встреча&nbsp;<a href="https://vk.com/mlomsk">ML клуба</a>'
                      '&nbsp;в офисе&nbsp;<a href="https://vk.com/7bits">7bits</a>, Таубе 5. '
                      'Регистрация на встречу:&nbsp;<a href="https://vk.com/away.php?to=http%3A%2F%2Fmlomsk.1der.link%2Fmeetup%2Fsignup&amp;post=-141957789_74&amp;cc_key=" target="_blank">mlomsk.1der.link/meetup/signup</a>.'
                      '<br>'
                      '<br>'
                      'В этот раз у нас будет 2 доклада:')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '10 февраля в 11:00 пройдет 5-я встреча ML клуба (https://vk.com/mlomsk)'
            ' в офисе 7bits (https://vk.com/7bits), Таубе 5. '
            'Регистрация на встречу: mlomsk.1der.link/meetup/signup.'
            '\n'
            '\n'
            'В этот раз у нас будет 2 доклада:',
            result)

    def test_format_event_real_html_tag_p(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '10 февраля в 11:00 пройдет 5-я встреча&nbsp;<a href="https://vk.com/mlomsk">ML клуба</a>'
                      '&nbsp;в офисе&nbsp;<a href="https://vk.com/7bits">7bits</a>, Таубе 5.'
                      '<p>Регистрация на встречу</p>')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '10 февраля в 11:00 пройдет 5-я встреча ML клуба (https://vk.com/mlomsk)'
            ' в офисе 7bits (https://vk.com/7bits), Таубе 5.'
            '\nРегистрация на встречу',
            result)

    def test_format_event_real_html_tag_p_with_style(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '10 февраля в 11:00 пройдет 5-я встреча&nbsp;<a href="https://vk.com/mlomsk">ML клуба</a>'
                      '&nbsp;в офисе&nbsp;<a href="https://vk.com/7bits">7bits</a>, Таубе 5.'
                      '<p style="">Регистрация на встречу</p>')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '10 февраля в 11:00 пройдет 5-я встреча ML клуба (https://vk.com/mlomsk)'
            ' в офисе 7bits (https://vk.com/7bits), Таубе 5.'
            '\nРегистрация на встречу',
            result)

    def test_format_event_real_html_tags_p(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p>10 февраля в 11:00 пройдет 5-я встреча&nbsp;<a href="https://vk.com/mlomsk">ML клуба</a>'
                      '&nbsp;в офисе&nbsp;<a href="https://vk.com/7bits">7bits</a>, Таубе 5.</p>'
                      '<p>Регистрация на встречу:&nbsp;<a href="https://vk.com/away.php?to=http%3A%2F%2Fmlomsk.1der.link%2Fmeetup%2Fsignup&amp;post=-141957789_74&amp;cc_key=" target="_blank">mlomsk.1der.link/meetup/signup</a>.</p>'
                      '<p>В этот раз у нас будет 2 доклада:</p>')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\n10 февраля в 11:00 пройдет 5-я встреча ML клуба (https://vk.com/mlomsk)'
            ' в офисе 7bits (https://vk.com/7bits), Таубе 5.\n'
            '\nРегистрация на встречу: mlomsk.1der.link/meetup/signup.\n'
            '\nВ этот раз у нас будет 2 доклада:',
            result)

    def test_format_event_real_html_tags_ul_li(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p>Всем привет!</p>'
                      '<p>Список:</p>'
                      '<ul style="">'
                      '<li>что-то</li>'
                      '<li>что-то еще</li>'
                      '</ul>'
                      'Конец!')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\nВсем привет!\n'
            '\nСписок:\n'
            '\n'
            '* что-то\n'
            '* что-то еще\n'
            '\n'
            'Конец!',
            result)

    def test_format_event_real_html_tags_ul_in_p(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p>Всем привет!</p>'
                      '<p>Список:'
                      '<ul style="">'
                      '<li>что-то</li>'
                      '<li>что-то еще</li>'
                      '</ul>'
                      '</p>'
                      'Конец!')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\nВсем привет!\n'
            '\nСписок:'
            '\n'
            '* что-то\n'
            '* что-то еще\n'
            '\n'
            'Конец!',
            result)

    def test_format_event_real_html_tags_ul_nested(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p>Всем привет!</p>'
                      '<p>Список:</p>'
                      '<ul style="">'
                      '<li>что-то</li>'
                      '<li>список внутри:'
                      '<ul style="">'
                      '<li>внутри что-то</li>'
                      '<li>внутри что-то еще</li>'
                      '</ul>'
                      '</li>'
                      '<li>что-то еще</li>'
                      '</ul>'
                      'Конец!')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\nВсем привет!\n'
            '\nСписок:\n'
            '\n'
            '* что-то\n'
            '* список внутри:\n'
            '  * внутри что-то\n'
            '  * внутри что-то еще\n'
            '* что-то еще\n'
            '\n'
            'Конец!',
            result)

    def test_format_event_real_html_tags_ol_li(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p>Всем привет!</p>'
                      '<p>Список:</p>'
                      '<ol style="">'
                      '<li>что-то</li>'
                      '<li>что-то еще</li>'
                      '</ol>'
                      'Конец!')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\nВсем привет!\n'
            '\nСписок:\n'
            '\n'
            '* что-то\n'
            '* что-то еще\n'
            '\n'
            'Конец!',
            result)

    def test_format_event_real_html_tags_ul_li_p(self):
        component = Component()
        component.add('summary', 'Встреча ML-клуба')
        component.add('location', 'ул. Таубе, 5, Омск, Омская обл., Россия, 644037')
        component.add('description',
                      '<p style="">Майский IT-субботник доверяем Gems Development!</p> '
                      '<p style="">Ребята подготовят митап для разработчиков.</p>'
                      '<p style="">Темы:&nbsp;</p>'
                      '<ul style="">'
                      '<li><p>Андрей: «Vue.js».</p></li>'
                      '<li><p>Виктор «Гибкие механизмы».</p></li>'
                      '</ul>'
                      'До встречи!')
        timezone = pytz.timezone('Asia/Omsk')
        component.add('dtstart', datetime.datetime(2018, 2, 10, 11, 0, 0, tzinfo=timezone))
        event = Event.from_vevent(component, timezone)
        user_config = UserConfig.new(Config('calbot.cfg.sample'), 'TEST')
        user_config.language = 'ru_RU.UTF-8'
        result = format_event(user_config, event)
        self.assertEqual(
            'Встреча ML-клуба\n'
            'Суббота, 10 февраля 2018, 11:00 Asia/Omsk\n'
            'ул. Таубе, 5, Омск, Омская обл., Россия, 644037\n'
            '\nМайский IT-субботник доверяем Gems Development!\n '
            '\nРебята подготовят митап для разработчиков.\n'
            '\nТемы: \n'
            '\n'
            '* Андрей: «Vue.js».\n'
            '* Виктор «Гибкие механизмы».\n'
            '\n'
            'До встречи!',
            result)

    def test_read_repeated_event_override(self):
        timezone = pytz.timezone('Asia/Omsk')

        config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/repeat.ics'.format(os.path.dirname(__file__)), 'TEST')
        calendar = Calendar(config)
        self.assertEqual(timezone, calendar.timezone)

        events = sort_events(list(
            calendar.read_ical(calendar.url,
                               datetime.datetime(2020, 3, 23, 0, 0, 0, tzinfo=timezone),
                               datetime.datetime(2020, 4, 26, 23, 59, 59, tzinfo=timezone))
        ))

        for e in events:
            print(e)
        self.assertEqual(3, len(events))

        event = events[0]
        self.assertEqual(datetime.date(2020, 3, 25), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата Ужин (OML)', event.title)
        self.assertRegex(event.description, r'Пиццот')
        event = events[1]
        self.assertEqual(datetime.date(2020, 4, 8), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата Ужин (OML)', event.title)
        self.assertRegex(event.description, r'discord')
        event = events[2]
        self.assertEqual(datetime.date(2020, 4, 22), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата Ужин (OML)', event.title)
        self.assertRegex(event.description, r'Пиццот')

        ids = set(map(lambda e: e.id, events))
        self.assertEqual(len(events), len(ids))  # all ids must be unique

    def test_read_repeated_event_until(self):
        timezone = pytz.timezone('Asia/Omsk')

        config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/repeat.ics'.format(os.path.dirname(__file__)), 'TEST')
        calendar = Calendar(config)

        events = sort_events(list(
            calendar.read_ical(calendar.url,
                               datetime.datetime(2019, 1, 21, 0, 0, 0, tzinfo=timezone),
                               datetime.datetime(2019, 2, 10, 23, 59, 59, tzinfo=timezone))
        ))

        for e in events:
            print(e)
        self.assertEqual(4, len(events))

        event = events[0]
        self.assertEqual(datetime.date(2019, 1, 23), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата ужин (OML)', event.title)
        self.assertRegex(event.description, r'Бутерbrot')
        event = events[3]
        self.assertEqual(datetime.date(2019, 2, 6), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата ужин (OML)', event.title)
        self.assertRegex(event.description, r'Розы Морозы')

        print('---')

        events = sort_events(list(
            calendar.read_ical(calendar.url,
                               datetime.datetime(2019, 3, 4, 0, 0, 0, tzinfo=timezone),
                               datetime.datetime(2019, 3, 24, 23, 59, 59, tzinfo=timezone))
        ))

        for e in events:
            print(e)
        self.assertEquals(5, len(events))

        event = events[0]
        self.assertEqual(datetime.date(2019, 3, 6), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата ужин (OML)', event.title)
        self.assertRegex(event.description, r'Розы Морозы')
        event = events[3]
        self.assertEqual(datetime.date(2019, 3, 20), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата ужин (OML)', event.title)
        self.assertRegex(event.description, r'Пиццот')

    def test_read_repeated_event_exdate(self):
        timezone = pytz.timezone('Asia/Omsk')

        config = CalendarConfig.new(
            UserConfig.new(Config('calbot.cfg.sample'), 'TEST'),
            '1', 'file://{}/test/repeat.ics'.format(os.path.dirname(__file__)), 'TEST')
        calendar = Calendar(config)

        events = sort_events(list(
            calendar.read_ical(calendar.url,
                               datetime.datetime(2019, 12, 16, 0, 0, 0, tzinfo=timezone),
                               datetime.datetime(2020, 1, 19, 23, 59, 59, tzinfo=timezone))
        ))

        for e in events:
            print(e)
        self.assertEqual(2, len(events))

        event = events[0]
        self.assertEqual(datetime.date(2019, 12, 18), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата Ужин (OML)', event.title)
        self.assertRegex(event.description, r'Пиццот')
        event = events[1]
        self.assertEqual(datetime.date(2020, 1, 15), event.date)
        self.assertEqual(datetime.time(19, 0, 0, tzinfo=timezone), event.time)
        self.assertEqual('Дата Ужин (OML)', event.title)
        self.assertRegex(event.description, r'Пиццот')
