from . import emojis
import discord
import math
import traceback
import logging


class Loading:
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message

    async def start(self):
        await self._add_reaction(emojis.loading)

    async def fail(self):
        await self._remove_reaction(emojis.loading)
        await self._add_reaction(emojis.x)

    async def succeed(self):
        await self._remove_reaction(emojis.loading)
        await self._add_reaction(emojis.check)

    async def _add_reaction(self, emoji):
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def _remove_reaction(self, emoji):
        try:
            await self.message.remove_reaction(emoji, self.bot.user)
        except discord.HTTPException:
            pass

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            await self.fail()
        else:
            await self.succeed()


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
