import json
import logging
import discord.ext.commands as commands

# Setup logging
rlog = logging.getLogger()
rlog.setLevel(logging.INFO)
handler = logging.FileHandler('panda.log', encoding='utf-8')
handler.setFormatter(logging.Formatter('{asctime}:{levelname}:{name}:{message}', style='{'))
rlog.addHandler(handler)

# Get the token
with open('conf.json') as fp:
    conf = json.load(fp)

# Complicated bot creation
bot = commands.Bot(commands.when_mentioned_or(conf['prefix']))
bot.load_extension('music')

# For when the bot is shitting itself
@bot.command()
@commands.has_permissions(manage_guild=True)
async def reload(ctx):
    """Reloads the music module.

    This command requires the Manage Server permission.
    """
    ctx.bot.unload_extension('music')
    ctx.bot.load_extension('music')
    await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

# Let's rock ! (and roll, because panda are round and fluffy)
bot.run(conf['token'])
