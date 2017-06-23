import asyncio
import functools

import discord
import discord.ext.commands as commands


def setup(bot):
    if not discord.opus.is_loaded():
        discord.opus.load_opus('opus')
    bot.add_cog(Music(bot))


def duration_to_str(duration):
    # Extract minutes, hours and days
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    # Create a fancy string
    return f"{f'{days} days, ' if days > 0 else ''}{f'{hours} hours, ' if hours > 0 else ''}{f'{minutes} minutes, ' if minutes > 0 else ''}{seconds} seconds"


class MusicError(commands.UserInputError):
    pass


class YtdlAudio(discord.FFmpegPCMAudio):
    def __init__(self, info, **kwargs):
        self.info = info
        super().__init__(info['url'], **kwargs)

    @classmethod
    async def create(cls, url, loop=None, ytdl_options=None, **kwargs):
        import youtube_dl

        loop = loop or asyncio.get_event_loop()

        ytdl_opts = {
            'format': 'webm[abr>0]/bestaudio/best',
            'prefer_ffmpeg': True,
        }
        if ytdl_options and isinstance(ytdl_options, dict):
            ytdl_opts.update(ytdl_options)
        ytdl = youtube_dl.YoutubeDL(ytdl_opts)

        partial = functools.partial(ytdl.extract_info, url, download=False)
        info = await loop.run_in_executor(None, partial)

        if "entries" in info:
            info = info['entries'][0]

        return cls(info, **kwargs)


class Song(discord.PCMVolumeTransformer):
    def __init__(self, source, requester, channel):
        self.info = source.info
        self.requester = requester
        self.channel = channel
        super().__init__(source)

    def __str__(self):
        return f"**{self.info['title']}** from **{self.info.get('creator') or self.info['uploader']}** (duration: {duration_to_str(self.info['duration'])})"


