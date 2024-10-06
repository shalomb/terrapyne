#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

from pathlib import Path
import shutil
import sys
import os
import tempfile
import platform
import json
from decouple import config
from unittest import mock

sys.path.append(Path(__file__ + "/../src").resolve())

import terrapyne
import terrapyne.logging
import logging as log

terraform = terrapyne.Terraform()
VERBOSITY = int(config("VERBOSITY", 0))
VERBOSE = int(config("VERBOSE", 0))
DEBUG = int(config("DEBUG", 0))
VERBOSITY = 5 if DEBUG != 0 else VERBOSE or VERBOSITY


class TestImport:
    def test_terrapyne_import(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            assert terraform
            assert terraform.version
            assert terraform.executable

    def test_terrapyne_required_version(self, tf_required_version):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            terraform = terrapyne.Terraform(required_version=tf_required_version)
            assert terraform.version
            assert len(terraform.platform.split("_")) == 2

    def test_terrapyne_blank_layout(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                # Path(terraform.environment_variables.get("TF_PLUGIN_CACHE_DIR", "tf-cache")).mkdir()

                shutil.copy("terraform.tf", "/tmp/terraform-1.tf")

                _fmt_out = terraform.fmt()

                shutil.copy("terraform.tf", "/tmp/terraform-2.tf")

                _init_out = terraform.init()

                _validate_out = terraform.validate()

                _plan_out = terraform.plan()

                _apply_out = terraform.apply()

                _destroy_out = terraform.destroy()

                assert "0 added" in _apply_out[0]
                assert "0 changed" in _apply_out[0]
                assert "0 destroyed" in _apply_out[0]

    def test_terrapyne_minimal_layout(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                # Path(terraform.environment_variables.get("TF_PLUGIN_CACHE_DIR", "tf-cache")).mkdir()

                _init_out = terraform.init()

                with open("outputs.tf", "a") as f:
                    f.write(
                        """
                    resource "local_file" "foo" {
                        content  = "foo!"
                        filename = "${path.module}/foo.bar"
                    }

                    output "example" {
                        sensitive = true
                        value = local_file.foo
                    }

                    output "foo" {
                        value = "bar"
                    }
                    """
                    )

                _apply_out = terraform.apply()
                assert Path("foo.bar").exists()
                assert "1 added" in _apply_out[0]
                assert "0 changed" in _apply_out[0]
                assert "0 destroyed" in _apply_out[0]

                _output_out = terraform.output()
                assert _output_out[0]["foo"]["value"] == "bar"

                _outputs_out = terraform.get_outputs()
                assert _outputs_out["example"]["value"]["content"] == "foo!"

                _resources_out = terraform.get_resources()
                assert _resources_out[0]["instances"][0]["attributes"]["content"] == "foo!"
                assert _resources_out[0]["instances"][0]["attributes"]["filename"] == "./foo.bar"

                Path("./foo.bar").unlink()
                _apply_out = terraform.apply()
                assert Path("foo.bar").exists()
                assert "1 added" in _apply_out[0]

                _destroy_out = terraform.destroy()
                assert "1 destroyed" in _destroy_out[0]

    def test_terrapyne_env_vars(self, capsys):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            envvars = {"TF_LOG": "trace", "TF_LOG_PATH": "tf-log.log", "foo": "nbar"}
            terraform = terrapyne.Terraform(environment_variables=envvars)
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()

                with open("outputs.tf", "a") as f:
                    f.write(
                        """
                        variable "foo" {
                        type = string
                        }
                        output "foo" {
                        value = var.foo
                        }
                    """
                    )

                # default env vars
                _apply_out = terraform.apply()
                _output_out = terraform.output()
                assert _output_out[0]["foo"]["value"] == "nbar"

                # per apply env vars
                _apply_out = terraform.apply(environment_variables={"foo": "env_bar"})
                _output_out = terraform.output()
                assert _output_out[0]["foo"]["value"] == "env_bar"

                # external env vars
                with mock.patch.dict('os.environ', {'TF_VAR_foo': 'external_bar'}, clear=True):
                    _apply_out = terraform.apply()
                    _output_out = terraform.output()
                    assert _output_out[0]["foo"]["value"] == "external_bar"

                # different env vars per apply
                _apply_out = terraform.apply()
                _output_out = terraform.output()
                assert _output_out[0]["foo"]["value"] == "nbar"


if __name__ == "__main__":
    with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
        log.info("Starting tests manually")
        TestImport().test_terrapyne_import()
        TestImport().test_terrapyne_required_version("1.9.7")
        TestImport().test_terrapyne_blank_layout()
        TestImport().test_terrapyne_minimal_layout()
