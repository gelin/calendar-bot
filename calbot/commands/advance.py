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


__all__ = ['create_handler']

logger = logging.getLogger('commands.advance')

SETTING = 0
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /advance command.
    :return: ConversationHandler
    """

    def get_advance_with_config(bot, update):
        return get_advance(bot, update, config)

    def set_advance_with_config(bot, update):
        return set_advance(bot, update, config)

    def cancel_with_config(bot, update):
        return cancel(bot, update, config)

    return ConversationHandler(
        entry_points=[CommandHandler('advance', get_advance_with_config)],
        states={
            SETTING: [MessageHandler(Filters.text, set_advance_with_config)],
        },
        fallbacks=[CommandHandler('cancel', cancel_with_config)],
        allow_reentry=True
    )


def get_advance(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)

    text = 'Events are notified %s hours in advance.\nType another numbers to change or /cancel\n' % (
        ', '.join(map(str, user_config.advance)),
    )
    message.reply_text(text)
    return SETTING


def set_advance(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)

    hours = message.text.strip()
    try:
        hours = message.text.split()
        user_config.set_advance(hours)
        text = 'Advance hours are updated.\nEvents will be notified %s hours in advance.' % (
            ', '.join(map(str, user_config.advance)),
        )
        message.reply_text(text)
        return END
    except Exception as e:
        logger.warning('Failed to update advance to "%s" for user %s', str(hours), user_id, exc_info=True)
        text = 'Failed to update advance hours:\n%s' % e
        try:
            message.reply_text(text)
            message.reply_text('Try again or /cancel')
        except Exception:
            logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return SETTING


def cancel(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    user_config = config.load_user(user_id)

    text = 'Cancelled.\nEvents will be notified %s hours in advance.' % (
        ', '.join(map(str, user_config.advance)),
    )
    message.reply_text(text)
    return END
