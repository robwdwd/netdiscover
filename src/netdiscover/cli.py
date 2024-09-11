#!/usr/bin/env python3
# Copyright (c), Rob Woodward. All rights reserved.
#
# This file is part of Get ISE tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import pprint
from json import JSONDecodeError, load
import click

def load_config(config_file):
    try:
        return json.load(config_file)
    except JSONDecodeError as err:
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
