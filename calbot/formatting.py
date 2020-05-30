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
import re
from html.parser import HTMLParser

# https://gist.github.com/gruber/8891611
url_regex = re.compile(r'''(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|link|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|link|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))''')


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
    return result.strip()


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
        super().__init__(convert_charrefs=True)
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []
        self.href = None
        self.text = []
        self.list_level = -1
        self.block_start = False
        self.block_end = False

    def handle_starttag(self, tag, attrs):
        self.text = []
        self.block_end = False
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.href = attr[1]
        elif tag == 'br':
            self.fed.append('\n')
        elif tag == 'p':
            if not self.block_start:
                self.fed.append('\n')
            self.block_start = True
        elif tag in ('ul', 'ol'):
            if not self.block_start and self.list_level <= 0:
                self.fed.append('\n')
            self.list_level = self.list_level + 1
            self.block_start = True
        elif tag == 'li':
            self.fed.append('  ' * self.list_level)
            self.fed.append('* ')
            self.block_start = True

    def handle_endtag(self, tag):
        self.block_start = False
        if tag == 'a' and self.href is not None:
            if url_regex.fullmatch(''.join(self.text)) is None:
                self.fed.append(' (')
                self.fed.append(self.href)
                self.fed.append(')')
            self.href = None
            self.block_end = False
        elif tag == 'p':
            if not self.block_end:
                self.fed.append('\n')
            self.block_end = True
        elif tag in ('ul', 'ol'):
            if not self.block_end or self.list_level <= 0:
                self.fed.append('\n')
            self.list_level = self.list_level - 1
            self.block_end = True
        elif tag == 'li':
            if not self.block_end:
                self.fed.append('\n')
            self.block_end = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)
        self.fed.append(d)
        self.block_start = False
        self.block_end = False

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed('<div>')     # <div> is required for Python 3.4.2, otherwise parser does nothing
    s.feed(str(html))
    s.feed('</div>')
    return s.get_data()
