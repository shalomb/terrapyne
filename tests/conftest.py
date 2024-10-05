#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

import pytest
import subprocess


@pytest.fixture()
def tf_required_version():
    out = subprocess.run(["terraform", "version"], capture_output=True, shell=False)
    req = out.stdout.decode().strip().split("\n")[0].split(" ")[1].replace("v", "")
    return req
