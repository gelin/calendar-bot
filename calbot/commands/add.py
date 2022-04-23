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

from telegram.ext import ConversationHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

from calbot.processing import update_calendar

__all__ = ['create_handler']

logger = logging.getLogger('commands.add')

ENTERING_URL = 0
ENTERING_CHANNEL = 1
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /add command.
    :return: ConversationHandler
    """

    def add_calendar_with_config(bot, update, chat_data):
        return add_calendar(bot, update, chat_data, config)

    return ConversationHandler(
        entry_points=[CommandHandler('add', start)],
        states={
            ENTERING_URL: [MessageHandler(Filters.text, enter_url, pass_chat_data=True)],
            ENTERING_CHANNEL: [MessageHandler(
                Filters.text, add_calendar_with_config, pass_chat_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

# TODO: add try-catch around all reply_text

def start(bot, update):
    message = update.message
    message.reply_text("You're going to add a new calendar.\nEnter an URL of iCal file or /cancel")
    return ENTERING_URL


def enter_url(bot, update, chat_data):
    message = update.message
    chat_data['calendar_url'] = message.text.strip()
    message.reply_text('Enter a channel name or /cancel')
    return ENTERING_CHANNEL


def add_calendar(bot, update, chat_data, config):
    message = update.message
    user_id = str(message.chat_id)
    url = chat_data['calendar_url']
    channel_id = message.text.strip()

    calendar = config.add_calendar(user_id, url, channel_id)

    message.reply_text(
        'The new calendar is queued for verification.\nWait for messages here and in the %s.' % channel_id)

    update_calendar(bot, calendar)

    return END


def cancel(bot, update):
    message = update.message
    message.reply_text('Cancelled.')
    return END
