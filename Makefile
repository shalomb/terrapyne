DEBUG ?= 0
ifeq ($(DEBUG), 1)
    PYTESTFLAGS  =-rA
	VERBOSITY=5
else
    PYTESTFLAGS =""
	VERBOSITY=0
endif

.PHONY: init test

init:
	pip install -r requirements.txt

test:
	VERBOSE=$(VERBOSITY) py.test $(PYTESTFLAGS) -rA -vvvv tests/ \
		--log-format="%(asctime)s %(levelname)s %(message)s" \
		--log-date-format="%Y-%m-%d %H:%M:%S" \
		--show-capture=all

venv:
	python3 -mvenv venv/

requirements:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt
