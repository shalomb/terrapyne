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


class TerraformException(Exception):
    pass


class Terraform:
    def __init__(self, required_version=None, environment_variables={}):
        self.executable = which("terraform") or next(Path("~/.local/bin").expanduser().glob("terraform"))

        self.environment_variables = {
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
            "NO_COLOR": "1",
            "TF_CLI_ARGS": "-no-color",
            "TF_CLI_ARGS_init": "-input=false -no-color",
            "TF_CLI_ARGS_validate": "-no-color",
            "TF_CLI_ARGS_plan": "-input=false -no-color",
            "TF_CLI_ARGS_apply": "-input=false -no-color -auto-approve",
            "TF_CLI_ARGS_destroy": "-input=false -no-color -auto-approve",
        } | self.generate_environment_variables(environment_variables)
        # "TF_LOG": "trace",
        # "TF_LOG_PATH": "./terraform.log",
        # "TF_PLUGIN_CACHE_DIR": "./tf-cache",
        self.tfplan_name = "current.tfplan"  # Name by project

        log.debug(f"terraform executable: {self.executable}")
        if required_version is not None:
            if self.version != required_version:
                raise TerraformException(f"required version of terraform check failed: {self.version} != {required_version}")

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
        )

    def validate(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["validate", *(args or [])],
            ignore_exit_code=True,
        )

    def plan(self, args=None, environment_variables={}) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["plan", *(args or [])],
            environment_variables=self.generate_environment_variables(environment_variables),
        )

    def apply(self, args=None, environment_variables={}) -> Tuple[str, str, int]:
        if not Path(self.tfplan_name).exists():
            self.init(args=["-backend=false"])
            self.plan(
                args=[f"-out={self.tfplan_name}"],
                environment_variables=self.generate_environment_variables(environment_variables),
            )
        return self.exec(
            cmd=["apply", *(args or [])],
            environment_variables=self.generate_environment_variables(environment_variables),
        )

    def output(self, args=None) -> Tuple[Any, str, int]:
        o, e, c = self.exec(
            cmd=["output", *(args or ["-json"])],
        )
        return json.loads(o), e, c

    def state(self, args=None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["state", *(args or [""])],
        )

    def dump(self, args=None) -> Tuple[dict[Any, Any], str, int]:
        o, e, c = self.exec(
            cmd=["state", "pull", *(args or [""])],
        )
        return json.loads(o), e, c

    def destroy(self, args=None) -> Tuple[str, str, int]:
        return self.exec(cmd=["destroy", *(args or [])])

    def fmt(self) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["fmt", "-recursive"],
        )

    def get_resources(self) -> dict[Any, Any]:
        o, _, _ = self.dump()
        return o["resources"]

    def get_outputs(self) -> dict[Any, Any]:
        o, _, _ = self.dump()
        return o["outputs"]

    def generate_environment_variables(self, in_vars) -> dict[str, str]:
        updated = {}
        for key in in_vars:
            newkey = key
            if key.startswith("TF_VAR"):
                newkey = re.sub("^TF_VAR_", "", key)
            updated[f"TF_VAR_{newkey}"] = in_vars[key]
        return updated

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
        environment_variables={},
    ) -> Tuple[str, str, int]:
        cmd.insert(0, self.executable)
        log.debug(f"terraform.exec({cmd}) with {self.executable}")

        process_env_vars = {}
        for key in os.environ:
            if key.startswith("TF_VAR_"):
                process_env_vars[key] = os.environ[key]

        p = Popen(
            cmd or ["terraform", "version"],
            stdout=PIPE,
            stdin=PIPE,
            stderr=PIPE,
            env=(self.environment_variables | process_env_vars | environment_variables),
        )

        stdout, stderr = p.communicate(input=input.encode())
        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()
        exit_code = p.returncode
        logmsg = " ".join(
            [
                "terraform.exec:",
                f"exit_code:[{exit_code}]",
                f"stdout:[{stdout}]",
                f"stderr:[{stderr}]",
                f"cwd:[{os.getcwd()}]",
            ]
        )
        log.debug(logmsg)

        if ignore_exit_code is not True and exit_code != expect_exit_code:
            raise TerraformException(f"[Error]: exit_code {exit_code} running '{cmd}': {stderr}")

        return stdout, stderr, exit_code
