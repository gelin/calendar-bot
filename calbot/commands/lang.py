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

import locale
import logging

from telegram.ext import ConversationHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

from calbot.formatting import normalize_locale, format_event
from calbot.ical import sample_event


__all__ = ['create_handler']

logger = logging.getLogger('commands.lang')

SETTING = 0
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /lang command.
    :return: ConversationHandler
    """

    def get_lang_with_config(bot, update):
        return get_lang(bot, update, config)

    def set_lang_with_config(bot, update):
        return set_lang(bot, update, config)

    def cancel_with_config(bot, update):
        return cancel(bot, update, config)

    return ConversationHandler(
        entry_points=[CommandHandler('lang', get_lang_with_config)],
        states={
            SETTING: [MessageHandler(Filters.text, set_lang_with_config)],
        },
        fallbacks=[CommandHandler('cancel', cancel_with_config)],
        allow_reentry=True
    )


def get_lang(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        message.reply_text('Current language is %s\nSample event:' % user_config.language)
        message.reply_text(format_event(user_config, sample_event))
        message.reply_text('Type another language name to set or /cancel')
        return SETTING
    except Exception:
        logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return END


def set_lang(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        new_lang = message.text.strip()
        old_lang = user_config.language
        normalized_locale = normalize_locale(new_lang)
        user_config.set_language(normalized_locale)
        try:
            sample = format_event(user_config, sample_event)
            message.reply_text('Language is updated to %s\nSample event:' % normalized_locale)
            message.reply_text(sample)
            return END
        except locale.Error as e:
            if old_lang:
                user_config.set_language(old_lang)
            logger.warning('Unsupported language "%s" for user %s', new_lang, user_id, exc_info=True)
            message.reply_text('Unsupported language:\n%s' % e)
            message.reply_text('Try again or /cancel')
            return SETTING
    except Exception as e:
        logger.warning('Failed to update language for user %s', user_id, exc_info=True)
        try:
            message.reply_text('Failed to update language:\n%s' % e)
            message.reply_text('Try again or /cancel')
        except Exception:
            logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return SETTING


def cancel(bot, update, config):
    message = update.message
    user_id = str(message.chat_id)
    try:
        user_config = config.load_user(user_id)
        text = 'Cancelled.\nCurrent language is %s' % user_config.language
        message.reply_text(text)
    except Exception:
        logger.error('Failed to send reply to user %s', user_id, exc_info=True)
    return END
