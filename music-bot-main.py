import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN in .env file!")

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Initialize bot
bot = commands.Bot(command_prefix='/', intents=intents)
bot.remove_command('help')

# Music configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.voice_clients = {}

    def get_voice_client(self, ctx):
        return self.voice_clients.get(ctx.guild.id)

    # NEW JOIN COMMAND
    @commands.command(name='join')
    async def join(self, ctx):
        """Join your voice channel"""
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                if self.get_voice_client(ctx):
                    await self.get_voice_client(ctx).move_to(channel)
                else:
                    self.voice_clients[ctx.guild.id] = await channel.connect()
                await ctx.send(f"Joined {channel.name} 🔊")
            else:
                await ctx.send("You need to be in a voice channel first!")
        except Exception as e:
            await ctx.send(f"Error joining: {str(e)}")

    # NEW LEAVE COMMAND
    @commands.command(name='leave')
    async def leave(self, ctx):
        """Leave the voice channel"""
        voice = self.get_voice_client(ctx)
        if voice and voice.is_connected():
            if ctx.guild.id in self.queues:
                self.queues[ctx.guild.id].clear()
            await voice.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("Left the voice channel 🔇")
        else:
            await ctx.send("I'm not in a voice channel!")

    async def play_next(self, ctx):
        if self.queues.get(ctx.guild.id):
            if len(self.queues[ctx.guild.id]) > 0:
                link = self.queues[ctx.guild.id].pop(0)
                await self.play(ctx, link=link)

    async def play(self, ctx, *, link):
        try:
            if not self.get_voice_client(ctx):
                await ctx.invoke(self.join)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            if 'entries' in data:
                data = data['entries'][0]

            audio_url = data['url']
            title = data.get('title', 'Unknown Track')

            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)

            self.get_voice_client(ctx).play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            await ctx.send(f"Now playing: **{title}**")


        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @commands.command(name='play')
    async def play_command(self, ctx, *, query):
        """Play a song from YouTube"""
        await self.play(ctx, link=query)

    @commands.command(name='queue')
    async def queue(self, ctx, *, url):
        """Add a song to the queue"""
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []
        self.queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")

    @commands.command(name='clear_queue')
    async def clear_queue(self, ctx):
        """Clear the current queue"""
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("No queue to clear!")

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pause the current song"""
        voice = self.get_voice_client(ctx)
        if voice and voice.is_playing():
            voice.pause()
            await ctx.send("Paused ⏸️")

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Resume playback"""
        voice = self.get_voice_client(ctx)
        if voice and voice.is_paused():
            voice.resume()
            await ctx.send("Resuming ▶️")

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Stop playback"""
        voice = self.get_voice_client(ctx)
        if voice and voice.is_playing():
            voice.stop()
            await ctx.send("Playback stopped ⏹️")

    @commands.command(name='next', aliases=['skip'])
    async def next(self, ctx):
        """Skip to the next song in the queue"""
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send("⏩ Skipped to next song")
        else:
            await ctx.send("Nothing is currently playing!")

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help(self, ctx):
        """Show this help message"""
        help_text = """
**Music Commands:**
`/join` - Join your voice channel
`/leave` - Leave the voice channel
'/next - Skip to next song
`/play [query/url]` - Play music from YouTube
`/pause` - Pause playback
`/resume` - Resume playback
`/stop` - Stop playback
`/queue [url]` - Add to queue
`/clear_queue` - Clear the queue
`/help` - Show this message

"""
        await ctx.send(help_text)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing,
        name="Sand🏖️/help for commands"
    ))

async def main():
    async with bot:
        await bot.add_cog(MusicCog(bot))
        await bot.add_cog(HelpCog(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())