"""This is the module that handles watching the actual Blizzard CDN."""

import discord
import logging
import httpx
import time
import json
import sys
import os

from discord import ui
from discord.ext import bridge, commands, tasks

START_LOOPS = True
DEBUG = False

FETCH_INTERVAL = 5

logger = logging.getLogger("discord.cdnwatcher")

class CDNUi(ui.View):
    def __init__(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext=None, 
                watcher=None, utility=False):
        super().__init__()
        self.watcher = watcher
        self.ctx = ctx
        self.utility = utility
        self.guild_id = self.ctx.guild_id

        if not self.utility:
            self.create_select_menu()

    def create_select_menu(self):
        placeholder = "Edit watchlist..."
        min_values = 0
        max_values = len(self.watcher.PRODUCTS)
        options = []
        disabled = False

        for branch, name in self.watcher.PRODUCTS.items():
            default = branch in self.watcher.watchlist[str(self.guild_id)]

            option = discord.SelectOption(label=name, value=branch, default=default)
            options.append(option)

        branch_select_menu = ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
        )
        self.branch_menu = branch_select_menu

        async def update_watchlist(interaction: discord.Interaction):
            selected_branches = branch_select_menu.values

            for value in self.watcher.PRODUCTS.keys():
                if value in selected_branches and value not in self.watcher.watchlist[str(self.guild_id)]:
                    self.watcher.add_to_watchlist(value)
                elif value in self.watcher.watchlist[str(self.guild_id)] and value not in selected_branches:
                    self.watcher.remove_from_watchlist(value)

            await interaction.response.defer()

            return True

        branch_select_menu.callback = update_watchlist
        self.add_item(branch_select_menu)


