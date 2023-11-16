import logging

import certifi
import discord
from discord.ext import commands
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import settings
from psthc_bot import PsthcBot


def run():
    # SSL certifcate
    ca = certifi.where()

    # Create a new client and connect to the server
    client = MongoClient(settings.DB_URI, server_api=ServerApi("1"), tlsCAFile=ca)

    # Send a ping to confirm a successful connection
    try:
        client.admin.command("ping")
        print("Connecté avec succès à MongoDB!")
    except Exception as e:
        print(e)
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
        name="setchannel",
        description="Défini le canal où poster les notifications PSTHC",
    )
    @commands.has_permissions(administrator=True)
    async def set_channel(interaction: discord.Interaction):
        try:
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
                logging.info(
                    f"Canal de notifications mis à jour pour le serveur {interaction.guild.name}"
                )
            else:
                # Ajouter un nouvel enregistrement
                new_record = {
                    "guild_id": interaction.guild.id,
                    "notifications_channel_id": interaction.channel_id,
                }
                db.guilds.insert_one(new_record)
                logging.info(
                    f"Nouvelle configuration ajoutée pour le serveur {interaction.guild.name}."
                )

            await interaction.response.send_message(
                f"Canal défini sur {interaction.channel.mention}", ephemeral=True
            )
        except:
            await interaction.response.send_message(
                f"Une erreur est survenue, veuillez réessayer...", ephemeral=True
            )

    print("Lancement du bot...")
    bot.run(settings.DISCORD_TOKEN, root_logger=True)


if __name__ == "__main__":
    run()
