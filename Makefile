.PHONY: help
help:
	@echo "make run | deploy"

.PHONY: run
run:
	./calbot.py

.PHONY: deploy
deploy:
	cd ansible && ansible-playbook deploy.yml
