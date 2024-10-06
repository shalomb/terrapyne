#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" """

import shutil
import sys
import os
import tempfile
import platform
import json

# import pytest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import terrapyne
import terrapyne.logging
import logging as log

terraform = terrapyne.Terraform()
VERBOSITY = int(os.environ.get("VERBOSE", 0))
VERBOSITY = 5 if int(os.environ.get("DEBUG", 0)) >= 1 else VERBOSITY


class TestImport:
    def test_terrapyne_import(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            assert terraform
            log.debug(f"log terrform version: {terraform.version}")
            assert terraform.version
            log.debug(f"log terrform executable: {terraform.executable}")
            assert terraform.executable

    def test_terrapyne_required_version(self, tf_required_version):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            terraform = terrapyne.Terraform(required_version=tf_required_version)
            assert terraform.version
            log.debug(f"log terrform version: {terraform.version}")
            assert len(terraform.platform.split('_')) == 2
            # "{}_{}".format(
            #     platform.system().lower(), platform.release().split("-")[-1]
            # ), f"terraform platform string ({terraform.platform}) appears invalid"
            log.debug(f"log terrform platform: {terraform.platform}")

    def test_terrapyne_blank_layout(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                os.mkdir(terraform.environment_variables.get("TF_PLUGIN_CACHE_DIR", "tf-cache"))

                shutil.copy("terraform.tf", "/tmp/terraform-1.tf")

                _fmt_out = terraform.fmt()
                log.debug(f"fmt: {_fmt_out}")

                shutil.copy("terraform.tf", "/tmp/terraform-2.tf")

                _init_out = terraform.init()
                log.debug(f"init: {_init_out}")

                _validate_out = terraform.validate()
                log.debug(f"validate: {_validate_out}")

                _plan_out = terraform.plan()
                log.debug(f"plan: {_plan_out}")

                _apply_out = terraform.apply()
                log.debug(f"apply: {_apply_out}")

                _destroy_out = terraform.destroy()
                log.debug(f"destroy: {_destroy_out}")

                assert "0 added" in _apply_out[0]
                assert "0 changed" in _apply_out[0]
                assert "0 destroyed" in _apply_out[0]
        assert True

    def test_terrapyne_minimal_layout(self):
        with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                terraform.make_layout()
                os.mkdir(terraform.environment_variables.get("TF_PLUGIN_CACHE_DIR", "tf-cache"))

                _init_out = terraform.init()
                log.debug(f"init: {_init_out}")

                with open("outputs.tf", "a") as f:
                    f.write(
                        """
                    resource "null_resource" "example" {
                      provisioner "local-exec" {
                        command = "echo This command will execute whenever the configuration changes"
                      }
                      # Using triggers to force execution on every apply
                      triggers = {
                        always_run = timestamp()
                      }
                    }

                    output "example" {
                      value = null_resource.example
                    }

                    output "foo" {
                        value = "bar"
                    }
                    """
                    )

                _apply_out = terraform.apply()
                log.debug(f"apply: {_apply_out}")

                assert "1 added" in _apply_out[0]
                assert "0 changed" in _apply_out[0]
                assert "0 destroyed" in _apply_out[0]

                _output_out = terraform.output()
                log.debug(f"output: {_output_out}")
                assert _output_out[0]["foo"]["value"] == "bar"

                _outputs_out = terraform.get_outputs()
                log.debug(f"outputs: {_outputs_out}")
                assert _outputs_out["foo"]["value"] == "bar"

                _resources_out = terraform.get_resources()
                log.debug(f"resources: {_resources_out}")
                assert _resources_out[0]["instances"]

                _destroy_out = terraform.destroy()
                log.debug(f"destroy: {_destroy_out}")

                assert "1 destroyed" in _destroy_out[0]
        assert True


if __name__ == "__main__":
    with terrapyne.logging.cli_log_config(verbose=VERBOSITY, logger=log.root):
        print("hey")
        log.critical("Everything passed")
        TestImport().test_terrapyne_import()
        TestImport().test_terrapyne_required_version()
        TestImport().test_terrapyne_blank_layout()
        TestImport().test_terrapyne_minimal_layout()
