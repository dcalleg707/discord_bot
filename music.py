import discord,asyncio,random,youtube_dl,string,os
from discord.ext import commands
from googleapiclient.discovery import build
from discord.ext.commands import command

# import pymongo
#NOTE: Import pymongo if you are using the database function commands 
#NOTE: Also add `pymongo` and `dnspython` inside the requirements.txt file if you are using pymongo

#TODO: CREATE PLAYLIST SUPPORT FOR MUSIC


#NOTE: Without database, the music bot will not save your volume 

ytdl_format_options= {
    'audioquality':8,
    'format': 'worstaudio',
    'outtmpl': '{}',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    "extractaudio":True,
    "audioformat":"opus",
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' #bind to ipv4 since ipv6 addresses cause issues sometimes
}

stim= {
    'default_search': 'auto',
    "ignoreerrors":True,
    'quiet': True,
    "no_warnings": True,
    "simulate": True,  # do not keep the video files
    "nooverwrites": True,
    "keepvideo": False,
    "noplaylist": True,
    "skip_download": False,
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}


ffmpeg_options = {
    'options': '-vn',
    # 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

class Downloader(discord.PCMVolumeTransformer):
    def __init__(self,source,*,data,volume=0.5):
        super().__init__(source,volume)
        self.data=data
        self.title=data.get('title')
        self.url=data.get("url")
        self.thumbnail=data.get('thumbnail')
        self.duration=data.get('duration')
        self.views=data.get('view_count')
        self.playlist={}




    @classmethod
    async def yt_download(cls,url,ytdl,*,loop=None,stream=False):
        """
        Download video directly with link
        """
        API_KEY='API_KEY'
        youtube=build('youtube','v3',developerKey=API_KEY)
        data=youtube.search().list(part='snippet',q=url).execute()
        song_url=data
        song_info=data
        download= await loop.run_in_executor(None,lambda: ytdl.extract_info(song_url,download=not stream))
        filename=data['url'] if stream else ytdl.prepare_filename(download)
        return cls(discord.FFmpegPCMAudio(filename,**ffmpeg_options),data=download),song_info

    async def yt_info(self,song):
        """
        Get info from youtube
        """
        API_KEY='API_KEY'
        youtube=build('youtube','v3',developerKey=API_KEY)
        song_data=youtube.search().list(part='snippet').execute()
        return song_data[0]

    @classmethod
    async def video_url(cls,url,ytdl,*,loop=None,stream=False):
        """
        Download the song file and data
        """
        loop=loop or asyncio.get_event_loop()
        data= await loop.run_in_executor(None,lambda: ytdl.extract_info(url,download=not stream))
        data1={'queue':[]}
        if 'entries' in data:
            if len(data['entries']) >1:
                playlist_titles=[title['title'] for title in data['entries']]
                data1={'title':data['title'],'queue':playlist_titles}
                data1['queue'].pop(0)

            data=data['entries'][0]
                
        filename=data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename,**ffmpeg_options),data=data),data1



    async def get_info(self,url):
        """
        Get the info of the next song by not downloading the actual file but just the data of song/query
        """
        yt=youtube_dl.YoutubeDL(stim)
        down=yt.extract_info(url,download=False)
        data1={'queue':[]}
        if 'entries' in down:
            if len(down['entries']) > 1:
                playlist_titles=[title['title'] for title in down['entries']]
                data1={'title':down['title'],'queue':playlist_titles}

            down=down['entries'][0]['title']
            
        return down,data1


