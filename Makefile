PYTHON ?= python3
NODE ?= node

.PHONY: test
test:
	$(PYTHON) -B -m unittest discover -s tests/skill
	$(PYTHON) -B -m unittest discover -s tests/hermes
	$(PYTHON) -B -m unittest discover -s integrations/osint-map
	$(NODE) --experimental-vm-modules --test tests/hermes/desktop.test.mjs
