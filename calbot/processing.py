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
from calbot.stats import update_stats


__all__ = ['update_calendars_job', 'update_calendars', 'update_calendar']

logger = logging.getLogger('processing')


def update_calendars_job(bot, job):
    """
    Job queue callback.
    Runs the update of all calendars one by one.
    Finally, updates statistics.
    :param bot: Bot instance
    :param job: it's context contains main config
    :return: None
    """
    config = job.context
    update_calendars(bot, config)


def update_calendars(bot, config):
    """
    Runs the update of all calendars one by one.
    Finally, updates statistics.
    :param bot: Bot instance
    :param config: main config
    :return: None
    """
    for calendar in config.all_calendars():
        update_calendar(bot, calendar)
    update_stats(config)


def update_calendar(bot, config):
    """
    Update data from the calendar.
    Reads ical file and notifies events if necessary.
    After the first successful read the calendar is marked as validated.
    :param bot: Bot instance
    :param config: CalendarConfig instance to persist and update events notification status
    :return: None
    """
    if not config.enabled:
        logger.info('Skipping processing of disabled calendar %s of user %s', config.id, config.user_id)
        return

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

        config.save_error(None)     # successful processing completion
    except Exception as e:
        logger.warning('Failed to process calendar %s of user %s', config.id, config.user_id, exc_info=True)
        was_enabled = config.enabled
        config.save_error(e)        # unsuccessful completion

        if config.enabled and not config.verified:  # still enabled
            try:
                bot.sendMessage(chat_id=config.user_id,
                                text='Failed to process calendar /cal%s:\n%s' % (config.id, e))
            except Exception:
                logger.error('Failed to send message to user %s', config.user_id, exc_info=True)

        if was_enabled and not config.enabled:      # just disabled
            try:
                bot.sendMessage(chat_id=config.user_id,
                                text='Calendar /cal%s is disabled due too many processing errors\n' % config.id)
            except Exception:
                logger.error('Failed to send message to user %s', config.user_id, exc_info=True)


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
