import logging
import shutil
import urllib
from datetime import datetime

import discord
import yaml
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import os
from .. import helpers
import aiohttp
import imgurpython

imgur_client = None


class Archive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 1 * 60 * 60, BucketType.member)
    async def archive(self, ctx: commands.Context, url: str):
        # Prevents link embed on Discord
        if url.startswith("<") and url.endswith(">"):
            url = url[1:-1]

        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.startswith("www"):
            parsed.netloc = parsed.netloc[3:]

        if parsed.path.endswith("/"):
            parsed.path = parsed.path[:-1]

        url = urllib.parse.urlunparse(parsed)

        options = ("imgur.com",)
        options_list = ""
        for option in options:
            options_list += "- " + option + "\n"

        if parsed.netloc == "imgur.com":
            if parsed.path.startswith("/album/") or parsed.path.startswith("/a/"):
                await archive_imgur(ctx, url)
            else:
                await ctx.send("That doesn't seem like an imgur album.")
        else:
            await ctx.send(
                (
                    f'The domain "{parsed.netloc}" is not currently available for '
                    f"archiving. Currently there are the following domains:"
                    f"\n{options_list}"
                )
            )

    @commands.command()
    @commands.cooldown(1, 1 * 60 * 5, BucketType.member)
    async def wayback(self, ctx, url):
        loading = helpers.Loading(ctx, ctx.message)

        async with loading:
            wayback_url = await get_wayback()

            embed = discord.Embed(title="Wayback Archive", description=wayback_url)
            await ctx.send(embed=embed)


async def archive_imgur(ctx, url):
    parsed = urllib.parse.urlparse(url)
    if parsed.path.startswith("/album/"):
        album_id = parsed.path.split("/album/", 1)[1]
    else:
        album_id = parsed.path.split("/a/", 1)[1]

    try:
        album = imgur_client.get_album(album_id)
        images = album.images
        if album.images is None:
            await ctx.send("Oops I couldn't get any images...")
            return
    except Exception:
        await ctx.send("That doesn't seem to be a valid album.")
        return

    # Does the file already exist?
    try:
        with open(f"downloads/{album_id}.zip", "r") as f:
            await send_archive(ctx, album)
            return
    except OSError:
        pass

    # Someone else may already be downloading the image.
    try:
        os.mkdir(f"downloads/{album_id}")
    except OSError:
        await ctx.send("Oops, I couldn't start downloading! Contact my owner for help.")
        return

    wait_message = await ctx.send(
        (
            f"Downloading {len(images)} images from album `{album_id}`... "
            "this may take a while."
        )
    )

    loading = helpers.Loading(ctx.bot, ctx.message)

    async with loading:
        chunk_size = 65536
        async with aiohttp.ClientSession() as session:
            for i, image in enumerate(images):
                if image["is_ad"]:
                    continue

                logging.info(f"Downloading image {image['link']}")

                if image["description"] is not None and image["description"] != "":
                    with open(
                        f"downloads/{album_id}/{i}_{image['id']}_description.txt",
                        "w+",
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

        await wait_message.delete()
        await send_archive(ctx, album)


async def send_archive(ctx, album):
    # wayback = await get_wayback(album.link)

    zip_file = f"{album.id}.zip"
    zip_path = f"downloads/{album.id}.zip"

    embed = discord.Embed(title=f"Archive of Imgur Album", colour=0x7289DA)

    embed.add_field(name="Album Link", value=f"[{album.title}]({album.link})")
    # embed.add_field(name="Wayback Archive", value=wayback.url)
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
        await ctx.send("Could not send file, probably was too large.")
        raise exception


async def get_wayback(url):
    return


def setup(bot):
    global imgur_client

    logging.basicConfig(level=logging.INFO)

    with open("secrets.yml", "r") as f:
        secrets = yaml.safe_load(f)

    imgur_client = imgurpython.ImgurClient(
        secrets["imgur_client_id"], secrets["imgur_client_secret"]
    )

    bot.add_cog(Archive(bot))
