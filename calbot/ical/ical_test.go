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
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func TestReadIcalSimple(t *testing.T) {
	timezone, _ := time.LoadLocation("Asia/Omsk")
	from := time.Date(2016, time.January, 1, 0, 0, 0, 0, timezone)
	till := time.Date(2017, time.January, 5, 23, 59, 59, 0, timezone)

	events, err := ReadIcal("testdata/simple.ics", from, till)

	if err != nil {
		t.Error(err)
	}

	assert.ElementsMatch(t, events,
		[]Event{
			{
				Time:        time.Date(2016, 6, 24, 0, 0, 0, 0, time.UTC), // TODO: calendar timezone
				Title:       "Событие по-русски",
				Description: "Какое-то описание\\nВ две строки", // TODO: newline
			},
			{
				Time:        time.Date(2016, 6, 23, 0, 0, 0, 0, time.UTC),
				Title:       "Event title",
				Description: "Event description",
			},
			{
				Time:  time.Date(2017, 1, 4, 10, 0, 0, 0, timezone),
				Title: "Daily event",
			},
			{
				Time:  time.Date(2017, 1, 5, 10, 0, 0, 0, timezone),
				Title: "Daily event",
			},
		})
}
