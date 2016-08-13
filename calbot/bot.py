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
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import Job
from .ical import Calendar

FORMAT = '''{title}
{date:%A, %d %B %Y, %H:%M %Z}
{location}
{description}
'''

GREETING = '''Hello, I'm calendar bot, please give me some commands.
/add ical_url @channel — to add new iCal to be sent to a channel
/list — to see all configured calendars
/del id — remove calendar by id
/format [new format] — get or set a calendar event formatting, use {title}, {date}, {location} and {description} variables
/advance [hours...] — get or set calendar events advance, i.e. how many hours before the event to publish it
'''


__all__ = ['run_bot']


logger = logging.getLogger('bot')


def run_bot(config):
    updater = Updater(config.token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', start))

    def add_calendar_to_config(bot, update, args, job_queue):
        add_calendar(bot, update, args, job_queue, config)
    dispatcher.add_handler(CommandHandler('add', add_calendar_to_config, allow_edited=True, pass_args=True, pass_job_queue=True))

    dispatcher.add_handler(MessageHandler([Filters.command], unknown))

    dispatcher.add_error_handler(error)

    updater.start_polling(clean=True)

    start_delay = 0
    for calendar in config.calendars():
        queue_calendar_update(updater.job_queue, calendar, start_delay)
        start_delay += 1

    updater.idle()


def queue_calendar_update(job_queue, calendar, start_delay=0):
    def update_this_calendar(bot, job):
        update_calendar(bot, calendar)
    job = Job(update_this_calendar, calendar.interval, repeat=True)
    job_queue.put(job, next_t=start_delay)


def start(bot, update):
    logger.info('started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text=GREETING)


def add_calendar(bot, update, args, job_queue, config):
    user_id = str(update.message.chat_id)
    if len(args) < 2:
        bot.sendMessage(chat_id=user_id,
                        text="Please provide two arguments to /add command:\n/add ical_url @channel")
        return

    url = args[0]
    channel_id = args[1]
    calendar = config.add_calendar(user_id, url, channel_id)
    queue_calendar_update(job_queue, calendar)

    bot.sendMessage(chat_id=user_id,
                    text="Calendar %s is queued for verification" % url)


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I don't understand that command.")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def update_calendar(bot, config):
    try:
        calendar = Calendar(config)
        for event in calendar.events:
            send_event(bot, config.channel_id, event)
            config.event_notified(event)
        config.save_events()
        if not config.verified:
            bot.sendMessage(chat_id=config.channel_id,
                            text='Events from %s will be notified here' % calendar.name)
            config.save_calendar(calendar)
            bot.sendMessage(chat_id=config.user_id,
                            text='Added:\n%s %s %s' % (config.id, config.name, config.channel_id))
    except Exception as e:
        logger.warning('Failed to process %s', config.url, exc_info=True)
        if not config.verified:
            bot.sendMessage(chat_id=config.user_id,
                            text='Failed to process %s:\n%s' % (config.url, e))


def send_event(bot, channel_id, event):
    bot.sendMessage(chat_id=channel_id, text=format_event(event))


def format_event(event):
    return FORMAT.format(**event.to_dict())
