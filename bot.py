import os
import sys
import cogs
import logging
import discord

from dotenv import load_dotenv
from discord.ext import bridge, commands
from logging.handlers import TimedRotatingFileHandler

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNERID = os.getenv("OWNERID")

DIR = os.path.dirname(os.path.realpath(__file__))

LOG_DIR = os.path.join(DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, f"bot_{cogs.get_timestamp()}.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
log_format = logging.Formatter("[%(asctime)s]:[%(levelname)s:%(name)s]: %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.DEBUG)

logger.addHandler(console_handler)  # adds console handler to our logger

file_handler = TimedRotatingFileHandler(
    filename=LOG_FILE, encoding="utf-8", when="midnight", backupCount=30
)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(file_handler)  # adds filehandler to our logger

logger.info(
    f"Using Python version {sys.version}",
)
logger.info(f"Using PyCord version {discord.__version__}")
cogs.log_start()

# This subclasses the default help command to provide our bot with a prettier command.
class CDNBotHelpCommand(commands.HelpCommand):
    def get_command_signature(self, command):
        return "%s%s %s" % (
            self.context.clean_prefix,
            command.qualified_name,
            command.signature,
        )

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blue())

        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)

            if command_signatures := [self.get_command_signature(c) for c in filtered]:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(
                    name=cog_name, value="\n".join(command_signatures), inline=False
                )

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=self.get_command_signature(command), color=discord.Color.random()
        )

        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        await self.get_destination().send(embed=embed)

    async def send_help_embed(self, title, description, commands):
        embed = discord.Embed(
            title=title, description=description or "No help found..."
        )

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=command.help or "No help found...",
                )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        title = self.get_command_signature(group)
        await self.send_help_embed(title, group.help, group.commands)

    async def send_cog_help(self, cog):
        title = cog.qualified_name or "No"
        await self.send_help_embed(
            f"{title} Category", cog.description, cog.get_commands()
        )


# The almighty Algalon himself
class CDNBot(bridge.Bot):
    """This is the almighty CDN bot, also known as Algalon. Inherits from `discord.ext.bridge.Bot`."""

    COGS_LIST = [
        "watcher",
    ]

    def __init__(self, command_prefix, help_command=None, **options):
        command_prefix = command_prefix or "!"
        help_command = help_command or commands.DefaultHelpCommand()

        super().__init__(
            command_prefix=command_prefix, help_command=help_command, **options
        )

        for cog in self.COGS_LIST:
            logger.info("Loading %s cog...", cog)
            try:
                self.load_extension(f"cogs.{cog}")
                logger.info("%s cog loaded!", cog)
            except Exception as exc:
                logger.error("Error loading cog %s", cog)
                logger.error(exc)

    async def on_ready(self):
        """This `async` function runs once when the bot is connected to Discord and ready to execute commands."""
        logger.info("%s has successfully connected to Discord!", self.user.name)


if __name__ == "__main__":
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Blizzard's CDN",
    )

    bot = CDNBot(
        command_prefix="!",
        help_command=CDNBotHelpCommand(),
        description="Algalon 2.0",
        intents=discord.Intents.default(),
        owner_id=OWNERID,
        status=discord.Status.online,
        activity=activity,
        auto_sync_commands=True,
    )
    bot.run(TOKEN)
