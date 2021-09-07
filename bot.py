import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get
import praw
import youtube_dl
import os
from youtubesearchpython import SearchVideos
import json
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
import requests
from bs4 import BeautifulSoup
import random
from dotenv import load_dotenv

load_dotenv()

TOKEN = "NzY2NTEzNTk2OTA0NTA1MzU0.X4kdag.RItKoucW3_eTLiIdqg5F-o2nyDE"
bot = commands.Bot(command_prefix='!', help_command= None)
bot.load_extension('music')
@bot.event
async def on_ready():
    pass

@bot.command()
async def marselo(ctx):
    await ctx.send("Agachate y conocelo");

@bot.command()
async def urban(ctx):
    pag = random.randint(1, 2000000000)
    r = requests.get("https://www.urbandictionary.com/random.php?page="+str(pag))
    s = BeautifulSoup(r.text)
    word = s.find("div", attrs={'class': 'def-header'}).a.text
    definition = s.find("div", attrs={'class': 'meaning'}).text
    await ctx.send("**"+word+"**");
    await ctx.send(definition);
    await ctx.send("-");


@bot.command()
async def key(ctx):
    r = requests.get("https://scrap.tf/")
    s = BeautifulSoup(r.text)
    price = s.find_all("div", attrs={'class': 'banking-selector-overlay'})[1].text
    await ctx.send("**"+price+"**");

@bot.command()
async def news(ctx):
    r = requests.get("https://rpp.pe/mundo")
    s = BeautifulSoup(r.text)
    articles = s.find_all("div", attrs={'class': 'cont'})
    for i in range(5):
        await ctx.send("**"+articles[i].h2.a.text+"**");
        await ctx.send(articles[i].p.text);


@bot.command()
async def dolar(ctx):
    r = requests.get("https://dolar.wilkinsonpc.com.co/divisas/dolar-diario.html")
    s = BeautifulSoup(r.text)
    price = s.find("span", attrs={'class': 'numero'}).text
    await ctx.send("El precio del dolar es: " + price);
    await ctx.send("Que hijueputa más caro");

@bot.command()
async def memes(ctx,section = "animemes", num = 10, num2 = -1):
    image_urls = []
    reddit = praw.Reddit(client_id = 'Do_LvAusQ-3jvg',
                         client_secret = 'VBVLAJz8js0Koyt28hU8S9ZJ_on-jQ',
                         user_agent = 'dcalleg707')
    subreddit = reddit.subreddit(section)
    if num2 == -1 or num > num2:
        posts = subreddit.hot(limit=num)
        for post in posts:
            await ctx.send(str(post.url.encode('utf-8'))[2:-1])
    else:  
        posts = subreddit.hot(limit=num2)
        posts = list(posts)[num:]
        for post in posts:
            await ctx.send(str(post.url.encode('utf-8'))[2:-1])    

@bot.command()
async def help(ctx):
    await ctx.send("**!News** will look for the last 5 global news  from rpp.pe")
    await ctx.send("**!marselo** will invoke marselo himself")
    await ctx.send("**!urban** will post a random word in urban dictionary")
    await ctx.send("**!dolar** will post the dolar current price with a sweet appreciation from marselo")
    await ctx.send("**!key** will post the tf2 key current price in refs")
    await ctx.send("**!play <song>** will play the indicated song or add it to the queue")
    await ctx.send("**!skip** will skip the currently playing song")
    await ctx.send("**!stop** will stop the music")
    await ctx.send("**!repeat** will keep the current song playing in a loop")
    await ctx.send("**!reset** will reset the currently playing song")
    await ctx.send("**!pause** will pause the music")
    await ctx.send("**!resume** will resume the music")
    await ctx.send("**!queue** will show the songs in the queue")
    await ctx.send("**!volume <number>** will change the bot volume to the specified number")
    await ctx.send("**!memes <subreddit> <number> <number2>** will look for the first 10 images in the specified subreddit if no numbers are specified. if the first number is specified, it will send that quantity of memes, and if the second number is specified as well, it will send the memes that are between the first and the second numbers")

@bot.event
async def on_message(message):
    await bot.process_commands(message)


bot.run(TOKEN, bot=True)


