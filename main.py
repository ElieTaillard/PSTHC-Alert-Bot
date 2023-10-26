import json
import logging
import time
from collections import deque

import discord
import feedparser
from discord.ext import commands, tasks

import settings

last_entry_id = None
rss_url = "https://www.psthc.fr/flux.xml"


def run():
    global last_entry_id
    feed = feedparser.parse(rss_url)
    if len(feed.entries) > 0:
        last_entry_id = feed.entries[0].id

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(
        command_prefix=".psthc", status=discord.Status.online, intents=intents
    )

    @bot.event
    async def on_ready():
        logging.info(f"Utilisateur connecté : {bot.user} (ID : {bot.user.id})")

        logging.info("Synchronisation des commandes...")
        await bot.tree.sync()

        if not check_rss.is_running():
            logging.info("Lancement de la Task 'check_rss' ...")
            check_rss.start()
            logging.info("La Task 'check_rss' est lancée")

    @bot.tree.command(
        name="setchannel",
        description="Défini le canal où poster les notifications PSTHC",
    )
    @commands.has_permissions(administrator=True)
    async def set_channel(interaction: discord.Interaction):
        try:
            # Enregistre l'ID du canal pour les futurs messages
            with open("channel.json", "r") as jsonFile:
                data = json.load(jsonFile)

            data["channel_id"] = interaction.channel_id

            with open("channel.json", "w") as jsonFile:
                json.dump(data, jsonFile)

            await interaction.response.send_message(
                f"Canal défini sur {interaction.channel.mention}", ephemeral=True
            )
        except:
            await interaction.response.send_message(
                f"Une erreur est survenue, veuillez réessayer...", ephemeral=True
            )

    @tasks.loop(seconds=1)
    async def check_rss():
        global last_entry_id
        feed = feedparser.parse(rss_url)

        if len(feed.entries) > 0:
            entry = feed.entries[0]

            if entry.id != last_entry_id:
                logging.info(f"Nouvel item détecté : {entry.title}")
                last_entry_id = entry.id

                with open("channel.json", "r") as jsonFile:
                    data = json.load(jsonFile)

                channel = bot.get_channel(data["channel_id"])

                await channel.send(f"Nouvel item détecté : {entry.title}")

    bot.run(settings.TOKEN, root_logger=True)


if __name__ == "__main__":
    run()
