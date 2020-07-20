import asyncio
import logging
from typing import List

from discord import Client, Embed, Colour, HTTPException
from humanize import naturalsize

from miui_updates_tracker.common.constants import website
from miui_updates_tracker.common.database.database import get_full_name, get_device_name, get_incremental
from miui_updates_tracker.common.database.models.update import Update

logger = logging.getLogger(__name__)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)
logging.getLogger('discord.gateway').setLevel(logging.ERROR)

class DiscordBot(Client):
    """
    This class implements discord bot that is used for sending updates to discord channels in Xiaomi server
    """

    def __init__(self, token):
        """
        Discord Bot class constructor
        :param token: Discord Bot API access token
        :param chat: Telegram chat username or id that will be used to send updates to
        """
        super().__init__(loop=asyncio.get_running_loop())
        self.token = token
        self.updates = None
        self.channels = None

    async def send_message(self, update: Update):
        """
        Generates and sends a Discord message
        """
        short_codename = update.codename.split('_')[0]
        message = f"**Device**: {get_full_name(update.codename)}\n" \
                  f"**Codename**: `{short_codename}`\n" \
                  f"**Version**: `{update.version} | {update.android}`\n" \
                  f"**Size**: {naturalsize(update.size)}\n"
        if update.md5:
            message += f"**MD5**: `{update.md5}`\n"
        if update.changelog != "Bug fixes and system optimizations.":
            changelog = f"**Changelog**:\n`{update.changelog}`"
            message += changelog[:2000 - len(message)]
        embed = Embed(title=f"New {update.branch} {update.method} update available!",
                      color=Colour.orange(), description=message)
        embed.add_field(name="Full ROM", value=f'[Download]({update.link})', inline=True)
        if update.method == "Recovery":
            incremental = get_incremental(update.version)
            if incremental:
                embed.add_field(name="Incremental", value=f'[Download]({incremental.link})', inline=True)
        embed.add_field(name="Latest", value=f'[Here]({website}/miui/{short_codename})', inline=True)
        embed.add_field(name="Archive", value=f'[Here]({website}/archive/miui/{short_codename})', inline=True)
        device = get_device_name(update.codename).lower()
        for name, channel in self.channels.items():
            if device.startswith(name):
                await channel.send(embed=embed)
                return
        await self.channels['other_phones'].send(embed=embed)

    async def on_ready(self):
        """Prepare"""
        self.channels = {x.name.replace('_series', '').replace('_', ' '): x
                         for x in sorted(self.get_all_channels(), key=lambda c: c.name)
                         if x.category_id == 699991467560534136}
        for update in self.updates:
            try:
                await self.send_message(update)
            except (KeyError, HTTPException):
                continue
        await self.logout()

    async def post_updates(self, new_updates: List[Update]):
        """
        Send updates to Discord channels
        :param new_updates: a list of updates
        """
        self.updates = new_updates
        await self.start(self.token)
