#!/usr/bin/python3
# -*- coding: utf-8 -*-


import logging
from urllib.request import urlopen
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from icalendar import Calendar


logger = logging.getLogger()


CALENDAR_URL = 'https://calendar.google.com/calendar/ical/rvsmtm05j6qc2126epnngu9kq0%40group.calendar.google.com/private-5d15121a99e8d543ae656471323b26e7/basic.ics'
TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
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


def run_bot(token, interval=3600):

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


def read_ical(url):
    with urlopen(url) as f:
        ical = Calendar.from_ical(f.read())
        for component in ical.walk():
            if component.name == 'VEVENT':
                yield component


def format_event(event):
    return FORMAT.format(
        title=event.get('summary'),
        date=event.get('dtstamp').dt,
        location=event.get('location'),
        description=event.get('description'))


def main():
    run_bot(TOKEN)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