class GuildMusicState:
    def __init__(self, loop):
        self.playlist = asyncio.Queue(maxsize=50)
        self.voice_client = None
        self.loop = loop
        self.player_volume = 0.5
        self.skips = set()
        self.min_skips = 5

    @property
    def current_song(self):
        return self.voice_client.source

    @property
    def volume(self):
        return self.player_volume

    @volume.setter
    def volume(self, value):
        self.player_volume = value
        if self.voice_client:
            self.voice_client.source.volume = value

    def clear(self):
        self.playlist._queue.clear()

    async def stop(self):
        self.clear()
        if self.voice_client:
            self.voice_client.stop()
            await self.voice_client.disconnect()
            self.voice_client = None

    def is_playing(self):
        return self.voice_client and self.voice_client.is_playing()

    async def play_next_song(self, error=None):
        if error:
            await self.current_song.channel.send(f'An error has occurred while playing {self.current_song}: {error}')

        if self.playlist.empty():
            await self.stop()
        else:
            next_song = self.playlist.get_nowait()
            next_song.volume = self.player_volume
            self.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next_song(e), self.loop).result())
            await next_song.channel.send(f'Now playing {next_song}')


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.music_states = {}

    def __unload(self):
        for state in self.music_states.values():
            self.bot.loop.create_task(state.stop())

    def __local_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command cannot be used in a private message.')
        return True

    async def __before_invoke(self, ctx):
        ctx.music_state = self.get_music_state(ctx.guild.id)

    async def __error(self, ctx, error):
        if not isinstance(error, commands.UserInputError):
            raise error

        try:
            await ctx.send(error)
        except discord.Forbidden:
            pass # /shrug

    def get_music_state(self, guild_id):
        state = self.music_states.get(guild_id)
        if not state:
            state = GuildMusicState(self.bot.loop)
            self.music_states[guild_id] = state
        return state

    @commands.command()
    async def status(self, ctx):
        """Displays the currently played song."""
        if ctx.music_state.is_playing():
            song = ctx.music_state.current_song
            await ctx.send(f'Playing {song}. Volume at {song.volume * 100}% in {ctx.music_state.voice_client.channel.mention}')
        else:
            await ctx.send('Not playing.')

    @commands.command()
    async def playlist(self, ctx):
        """Shows info about the current playlist."""
        info = 'Current playlist:\n'
        info_len = len(info)
        for song in list(ctx.music_state.playlist._queue):
            s = str(song)
            l = len(s) + 1 # Counting the extra \n
            if info_len + l > 1995:
                info += '[...]'
                break
            info += f'{s}\n'
            info_len += l

        await ctx.send(info)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.

        If no channel is given, summons it to your current voice channel.
        """
        if channel is None and not ctx.author.voice:
            raise MusicError('You are not in a voice channel nor specified a voice channel for me to join.')

        destination = channel or ctx.author.voice.channel

        if ctx.music_state.voice_client:
            await ctx.music_state.voice_client.move_to(destination)
        else:
            ctx.music_state.voice_client = await destination.connect()

    @commands.command()
    async def play(self, ctx, *, song: str):
        """Plays a song or adds it to the playlist.

        Automatically searches with youtube_dl
        List of supported sites :
        https://github.com/rg3/youtube-dl/blob/1b6712ab2378b2e8eb59f372fb51193f8d3bdc97/docs/supportedsites.md
        """
        await ctx.message.add_reaction('\N{HOURGLASS}')

        # Add the song to the playlist
        opts = {
            'default_search': 'auto',
            'quiet': True
        }
        source = Song(await YtdlAudio.create(song, loop=ctx.bot.loop, ytdl_options=opts), ctx.author, ctx.channel)
        try:
            ctx.music_state.playlist.put_nowait(source)
        except asyncio.QueueFull:
            raise MusicError('Playlist is full, try again later.')

        # Connect to the voice channel if needed
        voice_client = ctx.music_state.voice_client
        if voice_client is None or not voice_client.is_connected():
            await ctx.invoke(self.join)
            voice_client = ctx.music_state.voice_client

        # Start playing or notify it's been added to the playlist
        if not ctx.music_state.is_playing():
            await ctx.music_state.play_next_song()
        else:
            await ctx.send(f'Queued {source} in position **#{ctx.music_state.playlist.qsize()}**')

        await ctx.message.remove_reaction('\N{HOURGLASS}', ctx.me)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @play.error
    async def play_error(self, ctx, error):
        await ctx.message.remove_reaction('\N{HOURGLASS}', ctx.me)
        await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def pause(self, ctx):
        """Pauses the player."""
        if ctx.music_state.voice_client:
            ctx.music_state.voice_client.pause()

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def resume(self, ctx):
        """Resumes the player."""
        if ctx.music_state.voice_client:
            ctx.music_state.voice_client.resume()

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def stop(self, ctx):
        """Stops the player, clears the playlist and leaves the voice channel."""
        await ctx.music_state.stop()

    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """Sets the volume of the player, scales from 0 to 100."""
        if volume < 0 or volume > 100:
            raise MusicError('The volume level has to be between 0 and 100.')
        ctx.music_state.volume = volume/100

    @commands.command()
    async def clear(self, ctx):
        """Clears the playlist."""
        ctx.music_state.clear()

    @commands.command()
    async def skip(self, ctx):
        """Votes to skip the current song.

        To configure the minimum number of votes needed, use `minskips`
        """
        if not ctx.music_state.is_playing():
            raise MusicError('Not playing anything to skip.')

        if ctx.author.id in ctx.music_state.skips:
            raise MusicError(f'{ctx.author.mention} You already voted to skip that song')

        # Count the vote
        ctx.music_state.skips.add(ctx.author.id)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        # Check if the song has to be skipped
        if len(ctx.music_state.skips) > ctx.music_state.min_skips or ctx.author == ctx.music_state.current_song.requester:
            ctx.music_state.skips.clear()
            await ctx.music_state.play_next_song()

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def minskips(self, ctx, number: int):
        """Sets the minimum number of votes to skip a song.

        Requires the `Manage Guild` permission.
        """
        ctx.music_state.min_skips = number
