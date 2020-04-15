import json
import logging

import discord
import discord.ext.commands as commands

# Setup logging
rlog = logging.getLogger()
rlog.setLevel(logging.INFO)
handler = logging.FileHandler('panda.log', encoding='utf-8')
handler.setFormatter(logging.Formatter('{asctime}:{levelname}:{name}:{message}', style='{'))
rlog.addHandler(handler)

logging.getLogger('discord').setLevel(logging.WARNING)


class Panda(commands.Bot):
    def __init__(self):
        # load the conf
        self.conf_file = 'conf/panda.json'
        with open(self.conf_file) as fp:
            self.conf = json.load(fp)

        # Init the bot
        super().__init__(commands.when_mentioned_or(self.conf['prefix']), description='Never say no to Panda.')

        # Load cogs
        for cog_name in self.conf['extensions']:
            self.load_extension(f'cogs.{cog_name}')


# Let's rock ! (and roll, because panda are round and fluffy)
bot = Panda()
bot.run(bot.conf['token'])
