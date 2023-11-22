import logging

import certifi
import discord
from discord.ext import commands
from discord_logging.handler import DiscordHandler
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import settings
from psthc_bot import PsthcBot


def run():
    if settings.ENV == "DEV":
        client = MongoClient(settings.DB_URI, server_api=ServerApi("1"), tlsCAFile=None)
    else:
        client = MongoClient(
            settings.DB_URI, server_api=ServerApi("1"), tlsCAFile=certifi.where()
        )

    # Send a ping to confirm a successful connection
    try:
        client.admin.command("ping")
        logger.info("Connecté avec succès à MongoDB!")
    except Exception as e:
        logger.error(e)
        return

    db = client["PSTHC"]

    intents = discord.Intents.default()
    intents.message_content = True

    bot = PsthcBot(
        intents=intents,
        command_prefix=".psthc",
        status=discord.Status.online,
        rss_url="https://www.psthc.fr/flux.xml",
        interval=1,
        color=19149,
        db=db,
    )

    @bot.tree.command(
        name="psthc",
        description="Défini le canal actuel comme canal de notifications",
    )
    @commands.has_permissions(administrator=True)
    async def set_channel(interaction: discord.Interaction):
        try:
            if not interaction.channel.permissions_for(
                interaction.guild.me
            ).send_messages:
                await interaction.response.send_message(
                    "Je n'ai pas la permission d'envoyer des messages dans ce canal. Merci de m'attribuer les permissions nécessaires ou de choisir un autre canal.",
                    ephemeral=True,
                )
                return

            # Vérifier si un enregistrement avec le guild_id existe déjà
            existing_record = db.guilds.find_one({"guild_id": interaction.guild.id})

            if existing_record:
                # Mettre à jour l'enregistrement existant
                db.guilds.update_one(
                    {"guild_id": interaction.guild.id},
                    {
                        "$set": {
                            "notifications_channel_id": interaction.channel_id,
                        }
                    },
                )
                logger.info(
                    f"Canal de notifications mis à jour pour le serveur '{interaction.guild.name}'"
                )
            else:
                # Ajouter un nouvel enregistrement
                new_record = {
                    "guild_id": interaction.guild.id,
                    "notifications_channel_id": interaction.channel_id,
                }
                db.guilds.insert_one(new_record)
                logger.info(
                    f"Nouvelle configuration ajoutée pour le serveur {interaction.guild.name}."
                )

            await interaction.response.send_message(
                f"Canal défini sur {interaction.channel.mention}. Les notifications du site seront postées ici.",
                ephemeral=True,
            )
        except:
            await interaction.response.send_message(
                f"Désolé, une erreur est survenue. Si cette erreur persiste, merci de contacter le créateur du bot",
                ephemeral=True,
            )

    logger.info("Lancement du bot...")
    bot.run(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    logger = logging.getLogger()

    stream_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    discord_format = logging.Formatter("%(message)s")

    discord_handler = DiscordHandler("PSTHC Logs", settings.LOGS_WEBHOOK_URL)

    discord_handler.setFormatter(discord_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_format)

    # Add the handlers to the Logger
    logger.addHandler(discord_handler)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

    run()
