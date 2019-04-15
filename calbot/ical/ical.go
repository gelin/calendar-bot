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

import "time"

type Event struct {
	Time        time.Time
	Title       string
	Description string
}

// Reads .ical file from the provided URL.
// Returns all events in the specified interval (after inclusive and before exclusive)
// including the repeating events.
func ReadIcal(url string, after time.Time, before time.Time) (events []Event, err error) {
	events = make([]Event, 0)
	err = nil

	return
}
