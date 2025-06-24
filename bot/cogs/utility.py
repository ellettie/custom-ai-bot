import discord
from discord import app_commands
from discord.ext import commands

from .. import gemini
from ..config import Config

class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="info", description="Botの情報を確認")
    async def info(self, ctx: discord.Interaction):
        text = f"**チャットモデル**: {gemini.MODEL}\n**画像生成モデル**: {gemini.IMAGE_MODEL}"
        embed = discord.Embed(
            title=Config.EMBED_SET["info"]["title"],
            description=text,
            colour=Config.EMBED_SET["info"]["colour"],
        )
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar) # type: ignore
        embed.set_footer(text="developed by ellettie")
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="help", description="/コマンド一覧")
    async def help(self, ctx: discord.Interaction):
        embed = Config.HELP_EMBED.copy()
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar) # type: ignore
        embed.set_footer(text="developed by ellettie")
        await ctx.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))