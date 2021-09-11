import os
import discord
import logging
import pandas as pd
import config
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)

client = discord.Client()
guild = discord.Guild


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game('_scan help'))

@client.event
async def on_disconnect():
    print('We have logged off as {0.user}'.format(client))
    await client.change_presence(status=discord.Status.offline, activity=discord.Game('_scan help'))


# @client.event
# async def on_typing(channel, user, when):
#     await channel.send("**What are you typing, " + user.name + "?**")

@client.event
async def on_message(message):
    if message.author == client.user: #no infinite loops where the bot calls itself
        return
    elif message.content.startswith('_'): #Commands

        cmd = message.content.split()[0].replace("_","")
        if len(message.content.split()) > 1:
            parameters = message.content.split()[1:]

        # Bot Commands
        #SCAN ALL MESSAGES
        # if cmd == 'scan':

        #     data = pd.DataFrame(columns=['content', 'time', 'author'])

        #     # Acquiring the channel via the bot command
        #     if len(message.channel_mentions) > 0:
        #         channel = message.channel_mentions[0]
        #     else:
        #         channel = message.channel

        #     # Aquiring the number of messages to be scraped via the bot command
        #     if (len(message.content.split()) > 1 and len(message.channel_mentions) == 0) or len(message.content.split()) > 2:
        #         for parameter in parameters:
        #             if parameter == "help":
        #                 answer = discord.Embed(title="Command Format",
        #                                        description="""`_scan <channel> <number_of_messages>`\n\n`<channel>` : **the channel you wish to scan**\n`<number_of_messages>` : **the number of messages you wish to scan**\n\n*The order of the parameters does not matter.*""",
        #                                        colour=0x1a7794) 
        #                 await message.channel.send(embed=answer)
        #                 return
        #             elif parameter[0] != "<": # Channels are enveloped by "<>" as strings
        #                 limit = int(parameter)
        #     else:
        #         limit = 100
            
        #     answer = discord.Embed(title="Creating your Message History Dataframe",
        #                            description="Please Wait. The data will be sent to you privately once it's finished.",
        #                            colour=0x1a7794) 

        #     await message.channel.send(embed=answer)

        #     def is_command (message):
        #         if len(msg.content) == 0:
        #             return False
        #         elif msg.content.split()[0] == '_scan':
        #             return True
        #         else:
        #             return False

        #     async for msg in channel.history(limit=limit + 1000):       # The added 1000 is so in case it skips messages for being
        #         if msg.author != client.user:                           # a command or a message it sent, it will still read the
        #             if not is_command(msg):                             # the total amount originally specified by the user.
        #                 data = data.append({'content': msg.content,
        #                                     'time': msg.created_at,
        #                                     'author': msg.author.name}, ignore_index=True)
        #             if len(data) == limit:
        #                 break
            
        #     # Turning the pandas dataframe into a .csv file and sending it to the user

        #     file_location = f"{str(channel.guild.id) + '_' + str(channel.id)}.csv" # Determining file name and location
        #     data.to_csv(file_location) # Saving the file as a .csv via pandas

        #     answer = discord.Embed(title="Here is yousr .CSV File",
        #                            description=f"""It might have taken a while, but here is what you asked for.\n\n`Server` : **{message.guild.name}**\n`Channel` : **{channel.name}**\n`Messages Read` : **{limit}**""",
        #                            colour=0x1a7794) 

        #     await message.author.send(embed=answer)
        #     await message.author.send(file=discord.File(file_location, filename='data.csv')) # Sending the file
        #     os.remove(file_location) # Deleting the file

        #ECHO MESSAGE BACK TO THE USER
        elif cmd == 'echo':
            channel = message.channel
            await channel.send("*YOUR MESSAGE:* " + message.content.replace("_echo", "", 1))

        #SIMULATE TYPERACER TBD
        elif cmd == 'typeracer':
            if len(message.mentions) == 0: #If you didn't @ anyone like a stupid
                answer = discord.Embed(title="Command Format",
                                               description="""`_typeracer [users] '""",
                                               colour=0x1a7794) 
                await message.channel.send(embed=answer)
                return
            else:
                stats = {}
                for member in message.mentions:
                    await member.send("Good luck! The typeracer will begin in 5 seconds.")
                    stats[member.name] = [datetime.now()]
                time.sleep(5)
                for member in message.mentions:
                    await member.send("Congrats!")
                    stats[member.name] = (datetime.now() - stats[member.name][0]).total_seconds()
                
                print()
                print(stats)

client.run(config.bot_token)

#If the bot is closed or canceled
