import discord
from discord import app_commands
from discord.ext import tasks
import datetime
import asyncio
import random

# Setting the intents so that the bot can read messages
# and find out the what the names of users are
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Defines the client so the bot can log in and do things
client = discord.Client(intents=intents)
client.tree = app_commands.CommandTree(client)

# Finds out the local time zone to be used when setting times
local_tz = datetime.datetime.now().astimezone().tzinfo

# Sets up the global variables used for sending the automatic messages
targetChannel = None
targetThread = None
targetTime = datetime.time(hour=0, minute=0, tzinfo=local_tz)

givenVotes = []

# The loop checks what time it is and if it is the specified time
# and there is a channel specified, automatically asks a question there
@tasks.loop(seconds=30)
async def daily_question():
    timeNow = datetime.datetime.now(local_tz)
    if timeNow.hour == targetTime.hour and timeNow.minute == targetTime.minute \
    and targetChannel != None:
        await ask_question(targetChannel)
        await asyncio.sleep(60)

# This would be a better version that would work
# without checking the time every 30 seconds if I actually got it to work
# @tasks.loop(time=targetTime)
# async def daily_question():
#     if targetChannel != None:
#         await ask_question(targetChannel)
#         await asyncio.sleep(60)

# Loads the target channel, thread and time from a file,
# if stored there from previous run, then starts the automatic loop
# and informs user that login was successful
@client.event
async def on_ready():
    try:
        with open("channel_file.txt", "r", encoding="UTF-8") as channel_file:
            global targetChannel
            channel = int(channel_file.read())
            if channel == "":
                print("Warning, channel not set.")
            else:
                targetChannel = client.get_channel(channel)
    except FileNotFoundError:
        print("Warning, channel not set.")
    
    try:
        with open("thread_file.txt", "r", encoding="UTF-8") as thread_file:
            global targetThread
            thread = int(thread_file.read())
            if thread == "":
                print("Warning, thread not set.")
            else:
                targetThread = client.get_channel(thread)
    except FileNotFoundError:
        print("Warning, thread not set.")

    try:
        with open("time_file.txt", "r", encoding="UTF-8") as time_file:
            global targetTime
            time = time_file.readlines()
            if time == "":
                print("Warning, target time left as midnight default.")
            else:
                targetTime = datetime.time(hour=int(time[0]), minute=int(time[1]), tzinfo=local_tz)
    except FileNotFoundError:
        print("Warning, target time left as midnight default.")

    if not daily_question.is_running():
            daily_question.start()

    await app_commands.CommandTree.sync(client.tree)

    print(f"Successfully logged in as {client.user}.")

@client.tree.command(name = "set_channel", description = "Sets current channel as target.")
async def setchannel(interaction: discord.Interaction):
    global targetChannel
    channel = interaction.channel.id
    with open("channel_file.txt", "w", encoding="UTF-8") as channel_file:
        channel_file.write(str(channel))
    targetChannel = client.get_channel(channel)
    await interaction.response.send_message("Target channel set!")

@client.tree.command(name = "ask_question", description = "Asks question in target channel or here if none is set.")
async def ask_question(interaction: discord.Interaction):
    if targetChannel == None:
        await ask_question(interaction.channel)
    else: await ask_question(targetChannel)

@client.tree.command(name = "set_question_time", description = "Sets the target time for the daily question.")
@app_commands.describe(hour = "The hour at which to send.", minute = "The minute at which to send.")
async def set_question_time(interaction: discord.Interaction, hour: int, minute: int):
    if not setTargetTime(hour, minute):
        await interaction.response.send_message("Invalid time given, no changes were made.")
    else:
        await interaction.response.send_message("Target time set to "+targetTime.strftime("%H:%M")+".")

@client.tree.command(name = "enable_daily_question", description = "Makes Sphinxie ask questions at the specified time.")
async def enable_daily_question(interaction: discord.Interaction):
    if not daily_question.is_running():
        daily_question.start()
        await interaction.response.send_message("Daily question enabled.")
    else:
        await interaction.response.send_message("Daily question is already on.")
    
