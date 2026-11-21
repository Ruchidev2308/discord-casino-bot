Discord Economy & Casino Bot

I was inspired to build this bot cuz gambling bots don't feature control over currency. (i keep on running out of cowoncy)
This bot allows the admin to give currency as many times as they want. (Never run out of moni for playing)

Features-

$bal
$daily
$give
$lb
$bj (blackjack)
$roulette
$slot
$cf (coin flip)
$casino

Setup-

1. Prerequisites
 Python 3.10 or higher
 A Discord Bot Token from the [Discord Developer Portal](https://discord.com) with **Server Members Intent** and **Message Content Intent** enabled.

2. Installation
```bash
git clone https://github.com
cd discord-casino-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configuration
Create a `.env` file in the root directory and add your bot token:
```env
DISCORD_TOKEN=your_bot_token_here
```

4. Inviting & Running
a. In the Discord Developer Portal under OAuth2 , select the `bot` scope with `Send Messages`, `Embed Links`, and `Read Message History` permissions.
b. Open the generated URL to invite the bot to your server.
c. Start the bot:
```bash
python main.py
```


for both my discord bots, i took this yt tutorial to understand python logic - 
https://youtube.com/playlist?list=PL-7Dfw57ZZVQ-GCNQS4Kyz637Fffhb0Hs&si=XSOw1OHBgy1XW18I

**Soon I will be building interactive gambling bot featuring multiplayer games like rummy**
