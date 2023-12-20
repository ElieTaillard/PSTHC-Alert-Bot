import logging

import certifi
import coloredlogs
import discord
from discord.ext import commands
from discord_logging.handler import DiscordHandler
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import settings
from psthc_bot import PsthcBot

logger = logging.getLogger()


def setup_logger():
    """
    Set up the logger with a Discord handler and colored console output.
    """
    # Define format for logs
    discord_format = logging.Formatter("%(message)s")

    discord_handler = DiscordHandler("PSTHC Logs", settings.LOGS_WEBHOOK_URL)
    discord_handler.setFormatter(discord_format)

    coloredlogs.install(level=logging.INFO, logger=logger)

    # Add the handlers to the Logger
    logger.addHandler(discord_handler)
    logger.setLevel(logging.INFO)


def run():
    """
    Main function to set up and run the PSTHC bot.
    """
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
        color=16777215,
        db=db,
    )

    @bot.tree.command(
        name="psthc",
        description="Défini le canal actuel comme canal de notifications",
    )
    @commands.has_permissions(administrator=True)
    async def set_channel(interaction: discord.Interaction):
        """
        Command to set the current channel as the notifications channel.

        Parameters:
            interaction (discord.Interaction): The interaction object.
        """
        try:
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            missing_permissions = []

            if not permissions.send_messages:
                missing_permissions.append("Envoyer des messages")

            if not permissions.embed_links:
                missing_permissions.append("Intégrer des liens")

            if not permissions.attach_files:
                missing_permissions.append("Joindre des fichiers")

            # Check for missing permissions
            if missing_permissions:
                styled_missing_permissions = ", ".join(
                    ["**" + element + "**" for element in missing_permissions]
                )
                await interaction.response.send_message(
                    f"❌ Il me manque les permissions suivantes pour ce canal : {styled_missing_permissions}. \nMerci de m'attribuer les permissions nécessaires ou de choisir un autre canal.",
                    ephemeral=True,
                )
                return

            # Check if a record with the guild_id already exists
            existing_record = db.guilds.find_one({"guild_id": interaction.guild.id})

            if existing_record:
                # Update the existing record
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
                # Add a new record
                new_record = {
                    "guild_id": interaction.guild.id,
                    "notifications_channel_id": interaction.channel_id,
                }
                db.guilds.insert_one(new_record)
                logger.info(
                    f"Nouvelle configuration ajoutée pour le serveur {interaction.guild.name}."
                )

            await interaction.response.send_message(
                f"✅ Canal défini sur {interaction.channel.mention}. Les notifications du site seront postées ici.",
                ephemeral=True,
            )
        except:
            await interaction.response.send_message(
                f"❌ Désolé, une erreur est survenue. Si cette erreur persiste, merci de contacter le créateur du bot",
                ephemeral=True,
            )

    logger.info("Lancement du bot...")
    bot.run(settings.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    setup_logger()
    run()