@client.tree.command(name = "disable_daily_question", description = "Makes Sphinxie stop asking questions at the specified time.")
async def disable_daily_question(interaction: discord.Interaction):
    if daily_question.is_running():
        daily_question.cancel()
        await interaction.response.send_message("Daily question disabled.")
    else:
        await interaction.response.send_message("Daily question is already off.")

@client.tree.command(name = "presence_check", description = "Easy way to check if Sphinxie is currently up and running.")
async def presence_check(interaction: discord.Interaction):
    await interaction.response.send_message('Hello world!')

@client.tree.command(name = "check_user_list", description = "Sends a list of all users currently detected.")
async def check_user_list(interaction: discord.Interaction):
    await interaction.response.send_message(get_members())

@client.tree.command(name = "check_question_time", description = "Shows which time the daily question is set for.")
async def check_question_time(interaction: discord.Interaction):
    await interaction.response.send_message("The daily question is set to "+targetTime.strftime("%H:%M")+".")

@client.tree.command(name = "unset_channel", description = "Removes the target channel, leaving it unset.")
async def unset_channel(interaction: discord.Interaction):
    global targetChannel
    if targetChannel == None:
        await interaction.response.send_message("There is no targeted channel.")
    else:
        targetChannel = None
        with open("channel_file.txt", "w", encoding="UTF-8") as _:
            pass
        await interaction.response.send_message("Target channel unset!")

@client.tree.command(name = "unset_thread", description = "Removes the target thread, leaving it unset.")
async def unset_thread(interaction: discord.Interaction):
    global targetThread
    if targetThread == None:
        await interaction.response.send_message("There is no targeted thread.")
    else:
        targetThread = None
        with open("thread_file.txt", "w", encoding="UTF-8") as _:
            pass
        await interaction.response.send_message("Target thread unset!")
        
@client.tree.command(name = "make_poll", description = "Begins a poll in the channel where the command was used.")
async def make_poll(interaction: discord.Interaction):
    options = get_members()
    await make_poll(interaction.channel, get_question(), options)

@client.tree.command(name = "clear_consumed_questions", description = "Resets the list of consumed questions.")
async def clear_consumed_questions(interaction: discord.Interaction):
    with open("consumed_file.txt", "w", encoding="UTF-8") as _:
        pass
    await interaction.response.send_message("Consumed questions cleared!")

@client.tree.command(name = "vote", description = "Votes for specified user.")
@app_commands.describe(user = "The number of the user to vote for.")
async def vote(interaction: discord.Interaction, user: int):
    voteResult = vote(user)
    if voteResult == None:
        await interaction.response.send_message("Voting unsuccessful, invalid user chosen.")
    else:
        users = get_members()
        await interaction.response.send_message("Successfully voted for "+users[voteResult]+"!")

@client.tree.command(name = "finish_voting", description = "Immediately finishes voting and sends results.")
async def finish_voting(interaction: discord.Interaction):
    await interaction.response.send_message(makeSummary())

async def ask_question(location):
    """
    Makes a poll with a question at the specified location,
    then opens a thread on it with the question as the title.
    
    :param location: The channel in which to send the poll (channel)
    """
    initializeVoting()
    question = get_question()
    options = get_members()
    pollMessage = await make_poll(location, question, options)
    if pollMessage != None:
        await open_thread(pollMessage, question)

async def open_thread(location, name):
    """
    Opens a thread at the specified location with the specified name, 
    saves it to targetThread and then saves it's ID in the file thread_file.

    Location can either be a message, where the thread will be connected to the message,
    or a channel where the thread will be opened in the channel by itself.
    
    :param location: Where to open the thread (channel or message)
    :param name: What to name the thread (string)
    """
    global targetThread
    targetThread = await location.create_thread(name=name)
    with open("thread_file.txt", "w", encoding="UTF-8") as thread_file:
            thread_file.write(str(targetThread.id))

