#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

import contextlib
import os


# https://stackoverflow.com/a/75049063/742600
@contextlib.contextmanager
def change_directory(new_dir):
    old_dir = os.getcwd()

    # This could raise an exception, but it's probably
    # best to let it propagate and let the caller
    # deal with it, since they requested x
    os.chdir(new_dir)

    try:
        yield

    finally:
        # This could also raise an exception, but you *really*
        # aren't equipped to figure out what went wrong if the
        # old working directory can't be restored.
        os.chdir(old_dir)
