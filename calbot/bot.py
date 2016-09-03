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
from .ical import Calendar, sample_event


GREETING = '''Hello, I'm calendar bot, please give me some commands.
/add ical_url @channel — to add new iCal to be sent to a channel
/list — to see all configured calendars
/del id — remove calendar by id
/format [new format] — get or set a calendar event formatting, use {title}, {date}, {time}, {location} and {description} variables
/lang [language] — get or set language to print the event, may affect the week day name
/advance [hours...] — get or set calendar events advance, i.e. how many hours before the event to publish it
'''


__all__ = ['run_bot']


logger = logging.getLogger('bot')


def run_bot(config):
    """
    Starts the bot
    :param config: main bot configuration
    :return: None
    """
    updater = Updater(config.token)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', start))

    def add_calendar_to_config(bot, update, args, job_queue):
        add_calendar(bot, update, args, job_queue, config)
    dispatcher.add_handler(CommandHandler('add', add_calendar_to_config,
                                          allow_edited=True, pass_args=True, pass_job_queue=True))

    def list_calendars_from_config(bot, update):
        list_calendars(bot, update, config)
    dispatcher.add_handler(CommandHandler('list', list_calendars_from_config,
                                          allow_edited=True))

    def delete_calendar_from_config(bot, update, args, job_queue):
        delete_calendar(bot, update, args, job_queue, config)
    dispatcher.add_handler(CommandHandler('del', delete_calendar_from_config,
                                          allow_edited=True, pass_args=True, pass_job_queue=True))

    def get_set_format_with_config(bot, update):
        get_set_format(bot, update, config)
    dispatcher.add_handler(CommandHandler('format', get_set_format_with_config,
                                          allow_edited=True))

    dispatcher.add_handler(MessageHandler([Filters.command], unknown))

    dispatcher.add_error_handler(error)

    if config.webhook:
        webhook_url = 'https://%s/%s' % (config.domain, config.token)
        updater.start_webhook(listen=config.listen, port=config.port,
                              url_path=config.token, webhook_url=webhook_url)
        logger.info('started webhook on %s:%s' % (config.listen, config.port))
        updater.bot.set_webhook(webhook_url)
        logger.info('set webhook to %s' % webhook_url)
    else:
        updater.start_polling(clean=True)
        logger.info('started polling')

    start_delay = 0
    for calendar in config.all_calendars():
        queue_calendar_update(updater.job_queue, calendar, start_delay)
        start_delay += 1

    updater.idle()


def queue_calendar_update(job_queue, calendar, start_delay=0):
    """
    Adds the configured calendar to queue for processing
    :param job_queue: bot's job queue
    :param calendar: CalendarConfig instance
    :param start_delay: delay start of immediate calendar processing for specified number of seconds
    :return: None
    """
    job = Job(update_calendar, calendar.interval, repeat=True, context=calendar)
    job_queue.put(job, next_t=start_delay)


