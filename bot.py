import discord
from discord.ext import commands
import feedparser
import json
from dotenv import load_dotenv
import os
from discord import app_commands

load_dotenv()

# Configuration
RSS_FEED_URL = "URL_DU_FLUX_RSS"
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=".psthc", status=discord.Status.online, intents=intents
)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} est en cours d'execution")


@bot.event
async def on_guild_join(guild):
    welcome_message = (
        "Salut ! Je suis le bot PSTHC. Pour commencer, veuillez utiliser la commande suivante "
        "dans le canal où vous souhaitez que je poste les notifications :\n"
        "`/setchannel`"
    )
    await guild.text_channels[0].send(welcome_message)


@bot.tree.command(
    name="setchannel", description="Défini le canal où poster les notifications PSTHC"
)
@commands.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction):
    try:
        # Enregistre l'ID du canal pour les futurs messages
        with open("channel.json", "r") as jsonFile:
            data = json.load(jsonFile)

        data["channel_id"] = interaction.channel.id

        with open("channel.json", "w") as jsonFile:
            json.dump(data, jsonFile)

        await interaction.response.send_message(
            f"Canal défini sur {interaction.channel.mention}"
        )
    except:
        await interaction.response.send_message(
            f"Une erreur est survenue, veuillez réessayer..."
        )


bot.run(TOKEN)
