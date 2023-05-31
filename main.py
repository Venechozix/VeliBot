from discord.ext import commands
from discord import app_commands
import discord
from wavelink.ext import spotify
import wavelink as wavelink
import datetime
import asyncio
from decouple import config

key = config('TOKEN')

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.all()
        client = discord.Client(intents=intents)
        tree = app_commands.CommandTree(client)
        super().__init__(intents=intents,command_prefix='l!')

    async def on_ready(self) -> None:
        print(f"Logged to {self.user} | {self.user.id}")
    
    async def setup_hook(self) -> None:
        sc = spotify.SpotifyClient(client_id="f32b6ffb6a314f28bef375a9cc54461f",client_secret="5783648465de48f2a555db4522ac5b84")
        node : wavelink.Node = wavelink.Node(
            uri="lavalink1.albinhakanson.se:1141"
            ,password="albinhakanson.se"
            ,secure=False
        )
        await wavelink.NodePool.connect(client=bot,nodes=[node],spotify=sc)
        wavelink.Player.autoplay = False
            
bot=Bot()
bot.remove_command("help")

class QueuePagination(discord.ui.View):
    def __init__(self, vc: wavelink.Player, ctx: commands.Context):
        super().__init__()
        self.vc = vc
        self.ctx = ctx
        self.current_page = 1
        self.sep = 7

    async def send(self, ctx):
        self.message = await ctx.send(embed=await self.create_embed(), view=self)

    async def create_embed(self):
        embed = discord.Embed(title=f"Queue - Page {self.current_page}")
        if self.vc.is_playing() or not self.vc.queue.is_empty:
            np = self.vc.current
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{np.identifier}/maxresdefault.jpg")
            try:
                embed.add_field(name="Now Playing:", value=f"*{np.title} - {','.join(np.artists)}*  || Duration : [{datetime.timedelta(milliseconds=np.duration)}]", inline=False)
            except:
                embed.add_field(name="Now Playing:", value=f"*{np.title} - {np.author}*  || Duration : [{datetime.timedelta(milliseconds=np.duration)}]", inline=False)

            if not self.vc.queue.is_empty:
                embed.add_field(name="------------------------------------------",value="")
                from_item = (self.current_page - 1) * self.sep
                until_item = from_item + self.sep
                song_counter = from_item

                for i, song in enumerate(self.vc.queue):
                    if from_item <= i < until_item:
                        song_counter += 1
                        try:
                            embed.add_field(name=f"[{song_counter}] {song.title} - {song.author}", value=f"Duration {datetime.timedelta(milliseconds=song.duration)}", inline=False)
                        except:
                            embed.add_field(name=f"[{song_counter}] {song.title} - {','.join(song.artists)}", value=f"Duration {datetime.timedelta(milliseconds=song.length)}", inline=False)

        else:
            embed.description = "You're not playing any song"

        return embed

    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)

    def update_buttons(self):
        if self.current_page == 1:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == int(len(self.vc.queue) / self.sep) + 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
            
        if self.vc.queue.is_empty:
            self.next_song.disabled = True
            self.next_song.style = discord.ButtonStyle.gray
        else:
            self.next_song.disabled = False
            self.next_song.style = discord.ButtonStyle.primary

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary,disabled=True)
    async def prev_button(self, interaction: discord.Interaction ,button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        self.update_buttons()
        await self.update_message()

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction , button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        self.update_buttons()
        await self.update_message()
        
    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary)
    async def next_song(self, interaction: discord.Interaction , button: discord.ui.Button):
        await interaction.response.defer()
        await self.vc.stop()
        await self.ctx.reply("The song has been skipped",ephemeral=True)
        self.update_buttons()
        
