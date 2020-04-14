import json
import logging
import subprocess
import time

import discord
import discord.ext.commands as commands

import psutil

# Setup logging
rlog = logging.getLogger()
rlog.setLevel(logging.INFO)
handler = logging.FileHandler('panda.log', encoding='utf-8')
handler.setFormatter(logging.Formatter('{asctime}:{levelname}:{name}:{message}', style='{'))
rlog.addHandler(handler)

logging.getLogger('discord').setLevel(logging.WARNING)

conf_file = 'conf/panda.json'

# Get the token
with open(conf_file) as fp:
    conf = json.load(fp)

# Complicated bot creation
bot = commands.Bot(commands.when_mentioned_or(conf['prefix']), description='Never say no to Panda.')

# Load cogs
for cog_name in conf['extensions']:
    bot.load_extension(f'cogs.{cog_name}')

start_time = time.time()


def duration_to_str(duration):
    """Converts a timestamp to a string representation."""
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    duration = []
    if days > 0: duration.append(f'{days} days')
    if hours > 0: duration.append(f'{hours} hours')
    if minutes > 0: duration.append(f'{minutes} minutes')
    if seconds > 0 or len(duration) == 0: duration.append(f'{seconds} seconds')

    return ', '.join(duration)


@bot.command(aliases=['infos'])
async def info(ctx):
    """Shows info about the bot."""
    latest_commits = subprocess.check_output(['git', 'log', '--pretty=format:[`%h`](https://github.com/PapyrusThePlant/Panda/commit/%h) %s', '-n', '5']).decode('utf-8')

    embed = discord.Embed(description='[Click here to get your own Panda!](https://github.com/PapyrusThePlant/Panda)', colour=discord.Colour.blurple())
    embed.set_thumbnail(url='https://raw.githubusercontent.com/PapyrusThePlant/Panda/master/images/panda.jpg')
    embed.set_author(name='Author : Papyrus#0095', icon_url='https://cdn.discordapp.com/avatars/145110704293281792/2775b3ee7b6a865722b3f6a27da8b14a.webp?size=1024')
    embed.add_field(name='Command prefixes', value=f'`@{ctx.guild.me.display_name} `, `{conf["prefix"]}`', inline=False)
    embed.add_field(name='CPU', value=f'{psutil.cpu_percent()}%')
    embed.add_field(name='Memory', value=f'{psutil.Process().memory_full_info().uss / 1048576:.2f} Mb')  # Expressed in bytes, turn to Mb and round to 2 decimals
    embed.add_field(name='Uptime', value=duration_to_str(int(time.time() - start_time)))
    embed.add_field(name='Latest changes', value=latest_commits, inline=False)
    embed.add_field(name='\N{ZERO WIDTH SPACE}', value='For any question about the bot, announcements and an easy way to get in touch with the author, feel free to join the dedicated [discord server](https://discord.gg/AvAsTHW).')
    embed.set_footer(text='Powered by discord.py', icon_url='http://i.imgur.com/5BFecvA.png')

    await ctx.send(embed=embed)


# Cogs management
@bot.command()
@commands.has_permissions(manage_guild=True)
async def load(ctx, name):
    """Loads an extension.

    This command requires the Manage Server permission.
    """
    try:
        ctx.bot.load_extension(f'cogs.{name}')
    except commands.ExtensionAlreadyLoaded:
        await ctx.send(f'Extension {name} already loaded.')
    except commands.ExtensionNotFound:
        await ctx.send(f'Extension {name} not found.')
    else:
        conf['extensions'].append(name)
        with open(conf_file, 'w') as fp:
            json.dump(conf, fp)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


@bot.command()
@commands.has_permissions(manage_guild=True)
async def unload(ctx, name):
    """Unloads an extension.

    This command requires the Manage Server permission.
    """
    try:
        ctx.bot.unload_extension(f'cogs.{name}')
    except commands.ExtensionNotLoaded:
        await ctx.send(f'Extension {name} not loaded.')
    else:
        conf['extensions'].remove(name)
        with open(conf_file, 'w') as fp:
            json.dump(conf, fp)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


@bot.command()
@commands.has_permissions(manage_guild=True)
async def reload(ctx, *extensions):
    """Reloads extensions.

    If none are provided, reload all loaded extensions.

    This command requires the Manage Server permission.
    """
    if extensions is None:
        extensions = conf['extensions']

    for cog in extensions:
        try:
            ctx.bot.unload_extension(f'cogs.{cog}')
            ctx.bot.load_extension(f'cogs.{cog}')
        except commands.ExtensionError as e:
            await ctx.send(f'Error reloading extension {cog} : {e}')

    await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


# Let's rock ! (and roll, because panda are round and fluffy)
bot.run(conf['token'])
