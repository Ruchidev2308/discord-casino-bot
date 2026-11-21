import os
from dotenv import load_dotenv
load_dotenv()
import discord
from discord.ext import commands
import aiosqlite
TOKEN = os.getenv("DISCORD_TOKEN") #paste ur token here
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
class GambleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", intents=intents) #migth clash if any other bot in ur server user $
    async def setup_hook(self):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    guild_id INTEGER,
                    user_id INTEGER,
                    cash INTEGER DEFAULT 1000,
                    last_daily INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.commit()
        await self.load_extension("economy")
        await self.load_extension("gambling")
    async def on_ready(self):
        print(f"Casino Bot online as {self.user} (Prefix: $)")
bot = GambleBot()
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Only server admins can use that command.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down. Try again in **{error.retry_after:.1f}s**.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing argument. Check the command format.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid user or number.")
    else:
        print(f"Error: {error}")
bot.run(TOKEN)
