import discord

from .cache import CDNCache
from discord.ext import bridge


class CDNUi(discord.ui.View):
    def __init__(
        self,
        ctx: bridge.BridgeApplicationContext,
        watcher: CDNCache,
        utility=False,
    ):
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
        max_values = len(self.watcher.CONFIG.PRODUCTS)
        options = []
        disabled = False

        for branch, name in self.watcher.CONFIG.PRODUCTS.items():
            default = branch in self.watcher.watchlist[str(self.guild_id)]

            option = discord.SelectOption(label=name, value=branch, default=default)
            options.append(option)

        branch_select_menu = discord.ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            options=options,
            disabled=disabled,
        )
        self.branch_menu = branch_select_menu

        async def update_watchlist(interaction: discord.Interaction):
            selected_branches = branch_select_menu.values

            for value in self.watcher.CONFIG.PRODUCTS.keys():
                if (
                    value in selected_branches
                    and value not in self.watcher.watchlist[str(self.guild_id)]
                ):
                    self.watcher.add_to_watchlist(value, self.guild_id)
                elif (
                    value in self.watcher.watchlist[str(self.guild_id)]
                    and value not in selected_branches
                ):
                    self.watcher.remove_from_watchlist(value, self.guild_id)

            await interaction.response.defer()

            return True

        branch_select_menu.callback = update_watchlist
        self.add_item(branch_select_menu)
