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
from telegram.ext import RegexHandler

from calbot.conf import CalendarConfig


__all__ = ['create_handler']

logger = logging.getLogger('commands.cal')

EDITING = 0
END = ConversationHandler.END


def create_handler(config):
    """
    Creates handler for /calX command.
    :return: ConversationHandler
    """

    def get_cal_with_config(bot, update, groups, chat_data):
        return get_cal(bot, update, groups, chat_data, config)

    def del_cal_with_config(bot, update, chat_data, job_queue):
        return del_cal(bot, update, chat_data, job_queue, config)

    def enable_cal_with_config(bot, update, chat_data):
        return enable_cal(bot, update, chat_data, config)

    def disable_cal_with_config(bot, update, chat_data):
        return disable_cal(bot, update, chat_data, config)

    return ConversationHandler(
        entry_points=[RegexHandler(r'^/cal(\d+)', get_cal_with_config, pass_groups=True, pass_chat_data=True)],
        states={
            EDITING: [
                CommandHandler('enable', enable_cal_with_config, pass_chat_data=True),
                CommandHandler('disable', disable_cal_with_config, pass_chat_data=True),
                CommandHandler('delete', del_cal_with_config, pass_chat_data=True, pass_job_queue=True),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )


def get_cal(bot, update, groups, chat_data, config):
    message = update.message
    user_id = str(message.chat_id)
    calendar_id = groups[0]
    chat_data['calendar_id'] = calendar_id

    try:
        calendar = config.load_calendar(user_id, calendar_id)
        message.reply_text(
            '''Calendar %s details
Name: %s
URL: %s
Channel: %s
Verified: %s
Enabled: %s
Last processed: %s
Last error: %s
Errors count: %s''' % (calendar.id, calendar.name, calendar.url, calendar.channel_id,
                       calendar.verified, calendar.enabled,
                       calendar.last_process_at, calendar.last_process_error, calendar.last_errors_count))
        message.reply_text(('/disable' if calendar.enabled else '/enable') + ' /delete or /cancel')
        return EDITING
    except Exception as e:
        logger.warning('Failed to load calendar %s for user %s', calendar_id, user_id, exc_info=True)
        try:
            message.reply_text('Failed to find calendar %s:\n%s' % (calendar_id, e))
        except Exception:
            logger.error('Failed to send reply to user %s', user_id, exc_info=True)
        return END


def del_cal(bot, update, chat_data, job_queue, config):
    message = update.message
    user_id = str(message.chat_id)
    calendar_id = chat_data['calendar_id']

    try:
        config.delete_calendar(user_id, calendar_id)
        for job in job_queue.jobs():
            if (hasattr(job, 'context')
                    and isinstance(job.context, CalendarConfig)
                    and job.context.id == calendar_id):
                job.schedule_removal()
        message.reply_text('Calendar %s is deleted' % calendar_id)
    except Exception as e:
        logger.warning('Failed to delete calendar %s for user %s', calendar_id, user_id, exc_info=True)
        try:
            message.reply_text('Failed to delete calendar %s:\n%s' % (calendar_id, e))
        except Exception:
            logger.warning('Failed to send reply to user %s', user_id, exc_info=True)

    return END


def enable_cal(bot, update, chat_data, config):
    message = update.message
    user_id = str(message.chat_id)
    calendar_id = chat_data['calendar_id']

    try:
        config.enable_calendar(user_id, calendar_id, True)
        message.reply_text('Calendar /cal%s is enabled' % calendar_id)
    except Exception as e:
        logger.warning('Failed to enable calendar %s for user %s', calendar_id, user_id, exc_info=True)
        try:
            message.reply_text('Failed to enable calendar /cal%s:\n%s' % (calendar_id, e))
        except Exception:
            logger.warning('Failed to send reply to user %s', user_id, exc_info=True)

    return END


def disable_cal(bot, update, chat_data, config):
    message = update.message
    user_id = str(message.chat_id)
    calendar_id = chat_data['calendar_id']

    try:
        config.enable_calendar(user_id, calendar_id, False)
        message.reply_text('Calendar /cal%s is disabled' % calendar_id)
    except Exception as e:
        logger.warning('Failed to disable calendar %s for user %s', calendar_id, user_id, exc_info=True)
        try:
            message.reply_text('Failed to disable calendar /cal%s:\n%s' % (calendar_id, e))
        except Exception:
            logger.warning('Failed to send reply to user %s', user_id, exc_info=True)

    return END


def cancel(bot, update):
    message = update.message
    message.reply_text('Cancelled.')
    return END
