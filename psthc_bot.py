import asyncio
import json
import logging

import feedparser
from discord.ext import commands


class PsthcBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rss_url = kwargs.get("rss_url", None)
        self.last_entry_id = None

        feed = feedparser.parse(self.rss_url)
        if len(feed.entries) > 0:
            self.last_entry_id = feed.entries[0].id

    async def setup_hook(self) -> None:
        logging.info("Création de la Task check RSS en arrière plan")
        self.bg_task = self.loop.create_task(self.check_rss())

    async def on_ready(self):
        logging.info(f"Utilisateur connecté : {self.user} (ID : {self.user.id})")
        logging.info("Synchronisation des commandes...")
        await self.tree.sync()
        logging.info("Commandes synchronisées")

    async def check_rss(self):
        await self.wait_until_ready()

        logging.info("Check du flux RSS...")

        while not self.is_closed():
            feed = feedparser.parse(self.rss_url)

            if len(feed.entries) > 0:
                entry = feed.entries[0]

                if entry.id != self.last_entry_id:
                    logging.info(f"Nouvel item détecté : {entry.title}")
                    self.last_entry_id = entry.id

                    with open("channel.json", "r") as jsonFile:
                        data = json.load(jsonFile)

                    channel = self.get_channel(data["channel_id"])

                    await channel.send(f"Nouvel item détecté : {entry.title}")

            await asyncio.sleep(1)

        logging.warning("La connexion WebSocket s'est fermée")