class NowPlaying(discord.ui.View):
    def __init__(self, vc: wavelink.Player, channel: discord.channel):
        super().__init__()
        self.vc = vc
        self.channel = channel
    
    skipped=False
    dc=False
    
    async def send(self):
        self.message = await self.channel.send(embed=await self.create_embed(),view=self)
        
    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)
        
    async def create_embed(self):
        await asyncio.sleep(1.5)
        if not (self.skipped or self.dc):
            song= self.vc.current
            embed = discord.Embed(title="Now Playing:")
            try:
                embed.add_field(name=f"{song.title}", value=song.author)
            except:
                embed.add_field(name=f"{song.title}", value=','.join(song.artists))
    
        if self.skipped :
            embed = discord.Embed(title="Skipped the song")
            embed.add_field(name="Thanks for using my bot :)",value="" )
        
        elif self.dc:
            embed = discord.Embed(title="Disconnected")
            embed.add_field(name="Thanks for using my bot :)",value="" )
        
        return embed
        
    def update_buttons(self):
        self.next_song.disabled = True
        self.next_song.style = discord.ButtonStyle.gray
        self.disconnect.style = discord.ButtonStyle.gray
        self.disconnect.disabled = True
    
    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary)
    async def next_song(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        await self.vc.stop()
        self.update_buttons()
        self.skipped = True
        await self.update_message()
        return
    
    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.red)
    async def disconnect(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        await self.vc.disconnect()
        self.update_buttons()
        self.dc=True
        await self.update_message()
        return 
        
@bot.command()
async def queue(ctx):
    vc: wavelink.Player = ctx.guild.voice_client 
    pagination = QueuePagination(vc, ctx)
    await pagination.send(ctx)
    
        
@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEventPayload):
    player = payload.player
    channel = player.channel
    
    if player.queue.is_empty:
        try:
            await channel.send("There are no more tracks on the queue")
            await asyncio.sleep(60)
            if player.is_playing():
                return
            else:
                await channel.send("inactive for 60 seconds, leaving the vc...")
                await player.disconnect()
            return
        except Exception as e:
            print(e)
    
@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackEventPayload):
    player = payload.player
    channel = player.channel

    message = NowPlaying(vc=player, channel=channel)
    await message.send()    

@bot.command()
async def getnodeinfo(ctx: commands.Context):
    await ctx.send(wavelink.NodePool.get_connected_node().uri)
    await ctx.send(wavelink.NodePool.get_connected_node().status)
    await ctx.send(wavelink.NodePool.get_connected_node().heartbeat)
    
@bot.command()
async def help(context: commands.Context):
    embed=discord.Embed(title="About VeliBot ", description="VeliBot is a Music Bot made by ChoZix#2922, it's purpose is play music for the very sane brsl server (and sometimes my private servers )", color=0x83163c)
    embed.set_author(name="VeliBot Help", icon_url="https://i.imgur.com/X4JFBq1.jpeg")
    embed.set_thumbnail(url="https://i.imgur.com/X4JFBq1.jpeg")
    embed.add_field(name="Commands", value="list of active commands for VeliBot (it's posible that some of these change) ", inline=True)
    embed.add_field(name="v!Help", value="displays this message", inline=True)
    embed.add_field(name="v!Play [Song or Spotify link]", value="Plays a song or video from Youtube or Spotify ( Playlist and albums work)", inline=True)
    embed.add_field(name="v!Pause", value="Pauses the song", inline=True)
    embed.add_field(name="v!Resume", value="Resumes the song", inline=True)
    embed.add_field(name="v!Skip", value="Skips the current song", inline=True)
    embed.add_field(name="v!Volume [Value from 1 to 100]", value="Changes the Volume (recomended: 15%)", inline=True)
    embed.add_field(name="v!Queue", value="Shows the queue", inline=True)
    embed.add_field(name="v!Disconnect", value="Leaves the Voice Channel", inline=True)
    await context.send(embed=embed) 
    
@bot.tree.command(name="nodetest")
async def nodetest(interaction: discord.Interaction):
    await interaction.response.send_message(f"{wavelink.NodePool.get_connected_node().status}")
    