def start(bot, update):
    """
    /start or /help command handler. Prints greeting message.
    :param bot: Bot instance
    :param update: Update instance
    :return: None
    """
    logger.info('started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text=GREETING)


def add_calendar(bot, update, args, job_queue, config):
    """
    /add command handler.
    Adds url and channel_id of the new calendar to config and to the queue to be immediately processed.
    :param bot: Bot instance
    :param update: Update instance
    :param args: command arguments: url and channel_id
    :param job_queue: JobQueue instance to add calendar update job
    :param config: Config instance to persist calendar
    :return: None
    """
    message = update.message or update.edited_message
    user_id = str(message.chat_id)
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


def list_calendars(bot, update, config):
    """
    /list command handler. Prints the list of all calendars configured for the user.
    :param bot: Bot instance
    :param update: Update instance
    :param config: Config instance to read list of user's calendars
    :return: None
    """
    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    text = 'ID\tNAME\tCHANNEL\n'        # TODO: HTML formatting?
    for calendar in config.user_calendars(user_id):
        text += '%s\t%s\t%s\n' % (calendar.id, calendar.name, calendar.channel_id)
    bot.sendMessage(chat_id=user_id, text=text)


def delete_calendar(bot, update, args, job_queue, config):
    """
    /del command handler.
    Removes the calendar from the persisted config and from job queue by it's id.
    :param bot: Bot instance
    :param update: Update instance
    :param args: command arguments: url and channel_id
    :param job_queue: JobQueue instance to add calendar update job
    :param config: Config instance to persist calendar
    :return: None
    """
    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    if len(args) < 1:
        bot.sendMessage(chat_id=user_id,
                        text="Please provide the calendar id to /del command:\n/del calendar_id")
        return

    for calendar_id in args:
        try:
            config.delete_calendar(user_id, calendar_id)
            for job in job_queue.jobs():
                if job.context.id == calendar_id:
                    job.schedule_removal()
            bot.sendMessage(chat_id=user_id,
                            text="Calendar %s is deleted" % calendar_id)
        except Exception as e:
            logger.warning('Failed to delete calendar %s for user %s', calendar_id, user_id, exc_info=True)
            bot.sendMessage(chat_id=user_id,
                            text='Failed to delete calendar %s:\n%s' % (calendar_id, e))


def get_set_format(bot, update, config):
    """
    /format command handler.
    Prints the current format or sets the new format for the calendar event.
    :param bot: Bot instance
    :param update: Update instance
    :param config: Config instance
    :return: None
    """
    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    parts = message.text.split(' ', maxsplit=1)
    if len(parts) < 2:
        print_format(bot, user_id, config)
    else:
        new_format = parts[1]
        set_format(bot, user_id, new_format, config)


def print_format(bot, user_id, config):
    """
    Prints the current format
    :param bot: Bot instance
    :param user_id: ID of the user
    :param config: Config instance
    :return: None
    """
    user_config = config.load_user(user_id)
    format = user_config.format
    text = 'Current format:\n%s\nSample event:\n%s' % (     # TODO: HTML formatting?
        format,
        format_event(format, sample_event)
    )
    bot.sendMessage(chat_id=user_id, text=text)


def set_format(bot, user_id, format, config):
    """
    Saves the new format for the user
    :param bot: Bot instance
    :param user_id: ID of the user
    :param format: new format
    :param config: Config instance
    :return: None
    """
    # TODO


def unknown(bot, update):
    """
    Handler for unknown command. Prints error message.
    :param bot: Bot instance
    :param update: Update instance
    :return: None
    """
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I don't understand that command.")


def error(bot, update, error):
    """
    Error handler. Prints error message.
    :param bot: Bot instance
    :param update: Update instance
    :param error: the error
    :return: None
    """
    logger.warning('Update "%s" caused error "%s"' % (update, error))


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
            send_event(bot, config.channel_id, event, config.format)
            config.event_notified(event)
        config.save_events()
        if not config.verified:
            bot.sendMessage(chat_id=config.channel_id,
                            text='Events from %s will be notified here' % calendar.name)
            config.save_calendar(calendar)
            bot.sendMessage(chat_id=config.user_id,
                            text='Added:\n%s\t%s\t%s' % (config.id, config.name, config.channel_id))
    except Exception as e:
        logger.warning('Failed to process calendar %s of user %s', config.id, config.user_id, exc_info=True)
        if not config.verified:
            bot.sendMessage(chat_id=config.user_id,
                            text='Failed to process calendar %s:\n%s' % (config.id, e))


def send_event(bot, channel_id, event, format):
    """
    Sends the event notification to the channel
    :param bot: Bot instance
    :param channel_id: channel_id where to notify
    :param event: Event instance, read from ical
    :param format: format string
    :return: None
    """
    bot.sendMessage(chat_id=channel_id, text=format_event(format, event))


def format_event(format, event):
    """
    Formats the event for notification
    :param format: format string
    :param event: Event instance
    :return: formatted string
    """
    return format.format(**event.to_dict())
