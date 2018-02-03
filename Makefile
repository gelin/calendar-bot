.PHONY: help
help:
	@echo "make run | deploy"

.PHONY: install
install:
	pip3 install -r requirements.txt

.PHONY: run
run:
	./calbot.py

.PHONY: deploy
deploy:
	cd ansible && ansible-playbook deploy.yml
