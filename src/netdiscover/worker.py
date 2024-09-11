# Copyright (c) 2024, Rob Woodward. All rights reserved.
#
# This file is part of Net Discover tool Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#

import asyncio
import logging
import pprint
import re

import aiosqlite
from scrapli.driver import AsyncGenericDriver

pp = pprint.PrettyPrinter(indent=2, width=120)

logger = logging.getLogger()


class DeviceWorkerException(Exception):
    """Device worker exception."""

    pass


class DeviceWorker:
    """Device Worker."""

    def __init__(
        self,
        db_con: aiosqlite.Connection,
        db_lock: asyncio.Lock,
        queue: asyncio.Queue,
        match_re: dict['str', re.Pattern],
        prog_args: dict,
    ) -> None:
        """Init.

        Args:
            db_con (aiosqlite.Connection): SQlite DB Connection
            db_lock (asyncio.Lock): Database Lock
            queue (asyncio.Queue): Queue of devices
            prog_args (dict): Program Args

        Raises:
            DeviceWorkerException: When worker does not start
        """
        self.db_con = db_con
        self.queue = queue
        self.db_lock = db_lock
        self.prog_args = prog_args
        self.db_cursor = None
        self.match_re = match_re

    def parse_output(self, output: str):
        for line in output:
            pp.pprint(line)
            # Check each line against all regex patterns
            for label, pattern in self.match_re.items():
                pp.pprint([label, pattern])
                if re.search(pattern, line):
                    pp.pprint(label)


    async def connect(self, hostname: str, username: str, password: str):

        MY_DEVICE = {
            "host": hostname,
            "auth_username": username,
            "auth_password": password,
            "auth_strict_key": False,
            "transport": "asyncssh",
            "transport_options": {
                "asyncssh": {
                    "kex_algs": "+diffie-hellman-group1-sha1,diffie-hellman-group-exchange-sha1",
                    "encryption_algs": "+3des-cbc",
                }
            },
        }

        async with AsyncGenericDriver(**MY_DEVICE) as conn:
            await conn.send_command("terminal length 0")
            result = await conn.send_command("show version")

        return result.result

    async def run(self, i: int) -> None:
        """Device worker coroutine, reads from the queue until empty."""

        try:
            self.db_cursor = await self.db_con.cursor()
        except aiosqlite.Error as err:
            raise DeviceWorkerException(f"Worker {i} failed to create db cursor: {err}") from err

        try:
            while not self.queue.empty():
                device: str = self.queue.get_nowait()
                result = []

                try:
                    result = await self.connect(device, self.prog_args['username'], self.prog_args['password'])
                except Exception as err:
                    logger.exception("[%s] Device failed: %s", device, err)
                    self.queue.task_done()
                    continue

                if not result:
                    logger.info("[%s] Device has no version output.", device)
                    self.queue.task_done()
                    continue

                pp.pprint(result)

                self.parse_output(result)

                # async with self.db_lock:
                #     try:
                #         await self.db_cursor.executemany(
                #             "INSERT INTO neighbours "
                #             "(hostname,os,platform,address_family,ip_version,is_up,pfxrcd,protocol_instance,remote_asn,remote_ip,routing_instance,state) "
                #             "VALUES(:hostname,:os,:platform,:address_family,:ip_version,:is_up,:pfxrcd,:protocol_instance,:remote_asn,:remote_ip,:routing_instance,:state);",
                #             result,
                #         )
                #         await self.db_con.commit()
                #     except aiosqlite.Error as err:
                #         logger.exception("[%s] Failed to insert result in to database: %s", device.hostname, err)

                self.queue.task_done()
        except asyncio.CancelledError:
            logger.info("Worker #%d was cancelled due to failure of other workers.", i)
            raise
        finally:
            logger.info("Worker #%d finished, running cleanup.", i)
            if self.db_cursor:
                await self.db_cursor.close()
