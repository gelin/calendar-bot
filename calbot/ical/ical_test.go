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
	"testing"
	"time"
)

func TestReadIcal(t *testing.T) {
	timezone, _ := time.LoadLocation("Asia/Omsk")
	from := time.Date(2016, time.January, 1, 0, 0, 0, 0, timezone)
	till := time.Date(2017, time.December, 31, 23, 59, 59, 0, timezone)

	events, err := ReadIcal("file://./testdata/test.ics", from, till)

	if err != nil {
		t.Error(err)
	}
	println(events)
}
