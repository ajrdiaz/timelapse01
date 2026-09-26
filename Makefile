PY ?= python3

.PHONY: dev install test render draft build clean

install:
	$(PY) -m pip install -r requirements.txt
	cd frontend && npm install

dev:
	./run.sh

test:
	$(PY) -m pytest -q

render:
	$(PY) -m engine.render examples/bunker_gamer.json --cover

draft:
	$(PY) -m engine.render examples/bunker_gamer.json --draft

build:
	cd frontend && npm run build

clean:
	rm -rf .cache output frontend/dist
