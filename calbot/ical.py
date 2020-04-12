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

        after = datetime.now(tz=pytz.UTC)
        before = after + timedelta(hours=max(self.advance))

        self.all_events = list(self.read_ical(self.url, after, before))
        """list of all calendar events, from ical file"""

        future_events = filter_future_events(self.all_events, after, before)
        unnotified_events = filter_notified_events(future_events, config)
        sorted_events = sort_events(unnotified_events)

        self.events = list(sorted_events)
        """list of calendar events which should be notified, filtered from ical file"""

    def read_ical(self, url, after, before):
        """
        Reads ical file from url.
        :param url: url to read
        :param after: also generate repeating events after this datetime
        :param before: also generate repeating events before this datetime
        :return: it's generator, yields each event read from ical
        """
        # TODO also filter past events to avoid reading of the whole calendar
        logger.info('Getting %s', url)
        with urlopen(url) as f:
            timezone_set = 'none'
            explicit_events = set()

            vcalendar = icalendar.Calendar.from_ical(f.read())
            self.name = str(vcalendar.get('X-WR-CALNAME'))
            self.description = str(vcalendar.get('X-WR-CALDESC'))

            if vcalendar.get('X-WR-TIMEZONE') is not None:
                self.timezone = pytz.timezone(str(vcalendar.get('X-WR-TIMEZONE')))
                timezone_set = 'x-wr-timezone'

            for component in vcalendar.walk():
                if component.name == 'VTIMEZONE' and timezone_set in ('none', 'x-wr-timezone'):
                    try:
                        self.timezone = pytz.timezone(str(component.get('TZID')))
                        timezone_set = 'vtimezone.tzid'
                    except Exception as e:
                        logger.warning(e)

                elif component.name == 'VEVENT':
                    event = Event.from_vevent(component, self.timezone, self.day_start)
                    explicit_events.add(event.instance_id)
                    yield event
                    try:
                        for repeat in event.repeat_between(after, before, explicit_events):
                            yield repeat
                    except:
                        logger.warning('Failed to repeat %s at %s %s',
                            event.id, str(event.date), str(event.time), exc_info=True)


