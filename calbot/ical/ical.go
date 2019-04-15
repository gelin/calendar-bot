/*
 * Copyright 2019 Denis Nelubin.
 *
 * This file is part of Calendar Bot.
 *
 * Calendar Bot is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Calendar Bot is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Calendar Bot.  If not, see http://www.gnu.org/licenses/.
 */

package ical

import (
	"github.com/apognu/gocal"
	"github.com/utahta/go-openuri"
	"io"
	"time"
)

type Event struct {
	Time        time.Time
	Title       string
	Description string
}

// Reads .ical file from the provided URL.
// Returns all events in the specified interval
// including the repeating events.
func ReadIcal(url string, after time.Time, before time.Time) (events []Event, err error) {
	reader, err := readUrl(url)
	if err != nil {
		return
	}
	defer reader.Close()

	parser := gocal.NewParser(reader)
	parser.Start, parser.End = &after, &before
	err = parser.Parse()
	if err != nil {
		return
	}

	for _, vevent := range parser.Events {
		event := Event{
			Time:        *vevent.Start,
			Title:       vevent.Summary,
			Description: vevent.Description,
		}
		events = append(events, event)
	}

	return
}

func readUrl(url string) (reader io.ReadCloser, err error) {
	reader, err = openuri.Open(url)
	return
}
