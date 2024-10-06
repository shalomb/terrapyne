#!/usr/bin/env python3

# -*- coding: utf-8 -*-

from functools import cached_property
from pathlib import Path
from shutil import which
from subprocess import Popen, PIPE
from textwrap import dedent
from typing import Tuple, Any, TypeAlias, Union
import json
import logging as log
from benedict import benedict
import os
import re

from .utils import change_directory


class TerraformException(Exception):
    pass


NullableDict: TypeAlias = Union[dict[Any, Any], None]
NullableList: TypeAlias = Union[list, None]
NullableStr: TypeAlias = Union[str, None]


class Terraform:
    def __init__(
        self,
        workspace_directory: str,
        required_version: NullableStr = None,
        tfvars: NullableDict = None,
        envvars: NullableDict = None,
    ):
        self.executable = which("terraform") or next(Path("~/.local/bin").expanduser().glob("terraform"))
        self.workspace_directory = workspace_directory
        self.tfvars = self.benedict(tfvars or {})

        self.envvars = {
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
            "NO_COLOR": "1",
            "TF_CLI_ARGS": "-no-color",
            "TF_CLI_ARGS_init": "-input=false -no-color",
            "TF_CLI_ARGS_validate": "-no-color",
            "TF_CLI_ARGS_plan": "-input=false -no-color",
            "TF_CLI_ARGS_apply": "-input=false -no-color -auto-approve",
            "TF_CLI_ARGS_destroy": "-input=false -no-color -auto-approve",
        } | self.generate_envvars(envvars or {})

        # "TF_LOG": "trace",
        # "TF_LOG_PATH": "./terraform.log",
        # "TF_PLUGIN_CACHE_DIR": "./tf-cache",
        self.tfplan_name = "current.tfplan"  # Name by project

        assert self.version
        if required_version is not None:
            if self.version != required_version:
                raise TerraformException(f"required version of terraform check failed: {self.version} != {required_version}")

    @property
    def version(self) -> str:
        stdout, _, _ = self.exec(
            cmd=["version", "-json"],
        )
        self._version_info = self.benedict(json.loads(stdout))
        return self._version_info.terraform_version

    @property
    def platform(self) -> str:
        return self._version_info.platform

    def init(self, args: NullableList = None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["init", *(args or [])],
        )

    def validate(self, args: NullableList = None) -> benedict:
        o, e, c = self.exec(
            cmd=["validate", *(args or ["-json"])],
            ignore_exit_code=True,
        )
        if c != 0:
            raise TerraformException(f"terraform validate failed: {c} {e}")
        return self.objectify(o)

    def plan(
        self,
        args: NullableList = None,
        tfvars: NullableDict = None,
        envvars: NullableDict = None,
    ) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["plan", *(args or [])],
            tfvars=self.benedict(tfvars or {}),
            envvars=self.generate_envvars(envvars or {}),
        )

    def apply(
        self,
        args: NullableList = None,
        tfvars: NullableDict = None,
        envvars: NullableDict = None,
    ) -> Tuple[str, str, int]:
        if not Path(self.tfplan_name).exists():
            self.init(args=["-backend=false"])
            self.plan(
                args=[f"-out={self.tfplan_name}"],
                envvars=self.generate_envvars(envvars or {}),
            )
        return self.exec(
            cmd=["apply", *(args or [])],
            tfvars=self.benedict(tfvars or {}),
            envvars=self.generate_envvars(envvars or {}),
        )

    def output(self, args: NullableList = None) -> benedict:
        o, _, _ = self.exec(
            cmd=["output", *(args or ["-json"])],
        )
        return benedict(json.loads(o), keypath_separator="¬")

    def state(self, args: NullableList = None) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["state", *(args or [""])],
        )

    def dump(self, args: NullableList = None) -> Tuple[dict[Any, Any], str, int]:
        o, e, c = self.exec(
            cmd=["state", "pull", *(args or [""])],
        )
        return json.loads(o), e, c

    def tfstate(self) -> benedict:
        o, _, _ = self.dump()
        return benedict(o, keypath_separator="¬")

    def destroy(self, args: NullableList = None) -> Tuple[str, str, int]:
        return self.exec(cmd=["destroy", *(args or [])])

    def fmt(self) -> Tuple[str, str, int]:
        return self.exec(
            cmd=["fmt", "-recursive"],
        )

    def get_resources(self) -> benedict:
        return self.tfstate().resources

    def get_outputs(self) -> benedict:
        return self.tfstate().outputs

    def generate_envvars(self, in_vars) -> dict[str, str]:
        updated = {}
        for key in in_vars:
            newkey = key
            if key.startswith("TF_VAR"):
                newkey = re.sub("^TF_VAR_", "", key)
            updated[f"TF_VAR_{newkey}"] = in_vars[key]
        return updated

    def benedict(self, d: dict) -> benedict:
        return benedict(d, keypath_separator="¬")

    def objectify(self, string: str) -> benedict:
        return self.benedict(json.loads(string))

    @property
    def provider_selections(self) -> dict:
        return self._version_info.provider_selections

    def provider_schema(self) -> benedict:
        o, _, _ = self.exec(cmd=["providers", "schema", "-json"])
        return self.objectify(o)

    def modules(self) -> benedict:
        if modinfo := Path(".terraform/modules/modules.json").resolve():
            with open(modinfo, "r") as f:
                r = f.read()
                log.debug(f"R:{r} // f:{modinfo}")
                return self.objectify(r)
        return self.benedict({"Modules": []})

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
        envvars: NullableDict = None,
        tfvars: NullableDict = None,
    ) -> Tuple[str, str, int]:
        with change_directory(self.workspace_directory):
            cmd.insert(0, self.executable)
            log.debug(f"terraform.exec({cmd}) with {self.executable}")

            tfvars = self.benedict(self.tfvars | (tfvars or {}))
            with open("terrapyne.auto.tfvars.json", "w") as f:
                f.write(json.dumps(tfvars))

            process_env_vars = {}
            for key in os.environ:
                if key.startswith("TF_VAR_"):
                    process_env_vars[key] = os.environ[key]

            p = Popen(
                cmd or ["terraform", "version"],
                cwd=self.workspace_directory,
                stdout=PIPE,
                stdin=PIPE,
                stderr=PIPE,
                env=self.benedict(self.envvars | process_env_vars | (envvars or {})),
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
