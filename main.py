import json

import discord
from discord.ext import commands

import settings

logger = settings.logging.getLogger("bot")


def run():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(
        command_prefix=".psthc", status=discord.Status.online, intents=intents
    )

    @bot.event
    async def on_ready():
        logger.info(f"User:{bot.user} (ID:{bot.user.id})")
        await bot.tree.sync()

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

    bot.run(settings.TOKEN, root_logger=True)


if __name__ == "__main__":
    run()
