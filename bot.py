import discord
import logging
import config
from discord.ext import commands
import os
from riotwatcher import LolWatcher, ApiError
import requests 
import datetime as dt
import asyncio, aiohttp
from tqdm.asyncio import tqdm
from aiolimiter import AsyncLimiter
import json
import time

#logging.basicConfig(level=logging.INFO)

client = discord.Client()
guild = discord.Guild

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(':-)'))

@client.event
async def on_disconnect():
    print('We have logged off as {0.user}'.format(client))
    await client.change_presence(status=discord.Status.offline, activity=discord.Game(':-)'))

async def checkPlayer(api_key, region, summoner_name, channel):
    #PHASE 1: GET SUMMONER NAME
    watcher = LolWatcher(api_key)
    try:
        response_summoner = watcher.summoner.by_name(region, summoner_name)
    except ApiError as err:
        if err.response.status_code == 429:
            print("trying again")
        elif err.response.status_code == 404:
            await channel.send("Cannot find summoner with name {0}".format(summoner_name))
            return
    id = response_summoner['id']
    puuid = response_summoner['puuid']
    summoner_name = response_summoner['name']

    #print loading message to output:
    await channel.send("Loading information for {0}... please wait".format(summoner_name))


    #PHASE 2: GET PLAYER'S GAMES
    matches = []
    start = 0
    count = 100
    while True:
        try:
            URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/'+ puuid + '/ids?start='+ str(start) + '&count=' + str(count) + '&api_key=' + api_key
            async with aiohttp.ClientSession() as session:
                async with session.get(URL) as resp:
                    response_match_list = json.loads(await resp.text()) #stringdict to dict
        except requests.HTTPError as err:
            if err.response.status_code == 429:
                print("ratelimit")
            else:
                print(err.response.status_code)
                break
        if len(response_match_list) == 0:
            break
        matches.extend(response_match_list)
        start += count #next set of games

    if len(matches) == 0:
        title = "No previous names for {0} found"
        desc = "The summoner hasn't played games in a while.\n"
        player_embed = discord.Embed(title=title, description=desc, color=0x8ee6dd)
        await channel.send(embed=player_embed)
        return 

    max_api_calls = 100 #at max, 100 API calls
    step_amount = max(len(matches) // max_api_calls, 1)
    
    #PHASE 3: GET ALL PREVIOUS NAMES THROUGH ALL PREVIOUS MATCHES
    match_urls = []
    for index in range (0, len(matches), step_amount):
        match_url = 'https://americas.api.riotgames.com/lol/match/v5/matches/' + matches[index] + '?api_key=' + api_key
        match_urls.append(match_url)
    
    #fetches a riot item - semaphore lock to control concurrency
    async def fetch(session, sem, url, puuid): 
        async with sem:
            async with session.get(url) as response:
                match_response = json.loads(await response.text())
                try:
                    participants = match_response['info']['participants']
                    time_played = match_response['info']['gameStartTimestamp'] / 1000
                    timeSTR = dt.datetime.utcfromtimestamp(time_played).strftime("%Y/%m/%d")
                    for player in participants:
                        if type(player) == dict:
                            if player['puuid'] == puuid:
                                return (player['summonerName'], timeSTR)
                except KeyError as err:
                    return (None, None)
                else:
                    return (None, timeSTR)

    CONCURRENCY = 5 #coroutines at the same time MAX
    TIMEOUT = 15 #if the semaphore is locked, wait 15s
    sem = asyncio.Semaphore(CONCURRENCY)
    try:
        async with aiohttp.ClientSession() as session:
            responses = await tqdm.gather(*(
                asyncio.wait_for(fetch(session, sem, i, puuid), TIMEOUT)
                for i in match_urls
            ))
    except asyncio.TimeoutError:
        print("Timeout error")
        return

    seen = set()
    res_list = [(a, b) for a, b in responses[:-1] 
         if not (a in seen or seen.add(a)) and a is not None] 
    
    back_index = 1
    while back_index < len(responses): #solves issue where last index is a None: keep going back until we get something substantive
        if responses[-back_index][0] is not None:
            res_list.append(tuple(responses[-back_index])) #add the last one back in so we get a 
            break
        else:
            back_index += 1

    all_summoner_names, all_namechange_times = zip(*res_list)
    
    if len(all_summoner_names) <= 2:
        title = "No previous names for {0} found: {1} games checked".format(all_summoner_names[0], len(matches))
        if len(matches) == 0:
            desc = "The summoner hasn't played games in a while.\n"
        else:
            desc = "The summoner hasn't changed their name since at least " + all_namechange_times[-1] + "."
        player_embed = discord.Embed(title=title, description=desc, color=0x8ee6dd)
        await channel.send(embed=player_embed)
    else:
        title = "Previous names for {0}: {1} games checked".format(all_summoner_names[0], len(matches))
        desc = ""
        for i in range(1, len(all_namechange_times)-1):
            desc += all_summoner_names[i-1] + "\t<-\t" + all_summoner_names[i] + "\t(~around " + all_namechange_times[i] + ")\n"
        desc += all_summoner_names[-1] + " since at least " + all_namechange_times[-1]
        player_embed = discord.Embed(title=title, description=desc, color=0x8ee6dd)
        await channel.send(embed=player_embed)


@client.event
async def on_message(message):
    if message.author == client.user: #no infinite loops where the bot calls itself
        return
    
    elif message.content.startswith('_'): #Commands
        channel = message.channel
        cmd = message.content.split()[0].replace("_","")
        if len(message.content.split()) > 1:
            parameters = message.content.split()[1:]

        #ECHO MESSAGE BACK TO THE USER
        elif cmd == 'echo':
            await channel.send("*YOUR MESSAGE:* " + message.content.replace("_echo", "", 1))
        
        elif cmd == 'shutdown':
            shutdown_embed = discord.Embed(title='Bot Update', description='I am now shutting down. See you later. BYE! :slight_smile:', color=0x8ee6dd)
            await channel.send(embed=shutdown_embed)
            await client.close()
            exit(0)

    #riot player checker
    elif message.content.startswith('p'):
        message_arr = message.content.split()
        cmd = message_arr[0].replace("_","")
        if cmd == 'pcheck':
            start = time.time()
            channel = message.channel
            riot_api_key = config.riot_api_key
            region = 'na1'
            summoner_name = ' '.join(message_arr[1:])
            if summoner_name.isspace() or summoner_name == '': #blank call of pcheck
                await channel.send("Please send the summoner name like this: *pcheck Kshuna*")
                return   
            async with limiter: #TODO: Send a message if the person needs to wait             
                await checkPlayer(riot_api_key, region, summoner_name, channel)
                await channel.send("Time Elapsed: {:.4f} seconds".format(time.time() - start))

limiter = AsyncLimiter(2,10)                              
client.run(config.bot_token)

#If the bot is closed or canceled