async def make_poll(location, question, options):
    """
    Creates a poll at the specified location with the specified question and options.

    Returns the message corresponding to the poll.
    
    :param location: Where to send the poll (channel)
    :param question: What question the poll asks (string)
    :param options: What options the poll has (list of strings)
    """
    if question == None:
        await location.send("There are currently no more questions left to ask.")
        return
    else:
        poll = question + "\n"
        n = 0
        while n<len(options):
            poll+=(str(n+1)+"- "+options[n]+"\n")
            n+=1
        message = await location.send(poll)
        initializeVoting()
        return message

def get_question():
    """
    Returns a random question from the question_file excluding questions in consumed_file
    while adding the chosen question to consumed_file.
    """
    with open("question_file.txt", "r", encoding="UTF-8") as question_file:
        questions = question_file.readlines()
        length = len(questions)
        n = 0
        while n < length:
            questions[n] = questions[n].rstrip("\n")
            n+=1
    consumed_questions = obtain_consumed()
    for q in consumed_questions:
        questions.remove(q)
    if len(questions) == 0:
        return
    else:
        question = questions[random.randint(0, len(questions)-1)]
        consume_question(question)
    return question

def obtain_consumed():
    """
    Returns the list of questions in consumed_file to know which questions to not use.
    """
    try:
        with open("consumed_file.txt", "r", encoding="UTF-8") as consumed_file:
            questions = consumed_file.readlines()
            length = len(questions)
            n = 0
            while n < length:
                questions[n] = questions[n].rstrip("\n")
                n+=1
    except FileNotFoundError:
        questions = []
    return questions

def consume_question(question):
    """
    Adds the given question to the consumed_file so it is not used again.
    
    :param question: The question to add to the consumed_file (string)
    """
    with open("consumed_file.txt", "a", encoding="UTF-8") as consumed_file:
        consumed_file.write(question+"\n")

def get_members():
    """
    Returns a list with the display names of all members of the server (excluding bots) + a "no one".
    """
    unsanitizedMembers = client.get_all_members()
    members = []
    for member in unsanitizedMembers:
        if member.global_name != None:
            members.append(member.global_name)
    members.append("No One")
    return members

def initializeVoting():
    global givenVotes
    givenVotes = []
    amount = len(get_members())
    while len(givenVotes) < amount:
        givenVotes.append(0)

def vote(target):
    global givenVotes
    if not (len(givenVotes) >= target >= 1):
        return None
    givenVotes[target-1]+=1
    return target-1

def makeSummary():
    users = get_members()
    n = 0
    highest = 0
    winners = []
    while n < len(users):
        if givenVotes[n] > highest:
            highest = givenVotes[n]
            winners = [n]
        elif givenVotes[n] == highest:
            winners.append(n)
        n+=1
    if highest == 0:
        return "There are no winners because no one got any votes."
    elif len(winners) == 1:
        return "The winner is "+users[winners[0]]+" with "+str(highest)+" votes!"
    else:
        winnerString = ""
        winners.reverse()
        for n in winners:
            winnerString += users[winners[n]]+", "
        return "The winners are: "+winnerString+"with "+str(highest)+" votes each!"

def setTargetTime(hour, minute):
    """
    Sets the time at which the daily question should be asked to the specified one.
    
    :param hour: The hour at which to ask the question.
    :param minute: The minute at which to ask the question.
    """
    global targetTime
    if not (23 >= hour >= 0 and 59 >= minute >= 0):
        return False
    targetTime = datetime.time(hour=hour, minute=minute, tzinfo=local_tz)
    with open("time_file.txt", "w", encoding="UTF-8") as time_file:
            time_file.writelines(str(hour)+"\n"+str(minute))
    return True

# Obtains the bot's login token from the token_file
with open("token_file.txt", "r", encoding="UTF-8") as token_file:
    token = token_file.read()

# Runs the bot with the token
client.run(token)