class Event:
    """
    Calendar event as it was read from ical file.
    """

    def __init__(self, **kwargs):
        self.id = kwargs['id']
        """unique id of the event"""
        self.uid = kwargs.get('uid', kwargs['id'])
        """uid from vevent from """
        self.instance_id = kwargs.get('instance_id', (kwargs['id'], None))
        """event instance id, to identify each event in the sequence of recurring events"""
        self.title = kwargs['title']
        """title of the event"""
        self.location = kwargs.get('location')
        """the event location as string"""
        self.description = kwargs.get('description')
        """the event description"""
        self.date = kwargs.get('date')
        """event (start) date"""
        self.time = kwargs.get('time')
        """event (start) time, can be None"""
        self.notify_datetime = kwargs.get('notify_datetime')
        """calendar event datetime, relative to which to calculate notification moment,
        uses day_start if time for current event is None"""
        self.repeat_rule = kwargs.get('repeat_rule')
        """event repeat rule, can be None"""
        self.recurrence_id = kwargs.get('recurrence_id')
        """event recurrence ID, used to override recurred events, can be None"""
        self.notified_for_advance = kwargs.get('notified_for_advance')
        """hours in advance for which this event should be notified"""
        self.day_start = kwargs.get('day_start')
        """notification time for full-day events"""

    @classmethod
    def from_vevent(cls, vevent, timezone, day_start=None):
        """
        Creates calendar event from vEvent component read from ical file.
        :param vevent:  vEvent component
        :param timezone:    default timezone for the calendar
        :param day_start:   notification moment for full-day events
        :return: calendar event instance
        """

        event_uid = str(vevent.get('UID'))
        event_title = str(vevent.get('SUMMARY'))
        event_location = str(vevent.get('LOCATION'))
        event_description = str(vevent.get('DESCRIPTION'))

        event_date = None
        event_time = None
        notify_datetime = None

        dtstart = vevent.get('DTSTART').dt
        if isinstance(dtstart, datetime):
            dtstarttz = timezoned(dtstart, timezone)
            event_date = dtstarttz.date()
            event_time = dtstarttz.timetz()
            notify_datetime = datetime.combine(event_date, event_time)
        elif isinstance(dtstart, date):
            event_date = dtstart
            notify_datetime = datetime.combine(event_date, day_start.replace(tzinfo=timezone))

        repeat_rule = vevent.content_line('DTSTART')
        if vevent.get('RRULE') is not None:
            repeat_rule += "\n" + vevent.get('RRULE').to_ical().decode('utf-8')
        if vevent.get('EXDATE') is not None:
            exdate = vevent.get('EXDATE')
            try:
                exlist = []
                if isinstance(exdate, list):
                    exlist = exdate
                else:
                    exlist = [ exdate ]
                for exd in exlist:
                    repeat_rule += "\n" + exd.to_ical().decode('utf-8')
            except:
                logger.warning('Failed to get EXDATE: %s', str(vevent.get('EXDATE')), exc_info=True)

        # https://www.kanzaki.com/docs/ical/recurrenceId.html
        recurrence_id = None
        if vevent.get('RECURRENCE-ID') is not None:
            try:
                recurrence_id = timezoned(vevent.get('RECURRENCE-ID').dt, timezone)
            except:
                logger.warning('Failed to get RECURRENCE-ID: %s', str(vevent.get('RECURRENCE-ID')), exc_info=True)

        if recurrence_id is None:
            event_id = event_uid
        else:
            event_id = "%s_%s" % (event_uid, str(recurrence_id))

        event_instance_id = (event_uid, notify_datetime)

        event_day_start = day_start.replace(tzinfo=timezone) if day_start is not None else None

        return cls(
            id=event_id,
            uid=event_uid,
            instance_id=event_instance_id,
            title=event_title,
            location=event_location,
            description=event_description,
            date=event_date,
            time=event_time,
            notify_datetime=notify_datetime,
            repeat_rule=repeat_rule,
            recurrence_id=recurrence_id,
            day_start=event_day_start
        )

    @classmethod
    def copy_for_date(cls, event, newdatetime):

        event_id = event.id
        event_date = None
        event_time = None
        notify_datetime = None

        if isinstance(newdatetime, datetime):
            event_date = newdatetime.date()
            event_time = newdatetime.timetz()
            notify_datetime = datetime.combine(event_date, event_time)
            event_id += '_' + notify_datetime.isoformat()
        elif isinstance(newdatetime, date):
            event_date = newdatetime
            notify_datetime = datetime.combine(event_date, event.day_start)
            event_id += '_' + event_date.isoformat()

        event_instance_id = (event.uid, notify_datetime)

        return cls(
            id=event_id,
            uid=event.uid,
            instance_id=event_instance_id,
            title=event.title,
            location=event.location,
            description=event.description,
            date=event_date,
            time=event_time,
            notify_datetime=notify_datetime,
            day_start=event.day_start
        )

    def repeat_between(self, after, before, explicit_events=None):
        """
        Creates copies of this event repeating between specified datetime.
        The resulting list never includes the original (this) event.
        :param after:           start of the interval (exclusive)
        :param before:          end of the interval (inclusive)
        :param explicit_events: set of (id, datetime) pairs to skip repetition at these moments
        :return:    list of event repeats, each with it's own unique id
        """
        if self.repeat_rule is None:
            return []

        if self.time is not None:
            dtstart = datetime.combine(self.date, self.time)
            rule = rrule.rrulestr(self.repeat_rule)
            dates = rule.between(after, before, inc=True)
        else:
            dtstart = self.date
            rule = rrule.rrulestr(self.repeat_rule)
            # TODO: It still fails for full-day events with RRULE:FREQ=MONTHLY;WKST=MO;UNTIL=20150513T235959Z;BYMONTHDAY=14
            dates = rule.between(after.replace(tzinfo=None), before.replace(tzinfo=None), inc=True)

        dates = list(filter(lambda d: d != dtstart, dates))
        dates = list(filter(lambda d: d != after, dates))
        if explicit_events is not None:
            dates = list(filter(lambda d: self._instance_id_at(d) not in explicit_events, dates))
        events = list(map(lambda d: Event.copy_for_date(self, d), dates))
        return events

    def _instance_id_at(self, dt):
        return self.uid, dt

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


def filter_future_events(events, after, before):
    """
    Filters only events which are after and before the specified datetime
    :param events:  iterable of events
    :param after:   filter events after this datetime (exclusive)
    :param before:  filter events before this datetime (inclusive)
    :return: it's generator, yields each filtered event
    """
    for event in events:
        if after < event.notify_datetime <= before:
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


def timezoned(dt, timezone):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return timezone.localize(dt)
        elif dt.tzinfo == pytz.UTC:
            return dt.astimezone(timezone)
        else:
            return dt
    else:
        return dt


def _get_sample_event():
    now = datetime.now(tz=pytz.timezone('Asia/Omsk'))
    return Event(
        id='SAMPLE EVENT',
        uid='SAMPLE EVENT',
        instance_id=('SAMPLE EVENT', now),
        title='This is sample event',
        location='It happens in Milky Way',
        description='The sample event is to demonstrate how the event can be formatted',
        date=now.date(),
        time=now.timetz())


sample_event = _get_sample_event()
