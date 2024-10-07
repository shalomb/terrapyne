#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

import pytest
import subprocess
import re


@pytest.fixture()
def tf_required_version():
    out = subprocess.run(["terraform", "version"], capture_output=True, shell=False)
    if m := re.search('\\d\\.\\d[^ \n]+', out.stdout.decode()):
        return m.group(0)
