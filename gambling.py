import discord
from discord.ext import commands
import aiosqlite
import random
import asyncio
class BlackjackView(discord.ui.View):
    def __init__(self, cog, ctx, bet: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.bet = bet
        self.deck = self.create_deck()
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.ended = False
    def create_deck(self):
        suits = ["♠️", "♥️", "♦️", "♣️"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [(r, s) for s in suits for r in ranks]
        random.shuffle(deck)
        return deck
    def hand_value(self, hand) -> int:
        value = 0
        aces = 0
        for rank, _ in hand:
            if rank in ("J", "Q", "K"):
                value += 10
            elif rank == "A":
                value += 11
                aces += 1
            else:
                value += int(rank)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    def format_hand(self, hand, hide_second=False) -> str:
        if hide_second:
            r, s = hand[0]
            return f"**{r}{s}**  |  **??**"
        return "  |  ".join(f"**{r}{s}**" for r, s in hand)
    def build_embed(self, status: str = None, color=discord.Color.blurple()):
        p_val = self.hand_value(self.player_hand)
        d_val = self.hand_value(self.dealer_hand) if self.ended else "?"
        embed = discord.Embed(title=f"Blackjack — Bet: ${self.bet:,}", color=color)
        embed.add_field(name=f"{self.ctx.author.display_name}'s Hand ({p_val})", value=self.format_hand(self.player_hand), inline=False)
        embed.add_field(name=f"Dealer's Hand ({d_val})", value=self.format_hand(self.dealer_hand, hide_second=not self.ended), inline=False)
        if status:
            embed.description = f"**{status}**"
        return embed
    async def end_game(self, interaction: discord.Interaction, status: str, net_change: int, color):
        self.ended = True
        for item in self.children:
            item.disabled = True
        await self.cog.update_cash(self.ctx.guild.id, self.ctx.author.id, net_change)
        await interaction.response.edit_message(embed=self.build_embed(status, color), view=self)
        self.stop()
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This isn't your Blackjack table.", ephemeral=True)
            return False
        return True
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(self.deck.pop())
        p_val = self.hand_value(self.player_hand)
        if p_val > 21:
            await self.end_game(interaction, f"Bust! Lost -${self.bet:,}.", -self.bet, discord.Color.red())
        elif p_val == 21:
            await self.dealer_turn(interaction)
        else:
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.dealer_turn(interaction)
    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.primary)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        cash = await self.cog.get_cash(self.ctx.guild.id, self.ctx.author.id)
        if cash < self.bet * 2:
            return await interaction.response.send_message("Not enough cash to Double Down!", ephemeral=True)
        self.bet *= 2
        self.player_hand.append(self.deck.pop())
        if self.hand_value(self.player_hand) > 21:
            await self.end_game(interaction, f"Doubled & Busted! Lost -${self.bet:,}.", -self.bet, discord.Color.red())
        else:
            await self.dealer_turn(interaction)
    async def dealer_turn(self, interaction: discord.Interaction):
        while self.hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        p_val, d_val = self.hand_value(self.player_hand), self.hand_value(self.dealer_hand)
        if d_val > 21 or p_val > d_val:
            await self.end_game(interaction, f"You win! +${self.bet:,}!", self.bet, discord.Color.green())
        elif p_val < d_val:
            await self.end_game(interaction, f"Dealer wins! Lost -${self.bet:,}.", -self.bet, discord.Color.red())
        else:
            await self.end_game(interaction, "Push (Tie)! Bet returned.", 0, discord.Color.light_grey())
class Gambling(commands.Cog):
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
    async def update_cash(self, guild_id: int, user_id: int, delta: int):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("UPDATE users SET cash = MAX(0, cash + ?) WHERE guild_id = ? AND user_id = ?", (delta, guild_id, user_id))
            await db.commit()
    def parse_bet(self, bet_str: str, cash: int) -> int:
        bet_str = bet_str.lower()
        if bet_str == "all": return cash
        if bet_str == "half": return cash // 2
        if bet_str.endswith("k"): return int(float(bet_str[:-1]) * 1000)
        if bet_str.endswith("m"): return int(float(bet_str[:-1]) * 1_000_000)
        return int(bet_str)
    @commands.command(name="cf", aliases=["coinflip"])
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def coinflip(self, ctx, arg1: str, arg2: str = None):
        cash = await self.get_cash(ctx.guild.id, ctx.author.id)
        choice, bet_str = "heads", arg1
        if arg1.lower() in ("h", "heads", "t", "tails"):
            choice = "heads" if arg1.lower() in ("h", "heads") else "tails"
            if not arg2: return await ctx.send("Specify a bet! Example: `$cf t 500`")
            bet_str = arg2
        elif arg2 and arg2.lower() in ("h", "heads", "t", "tails"):
            choice = "heads" if arg2.lower() in ("h", "heads") else "tails"
            bet_str = arg1
        amount = self.parse_bet(bet_str, cash)
        if amount <= 0 or amount > cash: return await ctx.send("Not enough cash!")
        msg = await ctx.send(f"**{ctx.author.display_name}** spent **${amount:,}** and chose **{choice}**\nThe coin spins...")
        await asyncio.sleep(2)
        result = random.choice(["heads", "tails"])
        if choice == result:
            await self.update_cash(ctx.guild.id, ctx.author.id, amount)
            await msg.edit(content=f"**{ctx.author.display_name}** spent **${amount:,}** and chose **{choice}**\nLanded on **{result}** — you won **${amount * 2:,}**!")
        else:
            await self.update_cash(ctx.guild.id, ctx.author.id, -amount)
            await msg.edit(content=f"**{ctx.author.display_name}** spent **${amount:,}** and chose **{choice}**\nLanded on **{result}** — you lost it all...")
    @commands.command(name="slots", aliases=["slot", "s"])
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def slots(self, ctx, bet: str):
        cash = await self.get_cash(ctx.guild.id, ctx.author.id)
        amount = self.parse_bet(bet, cash)
        if amount <= 0 or amount > cash: return await ctx.send("Not enough cash!")
        symbols = ["🍒", "🍋", "🍇", "💎", "7️⃣"]
        msg = await ctx.send(f"**SLOTS**\n**[ ? | ? | ? ]**\n**{ctx.author.display_name}** bet **${amount:,}**...")
        await asyncio.sleep(1.5)
        r1, r2, r3 = random.choice(symbols), random.choice(symbols), random.choice(symbols)
        board = f"**SLOTS**\n**[ {r1} | {r2} | {r3} ]**\n"
        if r1 == r2 == r3:
            mult = 10 if r1 == "7️⃣" else (5 if r1 == "💎" else 3)
            winnings = amount * mult
            await self.update_cash(ctx.guild.id, ctx.author.id, winnings - amount)
            await msg.edit(content=f"{board}Won **${winnings:,}** ({mult}x)!")
        elif r1 == r2 or r2 == r3 or r1 == r3:
            winnings = int(amount * 1.5)
            await self.update_cash(ctx.guild.id, ctx.author.id, winnings - amount)
            await msg.edit(content=f"{board}Matched two and won **${winnings:,}**!")
        else:
            await self.update_cash(ctx.guild.id, ctx.author.id, -amount)
            await msg.edit(content=f"{board}Won nothing...")
    @commands.command(name="bj", aliases=["blackjack"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def blackjack(self, ctx, bet: str):
        cash = await self.get_cash(ctx.guild.id, ctx.author.id)
        amount = self.parse_bet(bet, cash)
        if amount <= 0 or amount > cash: return await ctx.send("Not enough cash!")
        view = BlackjackView(self, ctx, amount)
        if view.hand_value(view.player_hand) == 21:
            view.ended = True
            bonus = int(amount * 1.5)
            await self.update_cash(ctx.guild.id, ctx.author.id, bonus)
            return await ctx.send(embed=view.build_embed(f"NATURAL BLACKJACK! Won +${bonus:,}!", discord.Color.gold()))
        await ctx.send(embed=view.build_embed(), view=view)
    @commands.command(name="roulette", aliases=["rl"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def roulette(self, ctx, space: str, bet: str):
        cash = await self.get_cash(ctx.guild.id, ctx.author.id)
        amount = self.parse_bet(bet, cash)
        if amount <= 0 or amount > cash: return await ctx.send("Not enough cash!")
        space = space.lower()
        red_nums = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        if space not in {"red", "black", "green", "even", "odd"} and not (space.isdigit() and 0 <= int(space) <= 36):
            return await ctx.send("Bet on `red`, `black`, `green`, `even`, `odd`, or `0-36`.")
        roll = random.randint(0, 36)
        color = "green" if roll == 0 else ("red" if roll in red_nums else "black")
        emoji = "🟢" if color == "green" else ("🔴" if color == "red" else "⚫")
        won, mult = False, 0
        if space.isdigit() and int(space) == roll: won, mult = True, 35
        elif space == color: won, mult = True, (14 if color == "green" else 2)
        elif space == "even" and roll != 0 and roll % 2 == 0: won, mult = True, 2
        elif space == "odd" and roll % 2 == 1: won, mult = True, 2
        if won:
            profit = amount * (mult - 1)
            await self.update_cash(ctx.guild.id, ctx.author.id, profit)
            await ctx.send(f"Landed on {emoji} **{roll} ({color.upper()})**! Won **+${profit:,}** ({mult}x)!")
        else:
            await self.update_cash(ctx.guild.id, ctx.author.id, -amount)
            await ctx.send(f"Landed on {emoji} **{roll} ({color.upper()})**! Lost **-${amount:,}**.")
    @commands.command(name="casino")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def casino(self, ctx, bet: str):
        cash = await self.get_cash(ctx.guild.id, ctx.author.id)
        amount = self.parse_bet(bet, cash)
        if amount <= 0 or amount > cash: return await ctx.send("Not enough cash!")
        outcome = random.choice(["bust", "bust", "bust", "loss", "loss", "1.5x", "1.5x", "2x", "2x", "4x"])
        if outcome == "bust":
            await self.update_cash(ctx.guild.id, ctx.author.id, -amount)
            await ctx.send(f"**VIP Casino:** House swept the board. Lost **-${amount:,}**.")
        elif outcome == "loss":
            lost = amount // 2
            await self.update_cash(ctx.guild.id, ctx.author.id, -lost)
            await ctx.send(f"**VIP Casino:** Saved half your stack. Lost **-${lost:,}**.")
        else:
            mult = float(outcome[:-1])
            profit = int(amount * (mult - 1))
            await self.update_cash(ctx.guild.id, ctx.author.id, profit)
            await ctx.send(f"**VIP Casino:** Big win (**{outcome}**)! Walked away with **+${profit:,}**!"
async def setup(bot):
    await bot.add_cog(Gambling(bot))
