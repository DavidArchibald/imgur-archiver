import asyncio
import logging
import math
import os
import platform
import shutil
import traceback
import urllib.parse
from datetime import datetime

import aiohttp
import discord
import yaml
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

import imgurpython

imgur_client = None
bot = commands.Bot(">")


def main():
    global imgur_client
    with open("secrets.yml", "r") as f:
        secrets = yaml.safe_load(f)

    imgur_client = imgurpython.ImgurClient(
        secrets["imgur_client_id"], secrets["imgur_client_secret"]
    )

    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.run(secrets["discord_token"]))


@bot.event
async def on_ready():
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


@bot.command()
@commands.cooldown(1, 1 * 60 * 60, BucketType.member)
async def archive(ctx: commands.Context, url: str):
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1]

    parsed = urllib.parse.urlparse(url)

    if parsed.netloc not in ("www.imgur.com", "imgur.com") or (
        parsed.path.startswith("/album/") is False
        and parsed.path.startswith("/a/") is False
    ):
        await ctx.send("Sorry only Imgur albums are supported currently...")
        return

    if parsed.path.startswith("/album/"):
        album_id = parsed.path.split("/album/", 1)[1]
    else:
        album_id = parsed.path.split("/a/", 1)[1]

    try:
        with open(f"downloads/{album_id}.zip", "r") as f:
            await send_archive(ctx, archive)
            return
    except OSError:
        pass

    try:
        album = imgur_client.get_album(album_id)
        images = album.images
        if album.images is None:
            await ctx.send("Oops I couldn't get any images...")
            return
            # images = imgur_client.get_album_images(album_id)
    except Exception:
        await ctx.send("That doesn't seem to be a valid album.")
        return

    # print(vars(album))

    # already_downloaded = False
    try:
        os.mkdir(f"downloads/{album_id}")
    # except os.FileExistsError:
    #     already_downloaded = True
    except OSError:
        await ctx.send("Oops, I couldn't start downloading! Contact my owner for help.")
        return

    # if already_downloaded:
    #     await ctx.send(
    #         "This album has already been downloaded or may be in progress, the dev"
    #         "hasn't written that edge case yet... :sweatsmile:. "
    #         "Here is the cache of its contents:"
    #     )
    # else:
    wait_message = await ctx.send(
        (
            f"Downloading {len(images)} images from album `{album_id}`... "
            "this may take a while."
        )
    )

    loading = bot.get_emoji(478317750817914910)
    x = bot.get_emoji(475032169086058496)
    check = bot.get_emoji(475029940639891467)

    await ctx.message.add_reaction(loading)

    chunk_size = 65536
    async with aiohttp.ClientSession() as session:
        for i, image in enumerate(images):
            if image["is_ad"]:
                continue

            logging.info(f"Downloading image {image['link']}")

            if image["description"] is not None and image["description"] != "":
                with open(
                    f"downloads/{album_id}/{i}_{image['id']}_description.txt", "w+"
                ) as f:
                    f.write(image["description"])

            extension = image["type"].split("image/", 1)[1]
            async with session.get(image["link"]) as response:
                with open(
                    f"downloads/{album_id}/{i}_{image['id']}.{extension}", "wb"
                ) as f:
                    while True:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)

    album_folder = f"downloads/{album.id}"
    shutil.make_archive(album_folder, "zip", album_folder)
    try:
        shutil.rmtree(album_folder)
    except OSError:
        pass

    try:
        await send_archive(ctx, album)
    except discord.HTTPException as exception:
        print_traceback("Send archive: ", exception)
        try:
            await ctx.message.remove_reaction(loading, ctx.bot.user)
            await ctx.message.add_reaction(x)
        except discord.HTTPException as exception:
            print_traceback("Add x emoji: ", exception)
            pass

        try:
            await wait_message.edit(
                message="Could not send message, perhaps the album is too large?"
            )
        except discord.HTTPException as exception:
            print_traceback("Edit to error: ", exception)
            pass
    else:
        await wait_message.delete()
        try:
            await ctx.message.remove_reaction(loading, ctx.bot.user)
            await ctx.message.add_reaction(check)
        except discord.HTTPException:
            pass

    # try:
    #     shutil.rmtree(album_folder)
    # except OSError:
    #     pass


async def send_archive(ctx, album):
    zip_file = f"{album.id}.zip"
    zip_path = f"downloads/{album.id}.zip"

    embed = discord.Embed(title=f"Archive of Imgur Album", colour=0x7289DA)

    embed.add_field(name="Album Link", value=f"[{album.title}]({album.link})")
    # embed.add_field(name="Archive", value="")
    embed.add_field(name="Poster", value=album.account_url)
    embed.add_field(name="Posted", value=datetime.utcfromtimestamp(album.datetime))
    embed.add_field(name="Description", value=album.description)
    embed.add_field(name="Views", value=album.views)
    embed.add_field(name="Images", value=len(album.images))
    # embed.add_field(name="Thumbnail", value="")

    embed = await ctx.send(embed=embed)
    try:
        await ctx.send(file=discord.File(zip_path, filename=zip_file))
    except discord.HTTPException as exception:
        await ctx.remove(embed)
        raise exception


@archive.error
async def archive_error(ctx: commands.Context, error):
    if isinstance(error, commands.errors.CommandOnCooldown):
        print(error)
        print(error.retry_after)
        await ctx.send(f"You are on cooldown for {humanify(error.retry_after)}")
        return

    print_traceback(error)
    await ctx.send(
        "Hmm, something went wrong, are you sure you invoked the command correctly?"
    )


def humanify(seconds):
    seconds = math.ceil(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    items = []
    if hours != 0:
        items.append(f"{hours} hours")
    if minutes != 0:
        items.append(f"{minutes} minutes")
    if seconds != 0:
        items.append(f"{seconds} seconds")

    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} and {items[1]}"
    elif len(items) == 3:
        items[-1] = "and " + items[-1]
        return ", ".join(items)


def print_traceback(prefix, error=None):
    if error is None:
        error = prefix
        prefix = None

    if prefix is None:
        prefix = ""

    logging.warn(
        prefix
        + "\n".join(traceback.format_exception(type(error), error, error.__traceback__))
    )


if __name__ == "__main__":
    main()
