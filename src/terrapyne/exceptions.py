#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """


class TerraformException(Exception):
    pass


class TerraformVersionException(TerraformException):
    pass


class TerraformApplyException(TerraformException):
    def __init__(self, message, exit_code, expect_exit_code, stdout, stderr, pwd):
        self.message = message
        self.exit_code = exit_code
        self.expect_exit_code = expect_exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.pwd = pwd
