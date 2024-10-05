#!/usr/bin/make -f console

MAKEFILE          := $(realpath $(lastword $(MAKEFILE_LIST)))
MAKE              := make
MAKEFLAGS         += --no-print-directory
MAKEFLAGS         += --warn-undefined-variables

.ONESHELL:
SHELL             := /bin/bash
.SHELLFLAGS       := -o errexit -o nounset -o pipefail -u -ec

PATH              := $(PWD)/bin:$(PWD)/venv/bin:$(HOME)/go/bin:$(PATH)
PYTHONPATH        := $(PWD)/venv

APT_INSTALL       := sudo apt install -yyq --no-install-recommends --no-install-suggests

SYSTEM_PIP        := pip3
PYTHON            := $(PWD)/venv/bin/python3
PYTEST            := $(PWD)/venv/bin/pytest
COVERAGE          := $(PWD)/venv/bin/coverage
FLAKE8            := $(PWD)/venv/bin/flake8
BLACK             := $(PWD)/venv/bin/flake8
PIP3              := $(PWD)/venv/bin/pip3
YQ                := $(PWD)/venv/bin/yq -y
PIPREQS           := $(PWD)/venv/bin/pipreqs
BLACK             := $(PWD)/venv/bin/black

DEBUG ?= 0
ifeq ($(DEBUG), 1)
    PYTESTFLAGS  =-rA
	VERBOSITY=5
else
    PYTESTFLAGS =""
	VERBOSITY=0
endif

.PHONY: init test requirements venv

init: venv dev requirements
	source venv/bin/activate
	poetry env info

lint:
	poetry run black -q --check --exclude venv/ --color --diff .

test:
	VERBOSE=$(VERBOSITY) py.test $(PYTESTFLAGS) -rA -vvvv tests/ \
		--log-format="%(asctime)s %(levelname)s %(message)s" \
		--log-date-format="%Y-%m-%d %H:%M:%S" \
		--show-capture=all

venv:
	pip3 install -U pip --break-system-packages
	pip3 install -U virtualenv --break-system-packages
	python3 -mvenv venv/

requirements:
	source venv/bin/activate
	poetry install

dev:
	source venv/bin/activate
	$(PIP3) install poetry setuptools wheel pip
	poetry check
