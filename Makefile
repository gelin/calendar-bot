.PHONY: help
help:
	@echo "make run | deploy"

.PHONY: install
install:
	pip3 install -r requirements.txt

.PHONY: run
run:
	./calbot.py

.PHONY: test
test:
	python3 -m unittest calbot_test.py

.PHONY: deploy
deploy:
	cd ansible && ansible-playbook deploy.yml

.PHONY: copy
copy:
	rsync -axzv ./ rbx1-fr.quadhost.net:calbot/

.PHONY: docker
docker:
	docker run -it -v "$$PWD:/calbot" python:3.4.2 /bin/bash 
