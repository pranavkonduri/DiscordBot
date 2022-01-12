import os
import discord
import logging
import config
from discord.ext import commands
import os
from riotwatcher import LolWatcher, ApiError
import requests 
from tqdm import tqdm 
import datetime as dt
import asyncio, aiohttp

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
    watcher = LolWatcher(api_key)
    try:
        response_summoner = watcher.summoner.by_name(region, summoner_name)
    except ApiError as err:
        if err.response.status_code == 429:
            print("trying again")
        else:
            raise
    id = response_summoner['id']
    puuid = response_summoner['puuid']
    summoner_name = response_summoner['name']
    matches = []
    start = 0
    count = 100
    while True:
        try:
            URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/'+ puuid + '/ids?start='+ str(start) + '&count=' + str(count) + '&api_key=' + api_key
            response = requests.get(URL)
        except requests.HTTPError as err:
            if err.response.status_code == 429:
                print("ratelimit")
            else:
                print(err.response.status_code)
                break
        response_match_list = response.json()
        if len(response_match_list) == 0:
            break
        matches.extend(response_match_list)
        start += count #next set of games
    
    all_summoner_names = [summoner_name]
    all_namechange_times = [None]
    bar = tqdm(total=len(matches))
    message = await channel.send("Loading...\tProgress: N/A")
    max_api_calls = 100 #at max, 100 API calls
    step_amount = max(len(matches) // max_api_calls, 1)
    progress = "Loading information for {player}... \tProgress: {pg:.2f}% \t New Names Found: {nnf}"
    
    for index in range(0, len(matches), step_amount):
        await message.edit(content=progress.format(player = all_summoner_names[0], pg = min(100, (index + step_amount) / len(matches) * 100), nnf=len(all_summoner_names) - 1))
        bar.update(step_amount)
        match = matches[index]
        try:
            MATCH_URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/' + match + '?api_key=' + api_key
            response = requests.get(MATCH_URL)
        except requests.HTTPError as err:
            if err.response.status_code == 429:
                print("rate limit")
                raise
            else:
                print(err.response.status_code)
                raise
        match_response = response.json()
        try:
            participants = match_response['info']['participants']
            for player in participants:
                if type(player) == dict:
                    if player['summonerId'] == id:
                        if (player['summonerName'] not in all_summoner_names):
                            time = match_response['info']['gameStartTimestamp'] / 1000
                            timeSTR = dt.datetime.utcfromtimestamp(time).strftime("%Y/%m/%d")
                            all_summoner_names.append(player['summonerName'])
                            all_namechange_times.append(timeSTR)
                            #print(player['summonerName'], timeSTR)
        except KeyError as err:
            continue
    if len(all_summoner_names) == 1:
        title = "No previous names for {0}: {1} games checked".format(all_summoner_names[0], len(matches))
        desc = "Either the summoner hasn't changed their name, or hasn't played games in a while."
        player_embed = discord.Embed(title=title, description=desc, color=0x8ee6dd)
        await channel.send(embed=player_embed)
    else:
        title = "Previous names for {0}: {1} games checked".format(all_summoner_names[0], len(matches))
        desc = ""
        for i in range(1, len(all_namechange_times)):
            desc += all_summoner_names[i-1] + "\t<-\t" + all_summoner_names[i] + "\t(~around " + all_namechange_times[i] + ")\n"
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
            channel = message.channel
            riot_api_key = config.riot_api_key
            region = 'na1'
            summoner_name = ' '.join(message_arr[1:])
            if summoner_name.isspace() or summoner_name == '': #blank call of pcheck
                await channel.send("Please send the summoner name like this: *pcheck Kshuna*")
                return
            if sem.locked():
                await channel.send("Rate Limited: Please wait as the queue times are high.")
            async with sem:                    
                await checkPlayer(riot_api_key, region, summoner_name, channel)

                    

sem = asyncio.Semaphore(4) #3 processes cannot join at the same time (0->2 only)            
client.run(config.bot_token)

#If the bot is closed or canceled
