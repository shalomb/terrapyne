#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

from pathlib import Path
import sys
import os
import tempfile
from decouple import config
from unittest import mock

sys.path.append(Path(f"{__file__}/../src").resolve())

import terrapyne
import terrapyne.logging
import logging as log

terraform = terrapyne.Terraform()
VERBOSITY = int(config("VERBOSITY", 0))
VERBOSE = int(config("VERBOSE", 0))
DEBUG = int(config("DEBUG", 0))
VERBOSITY = 5 if DEBUG != 0 else VERBOSE or VERBOSITY


class TestImport:
    def test_terrapyne_import(self) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            assert terraform
            assert terraform.version
            assert terraform.executable

    def test_terrapyne_required_version(self, tf_required_version) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            terraform = terrapyne.Terraform(required_version=tf_required_version)
            assert terraform.version
            assert len(terraform.platform.split("_")) == 2

    def test_terrapyne_blank_layout(self) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                # Path(terraform.envvars.get("TF_PLUGIN_CACHE_DIR", "tf-cache")).mkdir()

                _ = terraform.fmt()
                _ = terraform.init()
                _ = terraform.validate()
                _ = terraform.plan()
                _apply_out = terraform.apply()
                _ = terraform.destroy()

                assert "0 added" in _apply_out[0]
                assert "0 changed" in _apply_out[0]
                assert "0 destroyed" in _apply_out[0]

    def test_terrapyne_minimal_layout(self) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                # Path(terraform.envvars.get("TF_PLUGIN_CACHE_DIR", "tf-cache")).mkdir()

                _ = terraform.init()

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
                assert _output_out.foo.value == "bar"

                _outputs_out = terraform.get_outputs()
                # assert _outputs_out["example"]["value"]["content"] == "foo!"
                assert _outputs_out
                assert _outputs_out.example.value.content == "foo!"

                _resources_out = terraform.get_resources()
                assert _resources_out[0].instances[0].attributes.content == "foo!"
                assert _resources_out[0].instances[0].attributes.filename == "./foo.bar"

                Path("./foo.bar").unlink()
                _apply_out = terraform.apply()
                assert Path("foo.bar").exists()
                assert "1 added" in _apply_out[0]

                _destroy_out = terraform.destroy()
                assert "1 destroyed" in _destroy_out[0]

    def test_terrapyne_env_vars(self) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            envvars = {"TF_LOG": "trace", "TF_LOG_PATH": "tf-log.log", "foo": "nbar"}
            terraform = terrapyne.Terraform(envvars=envvars)
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()

                with open("outputs.tf", "a") as f:
                    f.write(
                        """
                        variable "foo" { type = string }
                        output "foo" { value = var.foo }
                    """
                    )

                # default env vars
                _ = terraform.apply()
                _output_out = terraform.output()
                assert _output_out.foo.value == envvars["foo"]

                # per apply env vars
                localvars = {"foo": "env_bar"}
                _ = terraform.apply(envvars=localvars)
                _output_out = terraform.output()
                assert _output_out.foo.value == localvars["foo"]

                # external env vars
                localvars = {"TF_VAR_foo": "external_bar"}
                with mock.patch.dict("os.environ", localvars, clear=True):
                    _ = terraform.apply()
                    _output_out = terraform.output()
                    assert _output_out.foo.value == localvars["TF_VAR_foo"]

                # different env vars per apply for the same workspace
                # env vars must not be persisted across runs
                _ = terraform.apply()
                _output_out = terraform.output()
                assert _output_out.foo.value == envvars["foo"]

    def test_terrapyne_tf_tfvars(self) -> None:
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            tfvars = {
                "foo": "tfvars_bar",
                "bar": True,
                "baz": [1, 2],
                "moo": {"foo": "bar", "baz": "moo"},
            }
            terraform = terrapyne.Terraform(tfvars=tfvars)
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                with open("outputs.tf", "a") as f:
                    f.write(
                        """
                        variable "foo" { }
                        output "foo" { value = var.foo }
                        variable "bar" { }
                        output "bar" { value = var.bar }
                        variable "baz" { }
                        output "baz" { value = var.baz }
                        variable "moo" { }
                        output "moo" { value = var.moo }
                    """
                    )

                # round-trip tests
                _ = terraform.apply()
                _output_out = terraform.output()
                assert _output_out.foo.value == tfvars["foo"]
                assert _output_out.bar.value is tfvars["bar"]
                assert sorted(_output_out.baz.value) == sorted(tfvars["baz"])
                assert _output_out.moo.value.foo == tfvars["moo"]["foo"]
                assert _output_out.moo.value.baz == tfvars["moo"]["baz"]


if __name__ == "__main__":
    with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
        log.info("Starting tests manually")
        TestImport().test_terrapyne_import()
        TestImport().test_terrapyne_required_version("1.9.7")
        TestImport().test_terrapyne_blank_layout()
        TestImport().test_terrapyne_minimal_layout()
