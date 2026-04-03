#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """


class TerraformError(Exception):
    pass


class TerraformVersionError(TerraformError):
    pass


class TerraformApplyError(TerraformError):
    def __init__(self, message, exit_code, expect_exit_code, stdout, stderr, pwd):
        self.message = message
        self.exit_code = exit_code
        self.expect_exit_code = expect_exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.pwd = pwd


# Backwards compatible aliases for historical exception names
TerraformVersionException = TerraformVersionError
TerraformApplyException = TerraformApplyError
