import asyncio
import logging
import platform

import discord
import yaml
from discord.ext import commands

from . import helpers

bot = commands.Bot(">")

cogs = ["archiver.cogs.archive"]


def main():
    logging.basicConfig(level=logging.INFO)

    for cog in cogs:
        bot.load_extension(cog)

    with open("secrets.yml", "r") as f:
        secrets = yaml.safe_load(f)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.run(secrets["discord_token"]))


@bot.event
async def on_ready():
    helpers.emojis.get_emojis(bot)
    servers = len(bot.guilds)
    users = len(set(bot.get_all_members()))
    plural = "s" if servers > 1 else ""

    logging.info(
        (
            "=====================\n"
            f"Logged in as {bot.user.name} (ID: {bot.user.id}). Connected to"
            f" {servers} server{plural} | Connected to {users} users.\n"
            f"--------------\n"
            f"Current Discord.py Version: {discord.__version__} | "
            f"Current Python Version: {platform.python_version()}\n"
            f"--------------\n"
            f"Use this link to invite me: "
            f"https://discordapp.com/oauth2/authorize?client_id={bot.user.id}"
            "&scope=bot&permissions=298048\n"
            f"====================="
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.send(f"You are on cooldown for {helpers.humanify(error.retry_after)}")
        return

    helpers.print_traceback(error)
    await ctx.send(
        "Hmm, something went wrong, and the dev is too lazy to add good "
        "error handling. So I can't really tell you what went wrong."
    )


if __name__ == "__main__":
    main()
