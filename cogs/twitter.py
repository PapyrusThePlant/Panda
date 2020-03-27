import logging

import discord
import discord.ext.commands as commands
import peony

import config

log = logging.getLogger(__name__)
logging.getLogger('peony').setLevel(logging.WARNING)


def setup(bot):
    bot.add_cog(Twitter(bot))


class TwitterError(commands.UserInputError):
    pass


class Twitter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conf = config.Config('conf/twitter.json', encoding='utf-8')
        self.twitter_client = peony.PeonyClient(**self.conf.credentials)
        self.stream_task = None
        self.stream_start()

    def cog_unload(self):
        self.stream_stop()

    def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command cannot be used in a private message.')
        return True

    async def cog_command_error(self, ctx, error):
        if not isinstance(error, commands.UserInputError):
            raise error

        try:
            await ctx.send(error)
        except discord.Forbidden:
            pass  # /shrug
        finally:
            await ctx.message.add_reaction('\N{CROSS MARK}')

    def remove_channels_from_conf(self, *channels):
        removed = 0
        unfollowed = 0
        channels = set(channels)
        for user_id, conf in self.conf.follows.copy().items():
            map(conf.channels.pop, channels & set(self.conf.follows))

            removed += 1

            if len(conf.channels) == 0:
                del self.conf.follows[user_id]
                unfollowed += 1
        self.conf.save()

        if unfollowed > 0:
            self.stream_restart()
        return removed, unfollowed

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        removed, unfollowed = self.remove_channels_from_conf(channel)
        log.info(f'Deletion of channel {channel.id} removed {removed} feeds and unfollowed {unfollowed}')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        removed, unfollowed = self.remove_channels_from_conf(c.id for c in guild.text_channels)
        log.info(f'Removal of guild {guild.id} removed {removed} feeds and unfollowed {unfollowed}')

    def build_tweet_url(self, screen_name, tweet_id):
        return f'https://twitter.com/{screen_name}/status/{tweet_id}'

    async def dispatch_tweet(self, tweet):
        tweet_url = self.build_tweet_url(tweet['user']['screen_name'], tweet['id'])
        try:
            conf = self.conf.follows[tweet['user']['id']]
        except KeyError as e:
            return  # Apparently peony dispatch retweets of any users we're following as well

        for channel_id in conf.channels:
            await self.bot.get_channel(int(channel_id)).send(tweet_url)
            conf.channels[channel_id].last_tweet_id = tweet['id']
            self.conf.save()

    async def get_timeline(self, user_id=None, screen_name=None, limit: int = 3):
        params = {
            'exclude_replies': True,
            'include_rts': True,
        }
        if user_id:
            params['user_id'] = user_id
            conf = self.conf.follows[user_id]
            since_id = min(c.last_tweet_id for c in conf.channels.values())
        else:
            params['screen_name'] = screen_name
            since_id = 0

        if since_id > 0:
            params['since_id'] = since_id
        else:
            params['count'] = limit

        request = self.twitter_client.api.statuses.user_timeline.get(**params)
        responses = request.iterator.with_since_id(force=False)

        tweets = []
        async for chunk in responses:
            tweets.extend(chunk)
        return tweets

    async def get_timelines(self):
        for user_id, conf in self.conf.follows.items():
            yield await self.get_timeline(user_id=user_id)

    async def update_timelines(self):
        async for timeline in self.get_timelines():
            for timeline_tweet in reversed(timeline):
                await self.dispatch_tweet(timeline_tweet)

    def stream_start(self):
        if len(self.conf.follows) > 0 and self.stream_task is None:
            self.stream_task = self.bot.loop.create_task(self.stream_tweets())

    def stream_stop(self):
        if self.stream_task is not None:
            self.stream_task.cancel()
            self.stream_task = None

    def stream_restart(self):
        self.stream_stop()
        self.stream_start()

    async def stream_tweets(self):
        async with self.twitter_client.stream.statuses.filter.post(follow=list(self.conf.follows.keys())) as stream:
            async for data in stream:
                if peony.events.on_tweet(data):
                    await self.dispatch_tweet(data)
                elif peony.events.on_connect(data):
                    await self.update_timelines()

    @commands.command()
    async def list(self, ctx):
        """Lists the followed channels on the server."""
        follows = {}
        for conf in self.conf.follows.values():
            for channel_id in conf.channels:
                follows.setdefault(discord.utils.get(ctx.guild.text_channels, id=channel_id), []).append(f'@\N{ZERO WIDTH SPACE}{conf.screen_name}')

        if len(follows) == 0:
            raise TwitterError('Not following any channel on this server.')

        embed = discord.Embed(description='Followed channels:', colour=discord.Colour.blurple())
        for channel, channels in sorted(follows.items(), key=lambda t: t[0].position):
            embed.add_field(name=f'#{channel.name}', value=', '.join(sorted(channels)), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def search(self, ctx, query, limit: int = 5):
        """Searches for a Twitter user.

        To use a multi-word query, enclose it in quotes.
        """
        try:
            resp = await self.twitter_client.api.users.search.get(q=query, count=limit)
        except peony.exceptions.NotFound:
            raise TwitterError(f'No result when searching for {query}')
        users = resp.data
        if len(users) == 0:
            raise TwitterError('No result.')
        elif len(users) > 1:
            embed = discord.Embed(colour=discord.Colour.blurple())
            for user in users:
                name = f'{user["name"]} - @{user["screen_name"]}'
                embed.add_field(name=name, value=user['description'] or 'No description', inline=False)
        else:
            user = users[0]
            description = user["description"] or 'No description'
            embed = discord.Embed(colour=discord.Colour.blurple(), title=user['name'], description=description, url=f'https://twitter.com/{user["screen_name"]}')
            embed.set_author(name=f'@{user["screen_name"]}')
            embed.set_thumbnail(url=user["profile_image_url_https"])
            embed.add_field(name='Tweets', value=user["statuses_count"])
            embed.add_field(name='Followers', value=user["followers_count"])
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def follow(self, ctx, handle):
        """Follows a Twitter channel.

        The tweets from the given Twitter channel will be
        sent to the channel this command was used in.
        """
        screen_name = handle.lower().lstrip('@')
        user_id, conf = config.get(self.conf.follows, screen_name=screen_name)

        if conf is not None and ctx.channel.id in conf.channels:
            raise TwitterError(f'Already following {screen_name} in this channel.')
        elif conf is None:
            try:
                resp = await self.twitter_client.api.users.show.get(screen_name=screen_name)
            except peony.exceptions.NotFound:
                raise TwitterError(f'User {screen_name} not found.')
            user = resp.data

            # Retrieving tweets from protected users is only allowed by that user or approved followers
            if user['protected']:
                raise TwitterError('This user is protected and cannot be followed.')

            conf = config.ConfigElement(screen_name=screen_name, channels={})
            self.conf.follows[user['id']] = conf

            tweet_url = self.build_tweet_url(screen_name, user["status"]["id"])
            last_tweet_id = user['status']['id']
        else:
            last_tweet_id = max(c.last_tweet_id for c in conf.channels.values())
            tweet_url = self.build_tweet_url(screen_name, last_tweet_id)

        conf.channels[ctx.channel.id] = config.ConfigElement(last_tweet_id=last_tweet_id)
        self.conf.save()

        self.stream_restart()
        await ctx.send(tweet_url)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def unfollow(self, ctx, handle):
        """Unfollows a Twitter channel.

        The tweets from the given Twitter channel will not be
        sent to the channel this command was used in anymore.
        """
        screen_name = handle.lower().lstrip('@')
        user_id, conf = config.get(self.conf.follows, screen_name=screen_name)
        if conf is None:
            raise TwitterError(f'Not following {screen_name} on this channel.')

        try:
            del conf.channels[ctx.channel.id]
        except KeyError:
            raise TwitterError(f'Not following {screen_name} on this channel.')

        if len(conf.channels) == 0:
            del self.conf.follows[user_id]
            self.stream_restart()
        self.conf.save()

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    async def fetch(self, ctx, handle, limit: int = 3):
        """Retrieves the latest tweets from a channel and displays them.

        If a limit is given, at most that number of tweets will be displayed. Defaults to 1.
        """
        screen_name = handle.lower().lstrip('@')

        try:
            timeline = await self.get_timeline(screen_name=screen_name, limit=limit)
        except peony.exceptions.NotFound:
            raise TwitterError(f'User {screen_name} not found.')

        for tweet in reversed(timeline):
            tweet_url = self.build_tweet_url(screen_name, tweet['id'])
            await ctx.send(tweet_url)

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')