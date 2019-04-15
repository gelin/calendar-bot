NAME=calbot
#VERSION=$(shell git rev-list --count HEAD)
#BUILD=$(shell git rev-parse --short HEAD)
#LD_FLAGS="-w -X main.version=$(VERSION) -X main.build=$(BUILD)"

.PHONY: all
all: clean build

.PHONY: clean
clean:
	rm -rf build/*

.PHONY: build
build:
#	go build -ldflags $(LD_FLAGS) -o build/$(NAME)
	go build -o build/$(NAME)

.PHONY: run
run: clean build
	build/$(NAME)

.PHONY: update
update:
	go get -u

.PHONY: install
install: update
	go install


