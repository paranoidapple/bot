from __future__ import annotations

import hikari
import lightbulb

import os
from pathlib import Path

from .db import Database


class Bot(lightbulb.BotApp):
    base_dir = Path(os.path.abspath(__file__)).parents[1]

    def __init__(self, **kwargs):
        super().__init__(
            intents=hikari.Intents.ALL,
            default_enabled_guilds=[988119221705797632],
            help_slash_command=True,
            **kwargs,
        )

        # Global variables
        self.db = Database(self)

        # Do stuff
        self.start_listeners()

    def start_listeners(self):
        self.subscribe(hikari.StartingEvent, self.on_starting)

    async def on_starting(self, _: hikari.StartingEvent):
        self.load_extensions_from(f"{Bot.base_dir}/extensions/")
        await self.db.connect()
