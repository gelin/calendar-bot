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
from telegram.ext import MessageHandler, Filters
from .ical import read_ical


CALENDAR_URL = 'https://calendar.google.com/calendar/ical/rvsmtm05j6qc2126epnngu9kq0%40group.calendar.google.com/private-5d15121a99e8d543ae656471323b26e7/basic.ics'
CHAT_ID = '@gelintestchannel'
FORMAT = '''{title}
{date}
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


logger = logging.getLogger('bot')


def run_bot(token, interval=3600):
    updater = Updater(token)
    job_queue = updater.job_queue

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', start))
    dispatcher.add_handler(MessageHandler([Filters.command], unknown))

    dispatcher.add_error_handler(error)

    updater.start_polling()

    job_queue.put(send_events, interval=interval, next_t=0, repeat=True)

    updater.idle()


def start(bot, update):
    logger.info('started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text=GREETING)


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I don't understand that command.")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def send_events(bot):
    events = list(read_ical(CALENDAR_URL))
    for event in events:
        send_event(bot, event)


def send_event(bot, event):
    bot.sendMessage(chat_id=CHAT_ID, text=format_event(event))


def format_event(event):
    return FORMAT.format(
        title=event.get('summary'),
        date=event.get('dtstamp').dt,
        location=event.get('location'),
        description=event.get('description'))