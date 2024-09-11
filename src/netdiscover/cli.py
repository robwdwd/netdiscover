#!/usr/bin/env python3
# Copyright (c), Rob Woodward. All rights reserved.
#
# This file is part of Get ISE tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import json
import os
import pprint

import click
from scrapli.driver import GenericDriver

pp = pprint.PrettyPrinter(indent=2, width=120)


def connect(hostname: str, username: str, password: str):

    MY_DEVICE = {
        "host": hostname,
        "auth_username": username,
        "auth_password": password,
        "auth_strict_key": False,
    }

    # Context manager is a great way to use scrapli, it will auto open/close the connection for you:
    with GenericDriver(**MY_DEVICE) as conn:
        conn.send_command("terminal length 0")
        result = conn.send_command("show version")

    pp.pprint(result)


def load_config(config_file):
    try:
        return json.load(config_file)
    except json.JSONDecodeError as err:
        raise SystemExit(f"Unable to parse configuration file: {err}") from err


@click.command()
@click.option(
    "--config",
    metavar="CONFIG_FILE",
    help="Configuaration file to load.",
    default=os.path.join(os.environ["HOME"], ".config", "netdiscover", "config.json"),
    envvar="NETDISCOVER_CONFIG_FILE",
    type=click.File(mode="r"),
)
def cli(**cli_args):

    cfg = load_config(cli_args["config"])
    pp.pprint(cfg)
    connect('test', cfg['username'], cfg['password'])
