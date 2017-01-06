# Calendar Bot

It's the bot for [Telegram](https://telegram.org/).

It reads [iCalendar](https://en.wikipedia.org/wiki/ICalendar) file of a Google Calendars.
And sends notifications to a [telegram channel](https://telegram.org/faq_channels) some hours in advance to the events in the calendar.
Use it to mirror calendar events to the channel and notify the subscribers.

## Quick Start

1. Start talk with [@icalbot](https://telegram.me/icalbot).
2. Invite @icalbot to your channel and make it the [channel administrator](https://telegram.org/faq_channels#q-what-can-administrators-do) (to allow it to post messages to the channel).
3. Find the URL of your iCalendar file ([ICAL link](https://support.google.com/calendar/answer/37083?hl=en#link)).
4. Type `/add https://your_calendar.ics @your_channel` (setting your actual data) in the chat with the bot.
5. Wait for bot notifications in the chat and in the channel.

## Bot Commands

### /add

`/add ical_url @channel` — add new iCal to be sent to a channel

Adds the new calendar to be processed by the bot and be broadcasted to the channel.

Takes two parameters:

* `ical_url` — URL of the iCalendar file. Can look like `https://calendar.google.com/calendar/ical/many_many_characters/public/basic.ics`
* `@channel` — name of the channel where to broadcast calendar events, starts from `@`

### /list

`/list` — see all configured calendars

Prints a table with calendar ID, calendar name and the broadcast channel with all calendars you configured with the bot.
For example:

```
ID NAME CHANNEL
1 My Google Calendar @mychannel
2 Another Calendar @anotherchannel
```

### /del

`/del id` — remove calendar by id

Deletes the calendar from the list of the configured calendars.

Takes one parameter:

* `id` — numeric ID of the calendar, the first column in the table printed by the `/list` command

### /format

`/format [new format]` — get or set a calendar event formatting, use {title}, {date}, {time}, {location} and {description} variables

Without arguments prints the current format of the calendar event.
For example:

```
Current format:
{title}
{date:%A, %d %B %Y}{time:, %H:%M %Z}
{location}
{description}
Sample event:
This is sample event
Friday, 09 September 2016, 14:43 UTC
It happens in the Milky Way
The sample event is to demonstrate how the event can be formatted
```

With the text passed after the command name sets this text as the new event format.
See below the details of the formatting.
 
### /lang 

`/lang` — get and set language to print the event, may affect the weekday / month name

The command prints the current language and asks the new language to set.
For example:

```
Current language: ru_RU.UTF-8
Sample event:
This is sample event
Пятница, 23 Сентябрь 2016, 18:03 UTC
It happens in the Milky Way
The sample event is to demonstrate how the event can be formatted

Type another language name to set or /cancel
```

Enter the language name to set the new language.
The language can be two letter code ('ru') or the full name ('russian').
Not all languages are supported by the bot.

### /advance

`/advance` — get and set calendar events advance, i.e. how many hours before the event to publish it

The bot broadcasts the event from the calendar to the channel some hours in advance before the event starts.
How many hours in advance to notify can be configured by this command.
It's possible to define multiple advance hours, in this case the same event will be notified multiple times.

The command prints the current advance hours and asks new values to update.
For example:

```
Events are notified 48, 24 hours in advance.
Type another numbers to change or /cancel
```

Enter one or more space separated integer numbers to set the new notification advance.
Each number means hours to advance.

## Event Formatting

Event has some properties.
To print the property during the event broadcasting you should include the property name to the format string in curly braces.
The format string can be modified using `/format` command (see above).
It uses the syntax of Python's [str.format()](https://docs.python.org/3/library/string.html#formatstrings) method.
Date and time are formatted according to [strftime()](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) rules. 
 
Event properties:

* `title` — event one-line title, use `{title}` in format string.
* `date` — day, month and year of the event start, you may define additional format parameters in braces, for example: `{date:%A, %d %B %Y}`.  
    Possible 'percent' parameters:
        
    * `%a` — weekday abbreviated name (depends on language)
    * `%A` — weekday full name (depends on language)
    * `%w` — weekday as decimal number
    * `%d` — day of the month as a zero-padded decimal number
    * `%b` — month abbreviated name (depends on language)
    * `%B` — month full name (depends on language)
    * `%m` — month as a zero-padded decimal number
    * `%y` — year without century as a zero-padded decimal number
    * `%Y` — year with century as a decimal number
    * `%j` — day of the year as a zero-padded decimal number
    * `%U` — week number of the year (Sunday as the first day of the week)
    * `%W` — week number of the year (Monday as the first day of the week)
    * `%x` — whole date representation (depends on language)
* `time` — hour, minute of the event start, you may define additional format parameters in braces, for example: `{time:%H:%M %Z}`.  
    Possible 'percent' parameters:
    
    * `%H` — hour (24-hour clock) as a zero-padded decimal number
    * `%I` — hour (12-hour clock) as a zero-padded decimal number
    * `%p` — AM or PM (depends on language)
    * `%M` — minute as a zero-padded decimal number
    * `%S` — second as a zero-padded decimal number
    * `%z` — UTC offset in the form +HHMM or -HHMM
    * `%Z` — time zone name
    * `%X` — whole time representation (depends on language)
* `location` — event location, as string, use `{location}` in format string.
* `description` — event description, can be multi-line, use `{description}` in format string.