class CDNWatcher():
    SELF_PATH = os.path.dirname(os.path.realpath(__file__))
    CDN_URL = "http://us.patch.battle.net:1119/"
    PRODUCTS = {
        "wow": "Retail",
        "wowt": "Retail PTR",
        "wow_beta": "Beta",
        "wow_classic": "WotLK Classic",
        "wow_classic_ptr": "WotLK Classic PTR",
        "wow_classic_beta": "Classic Beta",
        "wow_classic_era": "Classic Era",
        "wow_classic_era_ptr": "Classic Era PTR",
        "wowz": "Submission",
        "wowlivetest": "Live Test",
        #"wowdev": "Internal"
    }
    PLATFORM = sys.platform
    
    def __init__(self):
        self.cache_path = os.path.join(self.SELF_PATH, "cache")
        self.data_path = os.path.join(self.cache_path, "cdn.json")

        load_watchlist = True

        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
            self.init_json()
        
        if load_watchlist:
            self.watchlist, self.channels = self.load_watchlist()
            self.save_watchlist()
        else:
            self.watchlist = ["wow", "wowt", "wow_beta"]
            self.save_watchlist()

    def init_json(self):
        """Populates the `cdn.json` file with default values if it does not exist."""
        with open(self.data_path, "w") as file:
            template = {
                "buildInfo": {},
                "watchlist": {857764832542851092: ["wow", "wowt", "wow_beta"]},
                "last_updated_by": self.PLATFORM,
                "last_updated_at": time.time()
            }

            json.dump(template, file, indent=4)

    def init_watchlist(self, key:int):
        """Creates the watchlist with default values."""
        self.add_to_watchlist("wow", key)

    def add_to_watchlist(self, branch:str, guild_id:int):
        """Adds a specific `branch` to the watchlist for guild `guild_id`."""
        if branch not in self.PRODUCTS.keys():
            return "Branch is not a valid product"
        else:
            if guild_id in self.watchlist.keys():
                if branch in self.watchlist[guild_id]:
                    return "Branch is already on the watchlist"
                else:
                    self.watchlist[guild_id].append(branch)
                    self.save_watchlist()
                    return True
            else:
                self.watchlist[guild_id] = [branch]
                self.save_watchlist()
                return True
    
    def remove_from_watchlist(self, branch:str, guild_id:int):
        """Removes specified `branch` from watchlist for guild `guild_id`."""
        if guild_id in self.watchlist.keys():
            if branch not in self.watchlist[guild_id]:
                raise ValueError("Argument 'branch' is not on the watchlist.")
            else:
                self.watchlist.remove(branch)
                self.save_watchlist()
        else:
            return False

    def load_watchlist(self):
        """Loads the watchlist from the `cdn.json` file."""
        logger.debug("Loading existing watchlist from file...")
        with open(self.data_path, "r") as file:
            file = json.load(file)
            if not "last_updated_by" in file:
                file["last_updated_by"] = self.PLATFORM

            if not "last_updated_at" in file:
                file["last_updated_at"] = time.time()

            if not "channels" in file:
                file["channels"] = {}

            return file["watchlist"], file["channels"]

    def save_watchlist(self):
        """Saves the watchlist to the `cdn.json` file."""
        logger.info("Saving configuration...")
        
        with open(self.data_path, "r+") as file:
            file_json = json.load(file)
            file_json["watchlist"] = self.watchlist
            file_json["channels"] = self.channels
            file_json["last_updated_by"] = self.PLATFORM
            file_json["last_updated_at"] = time.time()

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def set_channel(self, channel_id:int, guild_id:int):
        """Sets the notification channel to `channel_id` for the guild `guild_id`."""
        logger.info(f"Setting notification channel for {guild_id} to {channel_id}.")
        self.channels[str(guild_id)] = channel_id
        self.save_watchlist()

    def get_channel(self, guild_id:int):
        """Returns the `channel_id` for the notification channel of guild `guild_id`."""
        logger.info(f"Getting notification channel for {guild_id}.")
        if str(guild_id) in self.channels.keys():
            return self.channels[str(guild_id)]
        else:
            return False

    def compare_builds(self, branch:str, newBuild:dict) -> bool:
        """
        Compares two build strings.

        Returns `True` if the build is new, else `False`.
        """
        with open(self.data_path, "r") as file:
            file_json = json.load(file)

            if file_json["last_updated_by"] != self.PLATFORM and (time.time() - file_json["last_updated_at"]) < (FETCH_INTERVAL* 60):
                logger.info("Skipping build comparison, data is outdated")
                return False

            if branch in file_json["buildInfo"]:
                if file_json["buildInfo"][branch] != newBuild:
                    return True
                else:
                    return False
            else:
                file_json["buildInfo"][branch] = newBuild
                return True

    def save_build_data(self, branch:str, data:dict):
        """Saves new build data to the `cdn.json` file."""
        with open(self.data_path, "r+") as file:
            file_json = json.load(file)
            file_json["buildInfo"][branch] = data

            file.seek(0)
            json.dump(file_json, file, indent=4)
            file.truncate()

    def load_build_data(self, branch:str):
        """Loads existing build data from the `cdn.json` file."""
        with open(self.data_path, "r") as file:
            file_json = json.load(file)
            if branch in file_json["buildInfo"]:
                return file_json["buildInfo"][branch]
            else:
                file_json["buildInfo"][branch] = {
                    "region": "us",
                    "build": "",
                    "build_text": "untracked"
                }
                return False

    async def fetch_cdn(self):
        """This is a disaster."""
        logger.debug("Fetching CDN data...")
        async with httpx.AsyncClient() as client:
            new_data = []
            for branch in self.PRODUCTS:
                try:
                    logger.debug(f"Grabbing data for branch: {branch}")
                    url = self.CDN_URL + branch + "/versions"

                    res = await client.get(url, timeout=20)
                    logger.debug(f"Parsing CDN response")
                    data = self.parse_response(branch, res.text)

                    if data:
                        logger.debug(f"Comparing build data for {branch}")
                        is_new = self.compare_builds(branch, data)

                        if is_new:
                            output_data = data.copy()

                            old_data = self.load_build_data(branch)

                            if old_data:
                                output_data["old"] = old_data
                            
                            output_data["branch"] = branch
                            new_data.append(output_data)

                        logger.debug(f"Saving build data for {branch}")
                        self.save_build_data(branch, data)
                    else:
                        continue
                except Exception as exc:
                    logger.error(f"Timeout error during CDN check for {branch}")
                    return exc

            return new_data

    def parse_response(self, branch:str, response:str):
        """Parses the API response and attempts to return the new data."""
        try:
            data = response.split("\n")
            if len(data) < 3:
                return False
            data = data[2].split("|")
            region = data[0]
            build_number = data[4]
            build_text = data[5].replace(build_number, "")[:-1]

            output = {
                "region": region,
                "build": build_number,
                "build_text": build_text
            }

            return output
        except Exception as exc:
            logger.error(f"Encountered an error parsing API response for branch: {branch}.")
            logger.error(exc)

            return False


