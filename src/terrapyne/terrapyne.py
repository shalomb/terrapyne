#!/usr/bin/env python3

# -*- coding: utf-8 -*-

from textwrap import dedent
from functools import cached_property
from pathlib import Path
from shutil import which
from subprocess import Popen, PIPE
from typing import Tuple, Any
import logging as log
import os
import re
import json


class Terraform:
    def __init__(self, required_version=None):
        self.executable = which("terraform") or next(Path("~/.local/bin").expanduser().glob("terraform"))

        self.environment_variables = {
            "TF_IN_AUTOMATION": "1",
            "TF_LOG": "trace",
            "TF_LOG_PATH": "./terraform.log",
            "TF_INPUT": "0",
            "TF_CLI_ARGS": "-no-color",
            "TF_CLI_ARGS_init": "-input=false -no-color",
            "TF_CLI_ARGS_validate": "-no-color",
            "TF_CLI_ARGS_plan": "-input=false -no-color",
            "TF_CLI_ARGS_apply": "-input=false -no-color -auto-approve",
            "TF_CLI_ARGS_destroy": "-input=false -no-color -auto-approve",
            "NO_COLOR": "1",
        }
        # "TF_PLUGIN_CACHE_DIR": "./tf-cache",
        self.tfplan_name = "current.tfplan"  # Name by project

        log.debug(f"terraform executable: {self.executable}")
        if required_version is not None:
            if self.version != required_version:
                raise Exception(f"required version of terraform check failed: {self.version} != {required_version}")

    @cached_property
    def version(self):
        stdout, _, _ = self.exec(
            cmd=["version"],
        )
        result = stdout.replace("\n", " ").replace("Terraform ", "").replace(" on ", " ")
        log.debug(f"version string: {result}")

        version, self.platform = result.split(" ")[0:2]
        log.debug(f"version string: {version}, platform: {self.platform}")
        return re.sub("^v", "", version)

    def init(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["init", *(args or [])],
            expect_stdout=["Terraform has been successfully initialized!"],
        )

    def validate(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["validate", *(args or [])],
            ignore_exit_code=True,
            expect_stdout=["Success! The configuration is valid."],
        )

    def plan(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["plan", *(args or [])],
            # expect_stdout=[
            #     "No changes. Your infrastructure matches the configuration."
            # ],
        )

    def apply(self, args=None) -> Tuple[str, str, int]:
        if not os.path.exists(self.tfplan_name):
            self.init(args=["-backend=false"])
            self.plan(args=[f"-out={self.tfplan_name}"])
        return self.exec(
            cmd=["apply", *(args or [])],
            # expect_stdout=[
            #     "Apply complete!",
            #     "No changes. Your infrastructure matches the configuration.",
            # ],
        )

    def output(self, args=None) -> Tuple[str, str, int]:
        o, e, c = self.exec(
            cmd=["output", *(args or ["-json"])],
        )
        return json.loads(o), e, c

    def state(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["state", *(args or [""])],
            # expect_stdout=[
            #     "No changes. Your infrastructure matches the configuration."
            # ],
        )

    def get_resources(self) -> dict[Any, Any]:
        o, _, _ = self.dump()
        return o["resources"]

    def get_outputs(self) -> dict[Any, Any]:
        o, _, _ = self.dump()
        return o["outputs"]

    def dump(self, args=None) -> Tuple[dict[Any, Any], str, int]:
        o, e, c = self.exec(
            cmd=["state", "pull", *(args or [""])],
        )
        return json.loads(o), e, c

    def destroy(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["destroy", *(args or [])]
            # expect_stdout=[
            #     "Apply complete!",
            #     "No changes. Your infrastructure matches the configuration.",
            # ],
        )

    def fmt(self) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["fmt", "-recursive"],
        )

    def make_layout(self) -> None:
        for tf_file in [
            "main.tf",
            "versions.tf",
            "terraform.tf",
            "variables.tf",
            "outputs.tf",
        ]:
            with open(tf_file, "w") as f:
                if tf_file == "terraform.tf":
                    f.write(
                        dedent(
                            """
                    terraform {
                      required_providers { }
                    }
                    """
                        )
                    )
                elif tf_file == "locals.tf":
                    f.write(
                        dedent(
                            """
                    locals {
                    }
                    """
                        )
                    )
                else:
                    f.write(f"// {tf_file}\n")
        return None

    def exec(
        self,
        cmd,
        input="",
        expect_exit_code=0,
        ignore_exit_code=False,
        expect_stdout=None,
        expect_stderr=None,
    ) -> Tuple[str, str, int]:
        log.debug(f"terraform.exec({cmd}) with {self.executable}")
        cmd.insert(0, self.executable)
        log.debug(f"terraform.exec({cmd})")

        os.environ.update(self.environment_variables)

        p = Popen(
            cmd or ["terraform", "version"],
            stdout=PIPE,
            stdin=PIPE,
            stderr=PIPE,
        )

        stdout, stderr = p.communicate(input=input.encode())
        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()
        exit_code = p.returncode
        log.debug(f"stdout: {stdout}")
        log.debug(f"stderr: {stderr}")
        log.debug(f"exit_code: {exit_code}")

        if ignore_exit_code is not True and exit_code != expect_exit_code:
            raise Exception(f"[Error]: exit_code {exit_code} running '{cmd}': {stderr}")

        if expect_stdout is not None:
            for string in expect_stdout:
                if string not in stdout:
                    raise Exception(f"stdout did not contain expected string: {string}")

        if expect_stderr is not None:
            for string in expect_stderr:
                if string not in stderr:
                    raise Exception(f"stderr did not contain expected string: {string}")

        return stdout, stderr, exit_code
