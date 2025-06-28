import discord
from discord.ext import commands
import os
import logging
import time
from .config import Config
from . import myutils

# --- ロガー取得 (ハンドラは run.py で設定) ---
logger = logging.getLogger(__name__)

# --- Botクラスの定義 ---
class CUSTOM_AI_BOT(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        member_cache_flags = discord.MemberCacheFlags.none()
        super().__init__(
            command_prefix=None,  # type: ignore
            intents=intents,
            member_cache_flags=member_cache_flags,
            max_messages=None
        )
        self.start_ts = time.perf_counter()
        self.guild_id = Config.GUILD_ID

    async def setup_hook(self):
        # cogsディレクトリからCogをロード
        for filename in os.listdir('./bot/cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'bot.cogs.{filename[:-3]}')
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.exception(f"Failed to load cog {filename}: {e}")

        # コマンドを特定のギルドに同期
        guild = discord.Object(id=self.guild_id)
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {self.guild_id}")
        except Exception as e:
            logger.exception(f"Failed to sync commands when starting\n{e}")

    async def on_guild_join(self, guild: discord.Guild):
        # 許可されていないギルドからは退出
        if guild.id != self.guild_id:
            logger.warning(f"Leaved from unauthorized guild {guild.id} ({guild.name})")
            await guild.leave()
        else:
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"bot joined to {guild.id}")
            except Exception as e:
                logger.exception(f"failed to add slash commands when joining to {guild.id}\n{e}")

bot = CUSTOM_AI_BOT()

@bot.event
async def on_ready() -> None:
    myutils.print_banner(bot, bot.start_ts)
    print("Bot is ready!")

def run(level=logging.WARNING):
    # ログハンドラをrun.pyで一元管理するため、discord.pyのデフォルトハンドラを無効化
    bot.run(Config.TOKEN, log_handler=None, log_level=level)  # type: ignore