class MusicPlayer(commands.Cog,name='Music'):
    def __init__(self,client):
        self.bot=client
        # self.database = pymongo.MongoClient(os.getenv('MONGO'))['Discord-Bot-Database']['General']
        # self.music=self.database.find_one('music')
        self.player={
            "audio_files":[]
        }

    @property
    def random_color(self):
        return discord.Color.from_rgb(random.randint(1,255),random.randint(1,255),random.randint(1,255))

    # def cog_unload(self):
    #     """
    #     Update the database in mongodb to the latest changes when the bot is disconnecting
    #     """
    #     current=self.database.find_one('music')
    #     if current != self.voice:
    #         self.database.update_one({'_id':'music'},{'$set':self.music})



    @commands.Cog.listener('on_voice_state_update')
    async def music_voice(self,user,before,after):
        """
        Clear the server's playlist after bot leave the voice channel
        """
        if after.channel is None and user.id == self.bot.user.id:
            try:
                self.player[user.guild.id]['queue'].clear()
            except KeyError:
                #NOTE: server ID not in bot's local self.player dict
                print(f"Failed to get guild id {user.guild.id}") #Server ID lost or was not in data before disconnecting



    async def filename_generator(self):
        """
        Generate a unique file name for the song file to be named as
        """
        chars=list(string.ascii_letters+string.digits)
        name=''
        for i in range(random.randint(9,25)):
            name+=random.choice(chars)
        
        if name not in self.player['audio_files']:
            return name

        
        return await self.filename_generator()


    async def playlist(self,data,msg):
        """
        THIS FUNCTION IS FOR WHEN YOUTUBE LINK IS A PLAYLIST
        Add song into the server's playlist inside the self.player dict 
        """
        for i in data['queue']:
            self.player[msg.guild.id]['queue'].append({'title':i,'author':msg})



    async def queue(self,msg,song):
        """
        Add the query/song to the queue of the server
        """
        title1=await Downloader.get_info(self,url=song)
        title=title1[0]
        data=title1[1]
        #NOTE:needs fix here
        if data['queue']:
            await self.playlist(data,msg)
            #NOTE: needs to be embeded to make it better output
            return await msg.send(f"Added playlist {data['title']} to queue")
        self.player[msg.guild.id]['queue'].append({'title':title,'author':msg})
        return await msg.send(f"**{title} added to queue**".title())



    async def voice_check(self,msg):
        """
        function used to make bot leave voice channel if music not being played for longer than 2 minutes
        """
        if msg.voice_client is not None:
            await asyncio.sleep(120)
            if msg.voice_client is not None and msg.voice_client.is_playing() is False and msg.voice_client.is_paused() is False:
                await msg.voice_client.disconnect()


    async def clear_data(self,msg):
        """
        Clear the local dict data
            name - remove file name from dict
            remove file and filename from directory
            remove filename from global audio file names
        """
        name=self.player[msg.guild.id]['name']
        os.remove(name)
        self.player['audio_files'].remove(name)


    async def loop_song(self,msg):
        """
        Loop the currently playing song by replaying the same audio file via `discord.PCMVolumeTransformer()`
        """
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.player[msg.guild.id]['name']))
        loop=asyncio.get_event_loop()
        try:
            msg.voice_client.play(source, after=lambda a: loop.create_task(self.done(msg)))
            msg.voice_client.source.volume=self.player[msg.guild.id]['volume']
            # if str(msg.guild.id) in self.music:
            #     msg.voice_client.source.volume=self.music['vol']/100
        except Exception as Error:
            #Has no attribute play
            print(Error) #NOTE: output back the error for later debugging


    async def done(self,msg,msgId:int=None):
        """
        Function to run once song completes
        Delete the "Now playing" message via ID
        """
        if msgId:
            try:
                message=await msg.channel.fetch_message(msgId)
                await message.delete()
            except Exception as Error:
                print("Failed to get the message")

        if self.player[msg.guild.id]['reset'] is True:
            self.player[msg.guild.id]['reset']=False
            return await self.loop_song(msg)

        if msg.guild.id in self.player and self.player[msg.guild.id]['repeat'] is True:
            return await self.loop_song(msg)

        await self.clear_data(msg)

        if self.player[msg.guild.id]['queue']:
            queue_data=self.player[msg.guild.id]['queue'].pop(0)
            return await self.start_song(msg=queue_data['author'],song=queue_data['title'])


        else:
            await self.voice_check(msg)
    

    async def start_song(self,msg,song):
        new_opts=ytdl_format_options.copy()
        audio_name=await self.filename_generator()

        self.player['audio_files'].append(audio_name)
        new_opts['outtmpl']=new_opts['outtmpl'].format(audio_name)

        ytdl=youtube_dl.YoutubeDL(new_opts)
        download1=await Downloader.video_url(song,ytdl=ytdl,loop=self.bot.loop)

        download=download1[0]
        data=download1[1]
        self.player[msg.guild.id]['name']=audio_name
        emb=discord.Embed(colour=self.random_color, title='Now Playing',description=download.title,url=download.url)
        emb.set_thumbnail(url=download.thumbnail)
        emb.set_footer(text=f'Requested by {msg.author.display_name}',icon_url=msg.author.avatar_url)
        loop=asyncio.get_event_loop()




        if data['queue']:
            await self.playlist(data,msg)

        msgId=await msg.send(embed=emb)
        self.player[msg.guild.id]['player']=download
        self.player[msg.guild.id]['author']=msg
        msg.voice_client.play(download,after=lambda a: loop.create_task(self.done(msg,msgId.id)))

        # if str(msg.guild.id) in self.music: #NOTE adds user's default volume if in database
        #     msg.voice_client.source.volume=self.music[str(msg.guild.id)]['vol']/100
        msg.voice_client.source.volume=self.player[msg.guild.id]['volume']
        return msg.voice_client



    @command()
    async def play(self,msg,*,song):
        """
        Play a song with given url or title from Youtube
        `Ex:` s.play Titanium David Guetta
        `Command:` play(song_name)
        """
        if msg.guild.id in self.player:
            if msg.voice_client.is_playing() is True:#NOTE: SONG CURRENTLY PLAYING
                return await self.queue(msg,song)

            if self.player[msg.guild.id]['queue']:
                return await self.queue(msg,song)

            if msg.voice_client.is_playing() is False  and not self.player[msg.guild.id]['queue']:
                return await self.start_song(msg,song)


        else:
            #IMPORTANT: THE ONLY PLACE WHERE NEW `self.player[msg.guild.id]={}` IS CREATED
            self.player[msg.guild.id]={
                'player':None,
                'queue':[],
                'author':msg,
                'name':None,
                "reset":False,
                'repeat':False,
                'volume': 0.5
            }
            return await self.start_song(msg,song)


    @play.before_invoke
    async def before_play(self,msg):
        """
        Check voice_client
            - User voice = None:
                please join a voice channel
            - bot voice == None:
                joins the user's voice channel
            - user and bot voice NOT SAME:
                - music NOT Playing AND queue EMPTY
                    join user's voice channel
                - items in queue:
                    please join the same voice channel as the bot to add song to queue
        """
    
        if msg.author.voice is None:
            return await msg.send('**Please join a voice channel to play music**'.title())

        if msg.voice_client is None: 
            return await msg.author.voice.channel.connect()


        if msg.voice_client.channel != msg.author.voice.channel:
            
            #NOTE: Check player and queue 
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]['queue']:
                return await msg.voice_client.move_to(msg.author.voice.channel)
                #NOTE: move bot to user's voice channel if queue does not exist
            
            if self.player[msg.guild.id]['queue']:
                #NOTE: user must join same voice channel if queue exist
                return await msg.send("Please join the same voice channel as the bot to add song to queue")
            
    @commands.has_permissions(manage_channels=True)
    @command()
    async def repeat(self,msg):
        """
        Repeat the currently playing or turn off by using the command again
        `Ex:` .repeat
        `Command:` repeat()
        """
        if msg.guild.id in self.player:
            if msg.voice_client.is_playing() is True:
                if self.player[msg.guild.id]['repeat'] is True:
                    self.player[msg.guild.id]['repeat']=False
                    return await msg.message.add_reaction(emoji='???')
                    
                self.player[msg.guild.id]['repeat']=True
                return await msg.message.add_reaction(emoji='???')

            return await msg.send("No audio currently playing")
        return await msg.send("Bot not in voice channel or playing music")


    @commands.has_permissions(manage_channels=True)
    @command(aliases=['restart-loop'])
    async def reset(self,msg):
        """
        Restart the currently playing song  from the begining
        `Ex:` s.reset
        `Command:` reset()
        """
        if msg.voice_client is None:
            return await msg.send(f"**{msg.author.display_name}, there is no audio currently playing from the bot.**")

        if msg.author.voice is None or msg.author.voice.channel != msg.voice_client.channel:
            return await msg.send(f"**{msg.author.display_name}, you must be in the same voice channel as the bot.**")

        if self.player[msg.guild.id]['queue'] and msg.voice_client.is_playing() is False:
            return await msg.send("**No audio currently playing or songs in queue**".title(),delete_after=25)

        self.player[msg.guild.id]['reset']=True
        msg.voice_client.stop()
            



    @commands.has_permissions(manage_channels=True)
    @command()
    async def skip(self,msg):
        """
        Skip the current playing song
        `Ex:` s.skip
        `Command:` skip()
        """
        if msg.voice_client is None:
            return await msg.send("**No music currently playing**".title(),delete_after=60)

       
        if msg.author.voice is None or msg.author.voice.channel != msg.voice_client.channel:
            return await msg.send("Please join the same voice channel as the bot")
        
        
        if self.player[msg.guild.id]['queue'] and msg.voice_client.is_playing() is False:
            return await msg.send("**No songs in queue to skip**".title(),delete_after=60)


        self.player[msg.guild.id]['repeat']=False
        msg.voice_client.stop()
        return await msg.message.add_reaction(emoji='???')

    


    @commands.has_permissions(manage_channels=True)
    @command()
    async def stop(self,msg):
        """
        Stop the current playing songs and clear the queue
        `Ex:` s.stop
        `Command:` stop()
        """
        if msg.voice_client is None:
            return await msg.send("Bot is not connect to a voice channel")

        if msg.author.voice is None:
            return await msg.send("You must be in the same voice channel as the bot")

        if msg.author.voice is not None and msg.voice_client is not None:
            if  msg.voice_client.is_playing() is True or self.player[msg.guild.id]['queue']:
                self.player[msg.guild.id]['queue'].clear()
                self.player[msg.guild.id]['repeat']=False
                msg.voice_client.stop()
                return await msg.message.add_reaction(emoji='???')

            return await msg.send(f"**{msg.author.display_name}, there is no audio currently playing or songs in queue**")


    @commands.has_permissions(manage_channels=True)
    @command(aliases=['get-out','disconnect','leave-voice'])
    async def leave(self,msg):
        """
        Disconnect the bot from the voice channel
        `Ex:` s.leave
        `Command:` leave()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_playing() is True or self.player[msg.guild.id]['queue']:
                self.player[msg.guild.id]['queue'].clear()
                msg.voice_client.stop()
                return await msg.voice_client.disconnect(), await msg.message.add_reaction(emoji='???')
            
            return await msg.voice_client.disconnect(), await msg.message.add_reaction(emoji='???')
        
        if msg.author.voice is None:
            return await msg.send("You must be in the same voice channel as bot to disconnect it via command")



    @commands.has_permissions(manage_channels=True)
    @command()
    async def pause(self,msg):
        """
        Pause the currently playing audio
        `Ex:` s.pause
        `Command:` pause()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is True:
                return await msg.send("Song is already paused")

            if msg.voice_client.is_paused() is False:
                msg.voice_client.pause()
                await msg.message.add_reaction(emoji='???')




    @commands.has_permissions(manage_channels=True)
    @command()
    async def resume(self,msg):
        """
        Resume the currently paused audio
        `Ex:` s.resume
        `Command:` resume()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is False:
                return await msg.send("Song is already playing")

            if msg.voice_client.is_paused() is True:
                msg.voice_client.resume()
                return await msg.message.add_reaction(emoji='???')



    @command(name='queue',aliases=['song-list','q','current-songs'])
    async def _queue(self,msg):
        """
        Show the current songs in queue
        `Ex:` s.queue
        `Command:` queue()
        """
        if msg.voice_client is not None:
            if msg.guild.id in self.player:
                if self.player[msg.guild.id]['queue']:
                    emb=discord.Embed(colour=self.random_color, title='queue')
                    emb.set_footer(text=f'Command used by {msg.author.name}',icon_url=msg.author.avatar_url)
                    for i in self.player[msg.guild.id]['queue']:
                        emb.add_field(name=f"**{i['author'].author.name}**",value=i['title'],inline=False)
                    return await msg.send(embed=emb,delete_after=120)

        return await msg.send("No songs in queue")



    @command(name='song-info',aliases=['song?','nowplaying','current-song'])
    async def song_info(self,msg):
        """
        Show information about the current playing song
        `Ex:` s.song-info
        `Command:` song-into()
        """
        if msg.voice_client is not None and msg.voice_client.is_playing() is True:
            emb=discord.Embed(colour=self.random_color, title='Currently Playing',description=self.player[msg.guild.id]['player'].title)
            emb.set_footer(text=f"{self.player[msg.guild.id]['author'].author.name}",icon_url=msg.author.avatar_url)
            emb.set_thumbnail(url=self.player[msg.guild.id]['player'].thumbnail)
            return await msg.send(embed=emb,delete_after=120)
        
        return await msg.send(f"**No songs currently playing**".title(),delete_after=30)



    @command(aliases=['move-bot','move-b','mb','mbot'])
    async def join(self, msg, *, channel: discord.VoiceChannel=None):
        """
        Make bot join a voice channel you are in if no channel is mentioned
        `Ex:` .join (If voice channel name is entered, it'll join that one)
        `Command:` join(channel:optional)
        """
        if msg.voice_client is not None:
            return await msg.send(f"Bot is already in a voice channel\nDid you mean to use {msg.prefix}moveTo")

        if msg.voice_client is None:
            if channel is None:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji='???')
            
            return await channel.connect(), await msg.message.add_reaction(emoji='???')
        
        else:
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]['queue']:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji='???')


    @join.before_invoke
    async def before_join(self,msg):
        if msg.author.voice is None:
            return await msg.send("You are not in a voice channel")



    @join.error
    async def join_error(self,msg,error):
        if isinstance(error,commands.BadArgument):
            return msg.send(error)

        if error.args[0] == 'Command raised an exception: Exception: playing':
            return await msg.send("**Please join the same voice channel as the bot to add song to queue**".title())



    @commands.has_permissions(manage_channels=True)
    @command(aliases=['vol'])
    async def volume(self,msg,vol:int):
        """
        Change the volume of the bot
        `Ex:` .vol 100 (200 is the max)
        `Permission:` manage_channels
        `Command:` volume(amount:integer)
        """
        
        if vol > 200:
            vol = 200
        vol=vol/100
        if msg.author.voice is not None:
            if msg.voice_client is not None:
                if msg.voice_client.channel == msg.author.voice.channel and msg.voice_client.is_playing() is True:
                    msg.voice_client.source.volume=vol
                    self.player[msg.guild.id]['volume']=vol
                    # if (msg.guild.id) in self.music:
                    #     self.music[str(msg.guild.id)]['vol']=vol
                    return await msg.message.add_reaction(emoji='???')
                    
        
        return await msg.send("**Please join the same voice channel as the bot to use the command**".title(),delete_after=30)
    

    
    @volume.error
    async def volume_error(self,msg,error):
        if isinstance(error,commands.MissingPermissions):
            return await msg.send("Manage channels or admin perms required to change volume",delete_after=30)




def setup(bot):
    bot.add_cog(MusicPlayer(bot))