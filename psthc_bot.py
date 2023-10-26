import asyncio
import json
import logging

import aiohttp
import async_timeout
import feedparser
import yarl
from aiohttp import ClientResponseError, ClientSession
from discord.ext import commands


class PsthcBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rss_url = kwargs.get("rss_url", None)
        self.interval = kwargs.get("interval", 1)
        self.last_entry_id = None

        feed = feedparser.parse(self.rss_url)
        if len(feed.entries) > 0:
            self.last_entry_id = feed.entries[0].id

    async def setup_hook(self) -> None:
        logging.info("Création de la tâche en arrière-plan pour vérifier le flux RSS.")
        self.bg_task = self.loop.create_task(self.check_rss())

    async def on_ready(self):
        logging.info(f"Utilisateur connecté : {self.user} (ID : {self.user.id})")
        logging.info("Synchronisation des slash commandes...")
        await self.tree.sync()
        logging.info("Commandes synchronisées.")

    async def fetch_rss(self):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
                }
                async with session.request(
                    method="GET", url=self.rss_url, headers=headers
                ) as response:
                    response.raise_for_status()
                    return await response.text()
        except aiohttp.ClientError as e:
            logging.error(f"Une erreur HTTP est survenue : {e}")
            return None

    async def parse_rss(self):
        rss_data = await self.fetch_rss()
        if rss_data is None:
            return None
        try:
            feed = feedparser.parse(rss_data)
            return feed
        except Exception as e:
            logging.error(
                f"Une erreur s'est produite lors de l'analyse du flux RSS : {e}"
            )
            return None

    async def check_rss(self):
        await self.wait_until_ready()

        logging.info("Démarrage de la vérification du flux RSS...")

        while not self.is_closed():
            logging.info("Vérification du flux RSS...")
            feed = await self.parse_rss()
            if feed is None:
                logging.warning(
                    "Échec de l'analyse du flux RSS. Attente de la prochaine vérification."
                )
                await asyncio.sleep(self.interval)
                continue

            if len(feed.entries) > 0:
                entry = feed.entries[0]

                if entry.id != self.last_entry_id:
                    logging.info(f"Nouvel item détecté : {entry.title}")
                    self.last_entry_id = entry.id

                    with open("channel.json", "r") as jsonFile:
                        data = json.load(jsonFile)

                    channel = self.get_channel(data["channel_id"])

                    logging.info(f"Envoi de la notification à : {channel.name}")
                    await channel.send(f"Nouvel item détecté : {entry.title}")
            else:
                logging.warning("Aucune entrée dans le flux RSS.")

            await asyncio.sleep(self.interval)

        logging.warning("La connexion WebSocket s'est fermée.")
