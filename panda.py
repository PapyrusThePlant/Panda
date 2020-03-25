import json
import logging

import discord.ext.commands as commands

# Setup logging
rlog = logging.getLogger()
rlog.setLevel(logging.INFO)
handler = logging.FileHandler('logs/panda.log', encoding='utf-8')
handler.setFormatter(logging.Formatter('{asctime}:{levelname}:{name}:{message}', style='{'))
rlog.addHandler(handler)

logging.getLogger('discord').setLevel(logging.WARNING)

# Get the token
with open('conf/panda.json') as fp:
	conf = json.load(fp)

# Complicated bot creation
bot = commands.Bot(commands.when_mentioned_or(conf['prefix']), description='Never say no to Panda.')

# Load cogs
for cog_name in conf['extensions']:
	bot.load_extension(f'cogs.{cog_name}')


# Cogs management
@bot.command()
@commands.has_permissions(manage_guild=True)
async def load(ctx, name):
	"""Loads an extension

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
		await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


@bot.command()
@commands.has_permissions(manage_guild=True)
async def unload(ctx, name):
	"""Unloads an extension

	This command requires the Manage Server permission.
	"""
	try:
		ctx.bot.unload_extension(f'cogs.{name}')
	except commands.ExtensionNotLoaded:
		await ctx.send(f'Extension {name} not loaded.')
	else:
		conf['extensions'].remove(name)
		await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


@bot.command()
@commands.has_permissions(manage_guild=True)
async def reload(ctx):
	"""Reloads the bot's extensions.

	This command requires the Manage Server permission.
	"""
	for cog_name in conf['extensions']:
		await ctx.invoke(load, cog_name)
		await ctx.invoke(unload, cog_name)

	await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

# Let's rock ! (and roll, because panda are round and fluffy)
bot.run(conf['token'])