@bot.command()
async def play(context: commands.Context, *, search: str):
    """Simple play command that accepts a Spotify song URL.

    This command enables AutoPlay. AutoPlay finds songs automatically when used with Spotify.
    Tracks added to the Queue will be played in front (Before) of those added by AutoPlay.
    """
    
    if not context.guild.voice_client:
        try:
            vc: wavelink.Player = await context.author.voice.channel.connect(cls=wavelink.Player)
        except:
            context.reply("you're not in any channel")
            return
    else:
        vc: wavelink.Player = context.guild.voice_client

    # Check the search to see if it matches a valid Spotify URL...
    decoded = spotify.decode_url(search)
    if not decoded or decoded['type'] is not (spotify.SpotifySearchType.track or spotify.SpotifySearchType.album):
        sp = "yt"
        if decoded and decoded['type'] == spotify.SpotifySearchType.playlist:
            sp="list"
            
    if decoded:
        if decoded['type'] is spotify.SpotifySearchType.track:
            sp= "track"
        elif decoded['type'] is (spotify.SpotifySearchType.album or spotify.SpotifySearchType.playlist):
            sp= "list"   
        
    if sp=="track":
        track = await spotify.SpotifyTrack.search(search,node=wavelink.NodePool.get_connected_node())

    elif sp == "list":
        #put response on wait because we doing a lot of shit in this one (gives error if not)
        async with context.channel.typing():
        
            first = False
            if not vc.is_playing():
                first = True
            
            album_name = "starch"
            thumbnail_url = ":YEP:"
            count=0
            try:
                async for song in spotify.SpotifyTrack.iterator(query=search,node=wavelink.NodePool.get_connected_node()):
                    if first:
                        await vc.play(song)
                        first=False
                    else:
                        if count==1:
                            thumbnail_url = song.images.pop(1)
                            album_name= song.album.title()
                        await vc.queue.put_wait(song)
                    count+=1
                try:        
                    embed = discord.Embed(title="In queue:")
                    embed.add_field(name=f"from album: {album_name}",value=f"{count} tracks")
                    embed.set_thumbnail(url=thumbnail_url)
                    await context.send(embed=embed)
                    return   
                    
                except Exception as e:
                    print(thumbnail_url)
                    print(e)
                    return
            except Exception as e:
                print(e)
                return
    else:
        track = await wavelink.YouTubeTrack.search(search, return_first=True)
        
        # IF the player is not playing immediately play the song...
        # otherwise put it in the queue...
        
        
    if not vc.is_playing():
        try:
            await vc.play(track)
        except Exception as e:
            print(e)
    else:
        await vc.queue.put_wait(track)
        try:
            await context.reply(f"{track.title} - {track.author} added to the queue")
        except:
            try:
                await context.reply(f"{track.title} - {','.join(track.artists)} added to the queue")
            except Exception as e:
                print(e)

@bot.command()
async def skip(context : commands.Context):
    vc: wavelink.Player = context.guild.voice_client
    await vc.stop()
    await context.reply("The song has been skipped")
    
@bot.command()
async def pause(context : commands.Context):
    vc: wavelink.Player = context.guild.voice_client
    if vc.is_playing():
        await vc.pause()
        await context.reply("Pausing...")
    else:
        await context.reply("The song is already paused")
        
@bot.command()
async def resume(context : commands.Context):
    """Resume the song"""
    vc: wavelink.Player = context.guild.voice_client
    if not vc.is_paused():
        await context.reply("The song is already playing")
    else:
        await vc.resume()
        await context.reply("Resuming...")

@bot.command()
async def leave(context : commands.Context):
    """Disconnects from the voice channel"""
    
    vc: wavelink.Player = context.guild.voice_client
    try:
        await vc.disconnect()
        await context.send("Disconnected")
    except:
        await context.reply("The bot is not connected to any channel")

@bot.command()
async def volume(context : commands.Context, volume: int):
    
    vc: wavelink.Player = context.guild.voice_client
    
    if volume > 100:
        return await context.reply('thats wayy to high')
    elif volume < 0:
        return await context.reply("thats way to low")
    await context.send(f"Set the volume to `{volume}%`")
    return await vc.set_volume(volume)


        
bot.run(key)