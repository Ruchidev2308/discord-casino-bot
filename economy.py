import discord
from discord.ext import commands
import aiosqlite
import random
import time
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def get_cash(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute("SELECT cash FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO users (guild_id, user_id, cash) VALUES (?, ?, 1000)", (guild_id, user_id))
                await db.commit()
                return 1000
            return row[0]
    @commands.command(name="setmoney", aliases=["setcash", "setbal"])
    @commands.has_permissions(administrator=True)
    async def set_money(self, ctx, member: discord.Member, amount: int):
        await self.get_cash(ctx.guild.id, member.id)
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE users SET cash = ? WHERE guild_id = ? AND user_id = ?", (amount, ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"Set **{member.display_name}**'s balance to **${amount:,}**.")
    @commands.command(name="addmoney", aliases=["addcash", "giveadmin"])
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx, member: discord.Member, amount: int):
        await self.get_cash(ctx.guild.id, member.id)
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE users SET cash = cash + ? WHERE guild_id = ? AND user_id = ?", (amount, ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"Added **${amount:,}** to **{member.display_name}**.")
    @commands.command(name="removemoney", aliases=["removecash"])
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx, member: discord.Member, amount: int):
        await self.get_cash(ctx.guild.id, member.id)
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE users SET cash = MAX(0, cash - ?) WHERE guild_id = ? AND user_id = ?", (amount, ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"Removed **${amount:,}** from **{member.display_name}**.")
    @commands.command(name="cash", aliases=["bal", "balance", "money"])
    async def cash(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal = await self.get_cash(ctx.guild.id, member.id)
        await ctx.send(f"**{member.display_name}**, you currently have **${bal:,}**!")
    @commands.command(name="daily")
    async def daily(self, ctx):
        await self.get_cash(ctx.guild.id, ctx.author.id)
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute("SELECT last_daily FROM users WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id))
            last_daily = (await cursor.fetchone())[0]

            now = int(time.time())
            if now - last_daily < 86400:
                rem = 86400 - (now - last_daily)
                h, m = divmod(rem // 60, 60)
                return await ctx.send(f"You already claimed your daily cash. Come back in **{h}h {m}m**.")

            reward = random.randint(2500, 5000)
            await db.execute("UPDATE users SET cash = cash + ?, last_daily = ? WHERE guild_id = ? AND user_id = ?", (reward, now, ctx.guild.id, ctx.author.id))
            await db.commit()
        await ctx.send(f"You claimed your daily **${reward:,}**!")
    @commands.command(name="give", aliases=["send", "pay"])
    async def give(self, ctx, member: discord.Member, amount: int):
        if member.bot or member.id == ctx.author.id:
            return await ctx.send("You cannot send cash to yourself or a bot.")
        sender_bal = await self.get_cash(ctx.guild.id, ctx.author.id)
        await self.get_cash(ctx.guild.id, member.id)
        if amount <= 0 or amount > sender_bal:
            return await ctx.send("You don't have enough cash.")
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE users SET cash = cash - ? WHERE guild_id = ? AND user_id = ?", (amount, ctx.guild.id, ctx.author.id))
            await db.execute("UPDATE users SET cash = cash + ? WHERE guild_id = ? AND user_id = ?", (amount, ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"**{ctx.author.display_name}** sent **${amount:,}** to **{member.display_name}**!")
    @commands.command(name="lb", aliases=["leaderboard", "top"])
    async def leaderboard(self, ctx):
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute("SELECT user_id, cash FROM users WHERE guild_id = ? ORDER BY cash DESC LIMIT 10", (ctx.guild.id,))
            rows = await cursor.fetchall()

        embed = discord.Embed(title="Top Richest Players", color=discord.Color.gold())
        lines = [f"**{i}.** <@{uid}> — **${cash:,}**" for i, (uid, cash) in enumerate(rows, 1)]
        embed.description = "\n".join(lines) if lines else "No players yet."
        await ctx.send(embed=embed)
async def setup(bot):
    await bot.add_cog(Economy(bot))
