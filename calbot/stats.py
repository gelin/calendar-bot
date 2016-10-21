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

import os
from configparser import ConfigParser

from calbot.conf import ConfigFile

__all__ = ['update_stats', 'get_stats']


STATS_MESSAGE_FORMAT="""Active users: {}
Active calendars: {}
Notified events: {}"""


def update_stats(config):
    """
    Updates statistics.
    :param config: Main config object
    :return: None
    """
    config_file = StatsConfigFile(config.vardir)
    parser = ConfigParser(interpolation=None)
    parser.add_section('stats')

    users = 0
    calendars = 0
    events = 0

    for name in os.listdir(config.vardir):
        if os.path.isdir(os.path.join(config.vardir, name)):
            users += 1
            user_id = name
            for calendar in config.load_calendars(user_id):
                calendars += 1
                calendar.load_events()
                events += len(calendar.events)

    parser.set('stats', 'users', str(users))
    parser.set('stats', 'calendars', str(calendars))
    parser.set('stats', 'events', str(events))

    config_file.write(parser)


def get_stats(config):
    """
    Reads stats object from the stats.cfg file
    :param config: Main Config object
    :return: Stats object
    """
    config_file = StatsConfigFile(config.vardir)
    return Stats.load(config_file)


class Stats:
    """
    Holds statistics data.
    """

    def __init__(self, **kwargs):
        self.users = kwargs['users']
        """Number of active users"""
        self.calendars = kwargs['calendars']
        """Number of active calendar"""
        self.events = kwargs['events']
        """Number of notified events"""

    @classmethod
    def load(cls, stats_config):
        """
        Loads stats from the stats.cfg file
        """
        parser = stats_config.read_parser()
        return cls(
            users=parser.getint('stats', 'users', fallback=0),
            calendars=parser.getint('stats', 'calendars', fallback=0),
            events=parser.getint('stats', 'events', fallback=0),
        )

    def __str__(self):
        return STATS_MESSAGE_FORMAT.format(self.users, self.calendars, self.events)


class StatsConfigFile(ConfigFile):
    """
    Reads and writes stats config file.
    """

    def __init__(self, vardir):
        """
        Creates the config
        :param vardir: basic var dir
        """
        super().__init__(os.path.join(vardir, 'stats.cfg'))
