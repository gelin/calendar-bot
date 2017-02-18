#!/usr/bin/python3
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
import os
import sys

from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

from calbot.bot import run_bot
from calbot.conf import Config


def main():
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    else:
        configfile = os.path.join(os.path.dirname(__file__), 'calbot.cfg')
    config = Config(configfile)
    run_bot(config)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    setup_logging(SentryHandler(level=logging.WARNING))
    main()
