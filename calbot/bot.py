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


import locale
import logging

from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import Job
from telegram.ext import MessageHandler
from telegram.ext import Updater

from calbot.formatting import normalize_locale, format_event
from calbot.ical import Calendar, sample_event


GREETING = '''Hello, I'm calendar bot, please give me some commands.
/add ical_url @channel — add new iCal to be sent to a channel
/list — see all configured calendars
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

    def get_set_lang_with_config(bot, update, args):
        get_set_lang(bot, update, args, config)
    dispatcher.add_handler(CommandHandler('lang', get_set_lang_with_config,
                                          allow_edited=True, pass_args=True))

    def get_set_advance_with_config(bot, update, args):
        get_set_advance(bot, update, args, config)
    dispatcher.add_handler(CommandHandler('advance', get_set_advance_with_config,
                                          allow_edited=True, pass_args=True))

    dispatcher.add_handler(MessageHandler([Filters.command], unknown))

    dispatcher.add_error_handler(error)

    if config.webhook:
        webhook_url = 'https://%s/%s' % (config.domain, config.token)
        updater.start_webhook(listen=config.listen,
                              port=config.port,
                              url_path=config.token,
                              webhook_url=webhook_url,
                              bootstrap_retries=config.bootstrap_retries)
        logger.info('started webhook on %s:%s' % (config.listen, config.port))
        updater.bot.set_webhook(webhook_url)
        logger.info('set webhook to %s' % webhook_url)
    else:
        updater.start_polling(clean=True,
                              poll_interval=config.poll_interval,
                              timeout=config.timeout,
                              network_delay=config.network_delay,
                              bootstrap_retries=config.bootstrap_retries,
                              )
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
    text = 'ID\tNAME\tCHANNEL\n'
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

    def print_format():
        text = 'Current format:\n%s\nSample event:\n%s' % (
            user_config.format,
            format_event(user_config, sample_event)
        )
        bot.sendMessage(chat_id=user_id, text=text)

    def set_format(format):
        try:
            user_config.set_format(format)
            text = 'Format is updated\nSample event:\n%s' % (
                format_event(user_config, sample_event)
            )
            bot.sendMessage(chat_id=user_id, text=text)
        except Exception as e:
            logger.warning('Failed to update format for user %s', user_id, exc_info=True)
            bot.sendMessage(chat_id=user_id,
                            text='Failed to update format:\n%s' % e)

    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)
    parts = message.text.split(' ', maxsplit=1)
    if len(parts) < 2:
        print_format()
    else:
        new_format = parts[1]
        set_format(new_format)


def get_set_lang(bot, update, args, config):
    """
    /lang command handler.
    Prints the current language or sets the new language to display the calendar event.
    :param bot: Bot instance
    :param update: Update instance
    :param args: Command arguments
    :param config: Config instance
    :return: None
    """

    def print_lang():
        text = 'Current language: %s\nSample event:\n%s' % (
            user_config.language,
            format_event(user_config, sample_event)
        )
        bot.sendMessage(chat_id=user_id, text=text)

    def set_lang(language):
        old_language = user_config.language
        try:
            normalized_locale = normalize_locale(language)
            user_config.set_language(normalized_locale)
            try:
                text = 'Language is updated to %s\nSample event:\n%s' % (
                    normalized_locale,
                    format_event(user_config, sample_event)
                )
                bot.sendMessage(chat_id=user_id, text=text)
            except locale.Error as e:
                user_config.set_language(old_language)
                logger.warning('Unsupported language "%s" for user %s', language, user_id, exc_info=True)
                bot.sendMessage(chat_id=user_id,
                                text='Unsupported language:\n%s' % e)
        except Exception as e:
            logger.warning('Failed to update language to "%s" for user %s', language, user_id, exc_info=True)
            bot.sendMessage(chat_id=user_id,
                            text='Failed to update language:\n%s' % e)

    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)
    if len(args) < 1:
        print_lang()
    else:
        new_lang = args[0]
        set_lang(new_lang)


def get_set_advance(bot, update, args, config):
    """
    /advance command handler.
    Prints the current advance hours or sets the new advance hours,
    to display the event before it starts with these hours in advance.
    :param bot: Bot instance
    :param update: Update instance
    :param args: Command arguments
    :param config: Config instance
    :return: None
    """

    def print_advance():
        text = 'Events are notified %s hours in advance' % (
            ', '.join(user_config.advance),
        )
        bot.sendMessage(chat_id=user_id, text=text)

    def set_advance(hours):
        try:
            user_config.set_advance(hours)
            text = 'Advance hours are updated.\nEvents will be notified %s hours in advance.' % (
                ', '.join(user_config.advance),
            )
            bot.sendMessage(chat_id=user_id, text=text)
        except Exception as e:
            logger.warning('Failed to update advance to "%s" for user %s', str(hours), user_id, exc_info=True)
            bot.sendMessage(chat_id=user_id,
                            text='Failed to update advance hours:\n%s' % e)

    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)
    if len(args) < 1:
        print_advance()
    else:
        set_advance(args)


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
