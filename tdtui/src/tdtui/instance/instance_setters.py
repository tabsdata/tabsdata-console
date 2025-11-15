import subprocess
from tdtui.core.subprocess_runner import run_bash
from yaspin import yaspin
from yaspin.spinners import Spinners
import time


def set_config_yaml(instance):
    return


def start_instance(instance):

    return


def stop_instance(instance):
    return


def create_instance(instance):
    instance_name = instance["name"]
    with yaspin().bold.blink.bouncingBall.on_cyan as sp:
        run_bash(f"tdserver status")
        time.sleep(10)
    return


create_instance({"name": "test"})
