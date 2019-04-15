.PHONY: help
help:
	@echo "make run | deploy"

.PHONY: build
build:
	cd calbot && $(MAKE) build 

.PHONY: run
run:
	cd calbot && $(MAKE) run

.PHONY: install
install:
	pip3 install -r requirements.txt

.PHONY: test
test:
	python3 -m unittest calbot_test.py

.PHONY: deploy
deploy:
	cd ansible && ansible-playbook deploy.yml

.PHONY: docker
docker:
	docker run -it -v "$$PWD:/calbot" python:3.4.2 /bin/bash 
