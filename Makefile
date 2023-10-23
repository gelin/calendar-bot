.PHONY: help
help:
	@echo "make run | deploy"

.PHONY: install
install:
	python -m pip install --upgrade pip
	python -m pip install setuptools
	python -m pip install -r requirements.txt

.PHONY: run
run:
	python calbot.py

.PHONY: test
test:
	python -m unittest calbot_test.py

.PHONY: deploy
deploy:
	cd ansible && ansible-playbook deploy.yml

.PHONY: docker
docker:
	docker run -it -v "$$PWD:/calbot" python:3.4.2 /bin/bash 
