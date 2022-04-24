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

from calbot.formatting import format_event
from calbot.ical import sample_event


__all__ = ['create_handler']

logger = logging.getLogger('commands.format')

SETTING = 0
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /format command.
    :return: ConversationHandler
    """

    def get_format_with_config(bot, update):
        return get_format(bot, update, config)

    def set_format_with_config(bot, update):
        return set_format(bot, update, config)

    def cancel_with_config(bot, update):
        return cancel(bot, update, config)

    return ConversationHandler(
        entry_points=[CommandHandler('format', get_format_with_config)],
        states={
            SETTING: [MessageHandler(Filters.text, set_format_with_config)],
        },
        fallbacks=[CommandHandler('cancel', cancel_with_config)],
        allow_reentry=True
    )


def get_format(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        message.reply_text('Current format:')
        message.reply_text(user_config.format)
        message.reply_text('Sample event:')
        message.reply_text(format_event(user_config, sample_event))
        message.reply_text('Type a new format string to set or /cancel')
        return SETTING
    except Exception:
        logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return END


def set_format(bot, update, config):
    message = update.message or update.edited_message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        new_format = message.text.strip()
        user_config.set_format(new_format)
        message.reply_text('Format is updated.\nSample event:')
        message.reply_text(format_event(user_config, sample_event))
        return END
    except Exception as e:
        logger.warning('Failed to update format for user %s', user_id, exc_info=True)
        try:
            message.reply_text('Failed to update format:\n%s' % e)
            message.reply_text('Try again or /cancel')
        except Exception:
            logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return SETTING


def cancel(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        message.reply_text('Cancelled.\nCurrent format:')
        message.reply_text(user_config.format)
    except Exception:
        logger.error('Failed to send reply to user %s', user_id, exc_info=True)
    return END
