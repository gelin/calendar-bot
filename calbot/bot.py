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

from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from calbot import stats
from calbot.commands import add as add_command
from calbot.commands import cal as cal_command
from calbot.commands import format as format_command
from calbot.commands import lang as lang_command
from calbot.commands import advance as advance_command
from calbot.processing import update_calendars


__all__ = ['run_bot']

GREETING = '''Hello, I'm calendar bot, please give me some commands.
/add — add new iCal to be sent to a channel
/list — see all configured calendars
/format — get and set a calendar event formatting, use {title}, {date}, {time}, {location} and {description} variables
/lang — get and set language to print the event, may affect the week day name
/advance — get and set calendar events advance, i.e. how many hours before the event to publish it
'''

# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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

    dispatcher.add_handler(add_command.create_handler(config))

    def list_calendars_from_config(bot, update):
        list_calendars(bot, update, config)
    dispatcher.add_handler(CommandHandler('list', list_calendars_from_config))

    dispatcher.add_handler(cal_command.create_handler(config))
    dispatcher.add_handler(format_command.create_handler(config))
    dispatcher.add_handler(lang_command.create_handler(config))
    dispatcher.add_handler(advance_command.create_handler(config))

    def get_stats_with_config(bot, update):
        get_stats(bot, update, config)
    dispatcher.add_handler(CommandHandler('stats', get_stats_with_config))

    dispatcher.add_handler(CommandHandler('cancel', cancel))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))

    dispatcher.add_error_handler(error)

    if config.webhook:
        webhook_url = 'https://%s/%s' % (config.domain, config.token)
        updater.start_webhook(listen=config.listen,
                              port=config.port,
                              url_path=config.token,
                              webhook_url=webhook_url,
                              bootstrap_retries=config.bootstrap_retries)
        logger.info('Started webhook on %s:%s' % (config.listen, config.port))
        updater.bot.set_webhook(webhook_url)
        logger.info('Set webhook to %s' % webhook_url)
    else:
        updater.start_polling(clean=False,
                              poll_interval=config.poll_interval,
                              timeout=config.timeout,
                              read_latency=config.read_latency,
                              bootstrap_retries=config.bootstrap_retries,
                              )
        logger.info('Started polling')

    updater.job_queue.run_repeating(update_calendars, config.interval, first=0, context=config)

    updater.idle()


def start(bot, update):
    """
    /start or /help command handler. Prints greeting message.
    :param bot: Bot instance
    :param update: Update instance
    :return: None
    """
    logger.info('Started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text=GREETING)


def list_calendars(bot, update, config):
    """
    /list command handler. Prints the list of all calendars configured for the user.
    :param bot: Bot instance
    :param update: Update instance
    :param config: Config instance to read list of user's calendars
    :return: None
    """
    message = update.message
    user_id = str(message.chat_id)
    text = 'ID\tNAME\tCHANNEL\n'
    for calendar in config.user_calendars(user_id):
        text += '/cal%s\t%s\t%s\n' % (calendar.id, calendar.name, calendar.channel_id)
    bot.sendMessage(chat_id=user_id, text=text)


def get_stats(bot, update, config):
    """
    /stats command handler.
    Prints the current known statistics.
    :param bot: Bot instance
    :param update: Update instance
    :param config: Config instance
    :return: None
    """
    message = update.message
    text = str(stats.get_stats(config))
    bot.sendMessage(chat_id=message.chat_id, text=text)


def cancel(bot, update):
    """
    Handler for /cancel command. Prints error message.
    :param bot: Bot instance
    :param update: Update instance
    :return: None
    """
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, there's nothing to cancel.")


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