class CDNCogWatcher(commands.Cog):
    """This is the actual Cog that gets added to the Discord bot."""
    def __init__(self, bot:bridge.Bot):
        self.bot = bot
        self.cdn_watcher = CDNWatcher()
        self.last_update = 0
        self.last_update_formatted = 0

        if START_LOOPS:
            self.cdn_auto_refresh.add_exception_type(httpx.ConnectTimeout)
            self.cdn_auto_refresh.start()

    async def notify_owner_of_exception(self, error):
        """This is supposed to notify the owner of an error, but doesn't work."""
        owner = await self.bot.fetch_user(self.bot.owner_id)
        chan = await owner.create_dm()

        message = f"I've encountered an error! Help!\n{error}"

        await chan.send(message)

    def get_date(self, relative=False):
        """Returns a formatted timestamp for use in Discord embeds or messages."""
        current_time = int(time.time())
        if relative:
            return f"<t:{current_time}:R>"
        else:
            return f"<t:{current_time}:f>"

    def build_embed(self, data:dict, guild_id:int):
        """This builds a notification embed with the given data."""
        embed = discord.Embed(
                color=discord.Color.blue(),
                title="wow.tools builds page",
                description=f"{self.get_date()} **|** {self.get_date(relative=True)}",
                url="https://wow.tools/builds/"
            )

        embed.set_author(
                name="Blizzard CDN Update",
                icon_url="https://bnetcmsus-a.akamaihd.net/cms/gallery/D2TTHKAPW9BH1534981363136.png"
            )

        embed.set_footer(text="Data provided by the prestigious Algalon 2.0.")
        
        value_string = ""

        for ver in data:
            branch = ver["branch"]

            if str(guild_id) not in self.cdn_watcher.watchlist.keys():
                logger.error("Guild (%s) not on watchlist, adding default entry [\"wow\"].", guild_id)
                self.cdn_watcher.init_watchlist(guild_id)
                return False

            if branch not in self.cdn_watcher.watchlist[str(guild_id)]:
                continue

            if "old" in ver:
                build_text_old = ver["old"]["build_text"]
                build_old = ver["old"]["build"]
            else:
                build_text_old = "untracked"
                build_old = "0.0.0"
            
            build_text = ver["build_text"]
            build = ver["build"]

            public_name = self.cdn_watcher.PRODUCTS[branch]

            build_text = f"**{build_text}**" if build_text != build_text_old else build_text
            build = f"**{build}**" if build != build_old else build

            value_string += f'`{public_name} ({branch})`: {build_text_old}.{build_old} --> {build_text}.{build}\n'

        if value_string == "":
            return False

        embed.add_field(
            name="Branch Updates",
            value=value_string,
            inline=False
        )

        return embed

    async def distribute_embed(self):
        """This handles distributing the generated embeds to the various servers that should receive them."""
        logger.debug("Building CDN update embed")
        new_data = await self.cdn_watcher.fetch_cdn()

        if new_data and not DEBUG:
            if not type(new_data) == dict | bool:
                logger.error(new_data)
                self.notify_owner_of_exception(new_data)
                return False
            
            logger.info("New CDN data found! Creating posts...")

            for guild in self.bot.guilds:
                try:
                    if str(guild.id) in self.cdn_watcher.channels.keys():
                        cdn_channel = await guild.fetch_channel(self.cdn_watcher.channels[str(guild.id)])
                    else:
                        logger.error("Guild %s has not chosen a channel for notifications, skipping...", guild.id)
                except:
                    logger.error("Error fetching channel for guild %s.", guild.id)
                    continue
                embed = self.build_embed(new_data, guild.id)
                if embed:
                    await cdn_channel.send(embed=embed)

        else:
            if new_data and DEBUG:
                logger.info("New data found, but not creating posts in debug mode.")
                return
            logger.info("No CDN changes found.")

    @tasks.loop(minutes=FETCH_INTERVAL, reconnect=True)
    async def cdn_auto_refresh(self):
        """Forever problematic loop that handles auto-checking for CDN updates."""
        await self.bot.wait_until_ready()

        logger.info("Checking for CDN updates...")

        await self.distribute_embed()
            
        self.last_update = time.time()
        self.last_update_formatted = self.get_date(relative=True)

    async def cdn_refresh(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        new_data = await self.distribute_embed(True)

        if new_data:
            await ctx.interaction.response.send_message(embed=new_data)
        else:
            await ctx.interaction.response.send_message("No changes found.", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnaddtowatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_add_to_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext, branch:str):
        """Command for adding specific branches to the watchlist for your guild."""
        added = self.cdn_watcher.add_to_watchlist(branch, ctx.guild_id)
        if added != True:
            message = f"{added}\n\n**Valid branches:**\n```\n"

            for product, name in self.cdn_watcher.PRODUCTS.items():
                message += f"{product} : {name}\n"

            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
            return False
            
        await ctx.interaction.response.send_message(f"`{branch}` successfully added to watchlist.", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnremovefromwatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_remove_from_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext, branch:str):
        """Command for removing specific branches from the watchlist for you guild."""
        try:
            self.cdn_watcher.remove_from_watchlist(branch, ctx.guild_id)
        except ValueError:
            message = "Invalid branch argument, please try again.\n\n**Valid branches:**\n```\n"

            for product in self.cdn_watcher.watchlist:
                message += f"{product}\n"

            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
            return False
            
        await ctx.interaction.response.send_message(f"`{branch}` successfully removed from watchlist.", ephemeral=True, delete_after=300)
        
    @bridge.bridge_command(name="cdnwatchlist")
    @commands.has_permissions(administrator=True)
    async def cdn_watchlist(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        """Returns the entire watchlist for your guild."""
        message = "**These are the branches I'm currently observing:**\n```\n"

        if ctx.guild_id in self.cdn_watcher.watchlist.keys():
            for product in self.cdn_watcher.watchlist:
                message += f"{product}\n"
            
            message += "```"

            await ctx.interaction.response.send_message(message, ephemeral=True, delete_after=300)
        else:
            error_msg = "Your server does not have a watchlist, I'll create one for you with the Retail WoW branch as default, use `/cdnedit` to edit your new watchlist!"
            self.cdn_watcher.init_watchlist(str(ctx.guild_id))

            await ctx.interaction.response.send_message(error_msg, ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnedit")
    @commands.has_permissions(administrator=True)
    async def cdn_edit(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        """Returns a graphical editor for your guilds watchlist."""
        if ctx.guild_id not in self.cdn_watcher.watchlist.keys():
            error_msg = "Your server does not have a watchlist, I'll create one for you with the Retail WoW branch as default, use this command again to edit your new watchlist!"
            self.cdn_watcher.init_watchlist(str(ctx.guild_id))

            await ctx.interaction.response.send_message(error_msg, ephemeral=True, delete_after=300)
        else:
            view = CDNUi(ctx=ctx, watcher=self.cdn_watcher)
            message = "Edit the branches you are currently watching using the menu below.\nTo save your changes, just click out of the menu."

            await ctx.interaction.response.send_message(message, view=view, ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdnsetchannel")
    @commands.has_permissions(administrator=True)
    async def cdn_set_channel(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        """Sets the notification channel for your guild."""
        channel = ctx.channel_id
        guild = ctx.guild_id
        
        self.cdn_watcher.set_channel(channel, guild)

        await ctx.interaction.response.send_message("Channel successfully set!", ephemeral=True, delete_after=300)

    @bridge.bridge_command(name="cdngetchannel")
    @commands.has_permissions(administrator=True)
    async def cdn_get_channel(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        """Returns the current notification channel for your guild."""
        guild = ctx.guild_id

        channel = self.cdn_watcher.get_channel(guild)

        if channel:
            await ctx.interaction.response.send_message(f"This server's notification channel is set to <#{channel}>", ephemeral=True, delete_after=300)
        else:
            await ctx.interaction.response.send_message(f"This server does not have a notification channel set, try `/cdnsetchannel` to set your notification channel!", ephemeral=True, delete_after=300)
    
    @bridge.bridge_command(name="cdnlastupdate")
    async def cdn_last_update(self, ctx:bridge.BridgeApplicationContext | bridge.BridgeContext):
        """Returns the last time the bot checked for an update."""
        await ctx.interaction.response.send_message(f"Last update: {self.last_update_formatted}.", ephemeral=True, delete_after=300)
    


def setup(bot):
    bot.add_cog(CDNCogWatcher(bot))