# -*- coding: utf-8 -*-

# Copyright 2017 Denis Nelubin.
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

from calbot.formatting import format_event
from calbot.ical import Calendar


__all__ = ['queue_calendar_update']

logger = logging.getLogger('processing')


def queue_calendar_update(job_queue, calendar, start_delay=0):
    """
    Adds the configured calendar to queue for processing
    :param job_queue: bot's job queue
    :param calendar: CalendarConfig instance
    :param start_delay: delay start of immediate calendar processing for specified number of seconds
    :return: None
    """
    job_queue.run_repeating(update_calendar, calendar.interval, first=start_delay, context=calendar)


def update_calendar(bot, job):
    """
    Job queue callback to update data from the calendar.
    Reads ical file and notifies events if necessary.
    After the first successful read the calendar is marked as validated.
    :param bot: Bot instance
    :param job: it's context has CalendarConfig instance to persist and update events notification status
    :return: None
    """
    config = job.context
    try:
        calendar = Calendar(config)
        for event in calendar.events:
            send_event(bot, config, event)
            config.event_notified(event)
        config.save_events()
        if not config.verified:
            bot.sendMessage(chat_id=config.channel_id,
                            text='Events from %s will be notified here' % calendar.name)
            config.save_calendar(calendar)
            bot.sendMessage(chat_id=config.user_id,
                            text='''Added calendar %s
Name: %s
URL: %s
Channel: %s''' % (config.id, config.name, config.url, config.channel_id))
    except Exception as e:
        logger.warning('Failed to process calendar %s of user %s', config.id, config.user_id, exc_info=True)
        if not config.verified:
            bot.sendMessage(chat_id=config.user_id,
                            text='Failed to process calendar %s:\n%s' % (config.id, e))
        config.save_error(e)


def send_event(bot, config, event):
    """
    Sends the event notification to the channel
    :param bot: Bot instance
    :param config: CalendarConfig instance
    :param event: Event instance, read from ical
    :return: None
    """
    logger.info('Sending event %s "%s" to %s', event.id, event.title, config.channel_id)
    bot.sendMessage(chat_id=config.channel_id, text=format_event(config, event))
