import json
import time
import subprocess

import discord
import discord.ext.commands as commands

import psutil


def setup(bot):
    bot.add_cog(Core(bot))


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


class Core(commands.Cog):
    """♡🐼"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.start_time = time.time()

    @commands.command(aliases=['infos'])
    async def info(self, ctx):
        """Shows info about the bot."""
        latest_commits = subprocess.check_output(['git', 'log', '--pretty=format:[`%h`](https://github.com/PapyrusThePlant/Panda/commit/%h) %s', '-n', '5']).decode('utf-8')

        embed = discord.Embed(description='[Click here to get your own Panda!](https://github.com/PapyrusThePlant/Panda)', colour=discord.Colour.blurple())
        embed.set_thumbnail(url='https://raw.githubusercontent.com/PapyrusThePlant/Panda/master/images/panda.jpg')
        embed.set_author(name='Author : Papyrus#0095', icon_url='https://cdn.discordapp.com/avatars/145110704293281792/2775b3ee7b6a865722b3f6a27da8b14a.webp?size=1024')
        embed.add_field(name='Command prefixes', value=f'`@{ctx.guild.me.display_name} `, `{self.bot.conf["prefix"]}`', inline=False)
        embed.add_field(name='CPU', value=f'{psutil.cpu_percent()}%')
        embed.add_field(name='Memory', value=f'{psutil.Process().memory_full_info().uss / 1048576:.2f} Mb')  # Expressed in bytes, turn to Mb and round to 2 decimals
        embed.add_field(name='Uptime', value=duration_to_str(int(time.time() - self.bot.start_time)))
        embed.add_field(name='Latest changes', value=latest_commits, inline=False)
        embed.add_field(name='\N{ZERO WIDTH SPACE}', value='For any question about the bot, announcements and an easy way to get in touch with the author, feel free to join the dedicated [discord server](https://discord.gg/AvAsTHW).')
        embed.set_footer(text='Powered by discord.py', icon_url='http://i.imgur.com/5BFecvA.png')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def load(self, ctx, name):
        """Loads an extension.

        This command requires the Manage Server permission.
        """
        cog = name.lower()
        try:
            ctx.bot.load_extension(f'cogs.{cog}')
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(f'Extension {name} already loaded.')
        except commands.ExtensionNotFound:
            await ctx.send(f'Extension {name} not found.')
        else:
            self.bot.conf['extensions'].append(cog)
            with open(self.bot.conf_file, 'w') as fp:
                json.dump(self.bot.conf, fp)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def unload(self, ctx, name):
        """Unloads an extension.

        This command requires the Manage Server permission.
        """
        cog = name.lower()
        try:
            ctx.bot.unload_extension(f'cogs.{cog}')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Extension {name} not loaded.')
        else:
            self.bot.conf['extensions'].remove(cog)
            with open(self.bot.conf_file, 'w') as fp:
                json.dump(self.bot.conf, fp)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def reload(self, ctx, *extensions):
        """Reloads extensions.

        If none are provided, reloads all loaded extensions.

        This command requires the Manage Server permission.
        """
        if extensions is None:
            extensions = self.bot.conf['extensions']

        for name in extensions:
            cog = name.lower()
            try:
                ctx.bot.unload_extension(f'cogs.{cog}')
                ctx.bot.load_extension(f'cogs.{cog}')
            except commands.ExtensionError as e:
                await ctx.send(f'Error reloading extension {name} : {e}')

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


