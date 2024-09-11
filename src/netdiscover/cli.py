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
import logging
import re

import click

from scrapli.driver import GenericDriver

logging.basicConfig(format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger()

pp = pprint.PrettyPrinter(indent=2, width=120)

def compile_patterns() -> dict[str, re.Pattern]:
    """Compile a dictionary of string patterns into regex patterns.

    Args:
        pattern_dict (dict[str, str]): A dictionary of keys and their associated string patterns.

    Returns:
        dict[str, Pattern]: A dictionary mapping each key to its compiled regex pattern.
    """
    return {
      "IOS-XR": re.compile('Cisco IOS XR'),
      "IOS-XE": re.compile('Cisco IOS-XE'),
      "IOS": re.compile('Cisco IOS'),
      "JunOS": re.compile('JunOS')
    }


def parse_output(output: str):
    pass

def connect(hostname: str, username: str, password: str):

    MY_DEVICE = {
        "host": hostname,
        "auth_username": username,
        "auth_password": password,
        "auth_strict_key": False,
        "asyncssh": {
            "kex_algs": "+diffie-hellman-group1-sha1,diffie-hellman-group-exchange-sha1",
            "encryption_algs": "+3des-cbc",
        }
    }

    # Context manager is a great way to use scrapli, it will auto open/close the connection for you:
    with GenericDriver(**MY_DEVICE) as conn:
        conn.send_command("terminal length 0")
        result = conn.send_command("show version")

    pp.pprint(result.result)


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
@click.option(
    "--loglevel",
    "-L",
    type=str,
    default="WARNING",
    envvar="NETDISCOVER_LOG_LEVEL",
    help="Set logging level.",
)
@click.option(
    "-d",
    "--device",
    type=str,
    metavar="HOSTNAME",
    help="Single device to connect to",
)
def cli(**cli_args):

    cfg = load_config(cli_args["config"])
    pp.pprint(cfg)
    logger.setLevel(cli_args["loglevel"].upper())

    connect(cli_args['device'], cfg['username'], cfg['password'])
