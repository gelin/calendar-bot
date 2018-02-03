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
from html.parser import HTMLParser


def normalize_locale(language):
    """
    Normalized name of the locale.
    Always returns UTF-8 encoding for normalized locales.
    :param language: a language name, for example 'it' or 'italian'
    :return: locale name, like 'it_IT.UTF-8'
    """
    normalized_locale = locale.normalize(language)
    utf8_locale = normalized_locale.rpartition('.')[0] + '.UTF-8'
    return utf8_locale


def format_event(user_config, event):
    """
    Formats the event for notification
    :param user_config: UserConfig instance, contains format string and language
    :param event: Event instance
    :return: formatted string
    """
    event_dict = event.to_dict()
    event_dict['title'] = strip_tags(event_dict['title'])
    event_dict['location'] = strip_tags(event_dict['location'])
    event_dict['description'] = strip_tags(event_dict['description'])
    locale.setlocale(locale.LC_ALL, user_config.language)       # assuming formatting will never be concurrently
    result = user_config.format.format(**event_dict)
    locale.resetlocale()
    return result


class BlankFormat:
    """
    A special class which is always formatted as empty string
    """

    def __format__(self, format_spec):
        return ''

    def __str__(self):
        return ''


# https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python

class MLStripper(HTMLParser):

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.href = attr[1]
        elif tag == 'br':
            self.fed.append('\n')

    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.fed.append(' (')
            self.fed.append(self.href)
            self.fed.append(')')
            self.href = None

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(str(html))
    return s.get_data()
