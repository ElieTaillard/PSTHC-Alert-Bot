import asyncio
import logging
from datetime import datetime
from io import BytesIO

import aiohttp
import discord
import feedparser
from discord.ext import commands

from utils import limit_string_length

logger = logging.getLogger()


class PsthcBot(commands.Bot):
    """
    Discord bot for monitoring PSTHC RSS feed and sending notifications to specified channels.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the bot with necessary parameters.

        Parameters:
            *args: Variable length argument list.
            **kwargs: Variable length keyword argument list.
        """
        super().__init__(*args, **kwargs)

        self.rss_url = kwargs.get("rss_url")
        self.interval = kwargs.get("interval", 1)
        self.color = kwargs.get("color")
        self.db = kwargs.get("db")

        self.last_entry_id = None

        # Retrieve the latest entry from the RSS feed
        feed = feedparser.parse(self.rss_url)
        if len(feed.entries) > 0:
            self.last_entry_id = feed.entries[0].id

    async def setup_hook(self):
        """
        Set up the background task to check the RSS feed upon bot initialization.
        """
        logger.info("Création de la tâche en arrière-plan pour vérifier le flux RSS.")
        self.bg_task = self.loop.create_task(self.check_rss())
        logger.info("Bot prêt !")

    async def on_ready(self):
        """
        Event handler for when the bot is ready.
        """
        logger.info(f"Utilisateur connecté : {self.user} (ID : {self.user.id})")
        logger.info("Synchronisation des commandes slash...")
        await self.tree.sync()
        logger.info("Commandes synchronisées.")

    async def on_guild_join(self, guild):
        """
        Event handler for when the bot joins a new guild.

        Parameters:
            guild (discord.Guild): The guild the bot joined.
        """
        logger.info(f"Bot ajouté au serveur '{guild.name}'")

        welcome_message = (
            "Salut tout le monde !\n\n"
            "Je suis ravi de rejoindre ce serveur ! Je suis le bot de notification de PSTHC, et je suis là pour vous tenir informé des dernières actualités du site.\n\n"
            "Pour commencer, veuillez demander à un administrateur d'utiliser la commande `/psthc` pour définir l'endroit où je posterai les notifications."
        )

        logger.info("Recherche d'un canal pour poster le message de bienvenue...")

        # Retrieve the general channel of the server
        channel = guild.system_channel

        if channel is not None:
            try:
                await channel.send(welcome_message)
                logger.info("Message de bienvenue envoyé.")
                return
            except:
                # Permission issue or something else
                pass

        # Search for a channel to post the welcome message
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(welcome_message)
                logger.info("Message de bienvenue envoyé.")
                return
            break

        logger.warning(
            "Aucun canal trouvé avec les permissions pour poster le message de bienvenue."
        )

    async def on_guild_remove(self, guild):
        """
        Event handler for when the bot is removed from a guild.

        Parameters:
            guild (discord.Guild): The guild the bot was removed from.
        """
        logger.info(f"Bot retiré du serveur : {guild.name}")
        result_find = self.db.guilds.find_one({"guild_id": guild.id})

        if result_find:
            logger.info("Configuration trouvée en BDD pour le serveur associé")
            logger.info("Suppression des données en BDD pour le serveur associé...")

            result_delete = self.db.guilds.delete_one({"guild_id": guild.id})

            # Remove the server config in database
            if result_delete.deleted_count == 1:
                logger.info("Enregistrement supprimé avec succès")
            else:
                logger.warning("Aucun enregistrement trouvé avec le guild.id spécifié")

    async def fetch_rss(self):
        """
        Fetch the RSS feed content.

        Returns:
            str: The content of the RSS feed.
        """
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
            logger.error(
                f"Une erreur HTTP est survenue lors de la récupération du flux RSS : {e}"
            )
            return None

    async def parse_rss(self):
        """
        Parse the RSS feed content.

        Returns:
            feedparser.FeedParserDict: Parsed feed data.
        """
        rss_data = await self.fetch_rss()
        if rss_data is None:
            return None
        try:
            feed = feedparser.parse(rss_data)
            return feed
        except Exception as e:
            logger.error(
                f"Une erreur s'est produite lors de l'analyse du flux RSS : {e}"
            )
            return None

    async def create_embed(self, entry) -> discord.Embed:
        """
        Create an embed message for a given RSS entry.

        Parameters:
            entry: The RSS entry.

        Returns:
            discord.Embed: The created embed message.
        """
        logger.info("Création d'un message embed...")

        embedMessage = discord.Embed(
            title=limit_string_length(entry.title, 200),
            description=limit_string_length(entry.description, 300),
            url=entry.link,
            color=self.color,
        )

        # Date formatting
        try:
            date_obj = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
            date_format = date_obj.strftime("%a, %d %b %Y %H:%M")
            embedMessage.set_footer(text=date_format)
        except:
            logger.warning(
                "Problème lors du formatage de la date, utilisation de la date brute dans le message embed."
            )
            embedMessage.set_footer(text=entry.published)

        logger.info("Message embed créé.")
        return embedMessage

    async def get_thumb_image(self, url_thumbnail):
        """
        Download and retrieve the thumbnail image.

        Parameters:
            url_thumbnail (str): The URL of the thumbnail.

        Returns:
            BytesIO: The thumbnail image in BytesIO format.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url_thumbnail) as resp:
                    thumb_image = BytesIO(await resp.read())
        except aiohttp.ClientError as e:
            logger.error(
                f"Une erreur HTTP est survenue lors du téléchargement de la thumbnail : {e}"
            )

        return thumb_image

    async def check_rss(self):
        """
        Background task to check the RSS feed at regular intervals.
        """
        await self.wait_until_ready()

        logger.info("Démarrage de la vérification du flux RSS...")

        while not self.is_closed():
            feed = await self.parse_rss()
            if feed is None:
                logger.warning(
                    "Échec de l'analyse du flux RSS. Attente de la prochaine vérification."
                )
                await asyncio.sleep(self.interval)
                continue

            if len(feed.entries) > 0:
                entry = feed.entries[0]

                if entry.id != self.last_entry_id:
                    logger.info(f"Nouvel item détecté : {entry.title}")
                    self.last_entry_id = entry.id

                    # Create an embed message
                    embedMessage = await self.create_embed(entry)

                    url_thumbnail = None
                    try:
                        url_thumbnail = entry.links[1]["href"]
                    except:
                        logger.warning(
                            "Aucune URL de thumbnail trouvée dans le flux RSS."
                        )

                    # Retrieve all servers registered in the database
                    guilds = self.db.guilds.find()

                    logger.info(
                        "Envoi des notifications aux différents serveurs discord..."
                    )

                    for guild in guilds:
                        channel_id = guild["notifications_channel_id"]
                        channel = self.get_channel(channel_id)
                        guild_id = guild["guild_id"]
                        guild = self.get_guild(guild_id)

                        # Channel found, sending the message
                        if channel is not None:
                            # Retrieve the thumbnail
                            if url_thumbnail is not None or url_thumbnail.strip():
                                logger.info(
                                    f"Téléchargement de la thumbnail pour le serveur '{guild.name}'..."
                                )

                                thumb_image = await self.get_thumb_image(url_thumbnail)

                                logger.info("Téléchargement terminé.")

                                thumb_file = discord.File(
                                    fp=thumb_image, filename="thumb.png"
                                )

                                logger.info("Ajout de la thumbnail au message.")
                                embedMessage.set_thumbnail(
                                    url=f"attachment://{thumb_file.filename}"
                                )

                            logger.info("Envoi du message...")

                            try:
                                await channel.send(
                                    content="🚀 Nouvelle Publication sur PSTHC 📰",
                                    embed=embedMessage,
                                    file=thumb_file,
                                )
                                logger.info(
                                    f"Notification envoyée dans le canal '{channel.name}' du serveur '{guild.name}'"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Problème lors de l'envoi du message de le canal '{channel.name}' du serveur '{guild.name}' : {e}"
                                )

                    logger.info(f"Envoi des notifications terminé.")
            else:
                logger.warning("Aucune entrée dans le flux RSS.")

            await asyncio.sleep(self.interval)

        logger.critical("La connexion WebSocket s'est fermée.")
