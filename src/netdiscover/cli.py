#!/usr/bin/env python3
# Copyright (c), Rob Woodward. All rights reserved.
#
# This file is part of Get ISE tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import asyncio
import json
import logging
import os
import pprint
import re
import tempfile

import aiosqlite
import click

from netdiscover.worker import DeviceWorker, DeviceWorkerException

logging.basicConfig(format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger()

pp = pprint.PrettyPrinter(indent=2, width=120)

async def setup_database(db_file: str) -> aiosqlite.Connection:
    try:
        db_con = await aiosqlite.connect(db_file)
        db_cursor = await db_con.cursor()
        await db_cursor.execute("DROP TABLE IF EXISTS devices")
        await db_cursor.execute(
            "CREATE TABLE devices(hostname, vendor, os, protocol)"
        )
        await db_con.commit()
        await db_cursor.close()
        return db_con
    except aiosqlite.Error as err:
        raise SystemExit(f"Failed to create new SQLite database: {err}") from err



def compile_patterns() -> dict[str, re.Pattern]:
    """Compile a dictionary of string patterns into regex patterns.

    Args:
        pattern_dict (dict[str, str]): A dictionary of keys and their associated string patterns.

    Returns:
        dict[str, Pattern]: A dictionary mapping each key to its compiled regex pattern.
    """
    return {
        "IOS-XR": re.compile("Cisco IOS XR"),
        "IOS-XE": re.compile("Cisco IOS-XE"),
        "IOS": re.compile("Cisco IOS"),
        "JunOS": re.compile("JunOS"),
    }




async def do_devices(devices: list, prog_args: dict):
    queue = asyncio.Queue()
    db_lock = asyncio.Lock()

    db_con = await setup_database(prog_args["db_file"])

    for device in devices:
        await queue.put(device)

    # Create three worker tasks to process the queue concurrently.
    workers = [asyncio.create_task(DeviceWorker(db_con, db_lock, queue, prog_args).run(i)) for i in range(3)]

    try:
        await asyncio.gather(*workers, return_exceptions=False)
    except DeviceWorkerException as err:
        logger.error("Worker failed can not continue: %s", err)
        for task in workers:
            task.cancel()

        await asyncio.gather(*workers, return_exceptions=True)
        await db_con.close()
        return

    #await output_results(db_con, prog_args["out_format"], prog_args["quotechar"], prog_args["delimeter"])
    await db_con.close()


def setup_devices(cli_args: dict) -> list:
    """
    Setup devices based on command-line arguments.

    Args:
        cli_args (dict): Dictionary containing command-line arguments.

    Returns:
        list: list of devices.

    Raises:
        SystemExit: If required --seed or --device options are missing or there is an error decoding the JSON seed file.
    """

    if cli_args["device"]:
        return [cli_args["device"]]
    elif cli_args["seed"]:
        return []
    else:
        raise SystemExit("Required --seed or --device options are missing.")


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

    devices = setup_devices(cli_args)

    with tempfile.TemporaryDirectory(prefix="netdiscover_", suffix="_db", ignore_cleanup_errors=False) as tmp_db_dir:

        prog_args = {
            "username": cfg["username"],
            "password": cfg["password"],
            "db_file": f"{tmp_db_dir}/results.db",
        }

        asyncio.run(do_devices(devices, prog_args))


