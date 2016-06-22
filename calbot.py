#!/usr/bin/python3
# -*- coding: utf-8 -*-


import logging
from urllib.request import urlopen
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from icalendar import Calendar


logger = logging.getLogger(__name__)
job_queue = None
events = []


CALENDAR_URL = 'https://calendar.google.com/calendar/ical/rvsmtm05j6qc2126epnngu9kq0%40group.calendar.google.com/private-5d15121a99e8d543ae656471323b26e7/basic.ics'
TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
CHAT_ID = '@gelintestchannel'


def main():
    global events
    events = list(read_ical(CALENDAR_URL))
    start_bot()


def start_bot():
    global job_queue

    updater = Updater(token=TOKEN)
    job_queue = updater.job_queue

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler([Filters.command], unknown))

    dispatcher.add_error_handler(error)

    updater.start_polling()

    job_queue.put(send_events, 0, repeat=False)

    updater.idle()


def start(bot, update):
    logger.info('started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a test bot, please talk to me!")


def send_events(bot):
    global events
    for event in events:
        send_event(bot, event)


def send_event(bot, event):
    bot.sendMessage(chat_id=CHAT_ID, text=format_event(event))


def format_event(event):
    return '{title}\n{date}\n{location}\n{description}'.format(
          title=event.get('summary'),
          date=event.get('dtstamp').dt,
          location=event.get('location'),
          description=event.get('description'))


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I don't understand that command.")


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def read_ical(url):
    with urlopen(CALENDAR_URL) as f:
        ical = Calendar.from_ical(f.read())
        for component in ical.walk():
            if component.name == 'VEVENT':
                yield component


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
