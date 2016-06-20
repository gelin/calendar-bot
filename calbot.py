#!/usr/bin/python3


import logging
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters


TOKEN = '225478221:AAFvpu4aBjixXmDJKAWVO3wNMjWFpxlkcHY'
CHAT_ID = '@gelintestchannel'


def main():
    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    relay_handler = MessageHandler([Filters.text], relay)
    dispatcher.add_handler(relay_handler)
    unknown_handler = MessageHandler([Filters.command], unknown)
    dispatcher.add_handler(unknown_handler)
    updater.start_polling()
    updater.idle()


def start(bot, update):
    logging.log(logging.INFO, 'started from %s', update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="I'm a test bot, please talk to me!")


def relay(bot, update):
    bot.sendMessage(chat_id=CHAT_ID, text=update.message.text)


def unknown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()
