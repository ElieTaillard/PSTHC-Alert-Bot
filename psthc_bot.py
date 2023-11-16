import asyncio
import logging
from datetime import datetime
from io import BytesIO

import aiohttp
import discord
import feedparser
from discord.ext import commands


class PsthcBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rss_url = kwargs.get("rss_url")
        self.interval = kwargs.get("interval", 1)
        self.color = kwargs.get("color")
        self.db = kwargs.get("db")

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
            logging.error(
                f"Une erreur HTTP est survenue lors de la récupération du flux RSS : {e}"
            )
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

                    logging.info(f"Création d'un message embed")

                    embedMessage = discord.Embed(
                        title=entry.title,
                        description=entry.description,
                        url=entry.link,
                        color=self.color,
                    )

                    url_thumbnail = entry.links[1]["href"]
                    thumb_file = None

                    if len(url_thumbnail) != 0:
                        # download the image and save in a bytes object
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url_thumbnail) as resp:
                                thumb_image = BytesIO(await resp.read())

                        # creating a discord file
                        thumb_file = discord.File(fp=thumb_image, filename="thumb.png")

                        # setting the file as thumbnail
                        embedMessage.set_thumbnail(
                            url=f"attachment://{thumb_file.filename}"
                        )

                    # Conversion de la date d'origine en un objet datetime
                    date_obj = datetime.strptime(
                        entry.published, "%a, %d %b %Y %H:%M:%S %z"
                    )

                    # Formatage de la date résultante
                    date_format = date_obj.strftime("%a, %d %b %Y %H:%M")

                    embedMessage.set_footer(text=date_format)

                    # Récupération de tous les serveurs enregistrés
                    guilds = self.db.guilds.find()

                    logging.info(
                        f"Envoi des notifications aux différents serveurs discord..."
                    )

                    for guild in guilds:
                        channel_id = guild["notifications_channel_id"]
                        channel = self.get_channel(channel_id)

                        if channel is not None:
                            await channel.send(
                                content="🚀 Nouvelle Publication sur PSTHC 📰",
                                embed=embedMessage,
                                file=thumb_file,
                            )

                    logging.info(f"Envoi des notifications terminé.")
            else:
                logging.warning("Aucune entrée dans le flux RSS.")

            await asyncio.sleep(self.interval)

        logging.warning("La connexion WebSocket s'est fermée.")
