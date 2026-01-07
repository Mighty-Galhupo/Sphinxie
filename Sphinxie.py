import discord
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

    print(f"Successfully logged in as {client.user}.")

# When the user sends a command in a message on discord, reads it then acts accordingly
@client.event
async def on_message(message):
    global targetChannel
    global targetThread
    if message.author == client.user:
        return

    if message.content.startswith("$SphinxieSetChannel"):
        channel = message.channel.id
        with open("channel_file.txt", "w", encoding="UTF-8") as channel_file:
            channel_file.write(str(channel))
        targetChannel = client.get_channel(channel)
        await targetChannel.send("Target channel set!")

    if message.content.startswith("$SphinxieAskQuestion"):
        if targetChannel == None:
            await ask_question(message.channel)
        else: await ask_question(targetChannel)

    if message.content.startswith("$SphinxieSetQuestionTime"):
        if not setTargetTime(message.content):
            await message.channel.send("Target time not in valid format, \
                                       please use the command with the following format: \
                                       $SphinxieSetQuestionTime hh mm.")
        else:
            daily_question.change_interval(time=targetTime)
            await message.channel.send("Target time set to "+targetTime.strftime("%H:%M")+".")

    if message.content.startswith("$SphinxieEnableDailyQuestion"):
        if not daily_question.is_running():
            daily_question.start()
            await message.channel.send("Daily question enabled.")
        else:
            await message.channel.send("Daily question is already on.")
    
    if message.content.startswith("$SphinxieDisableDailyQuestion"):
        if daily_question.is_running():
            daily_question.cancel()
            await message.channel.send("Daily question disabled.")
        else:
            await message.channel.send("Daily question is already off.")

    if message.content.startswith("$SphinxiePresenceCheck"):
        await message.channel.send('Hello world!')
    
    if message.content.startswith("$SphinxieCheckUserList"):
        await message.channel.send(get_members())

    if message.content.startswith("$SphinxieCheckQuestionTime"):
        await message.channel.send("The daily question is set to "+targetTime.strftime("%H:%M")+".")

    if message.content.startswith("$SphinxieUnsetChannel"):
        if targetChannel == None:
            await message.channel.send("There is no targeted channel.")
        else:
            targetChannel = None
            await message.channel.send("Target channel unset!")

    if message.content.startswith("$SphinxieUnsetThread"):
        if targetThread == None:
            await message.channel.send("There is no targeted thread.")
        else:
            targetThread = None
            await message.channel.send("Target thread unset!")
        
    if message.content.startswith("$SphinxieMakePoll"):
        options = get_members()
        await make_poll(message.channel, get_question(), options)
    
    if message.content.startswith("$SphinxieCreateThread"):
        await open_thread(message, "This is a thread.")

    if message.content.startswith("$SphinxieClearConsumedQuestions"):
        with open("consumed_file.txt", "w", encoding="UTF-8") as _:
            pass
        await message.channel.send("Consumed questions cleared!")

    if message.content.startswith("$SphinxieVote"):
        voteResult = vote(message.content)
        users = get_members()
        await message.channel.send("Successfully voted for "+users[voteResult]+"!")

    if message.content.startswith("$SphinxieFinishVoting"):
        await message.channel.send(makeSummary())

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
    Returns a list with the display names of all members of the server (excluding bots).
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

def vote(message):
    global givenVotes
    content = message.split()
    try:
        target = int(content[1])
    except ValueError:
        return False
    except IndexError:
        return False
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

def setTargetTime(message):
    """
    Sets the time at which the daily question should be asked to the specified one.
    
    :param message: Message with the command to set the time (string)
    """
    global targetTime
    content = message.split()
    try:
        hour = int(content[1])
        minute = int(content[2])
    except ValueError:
        return False
    except IndexError:
        return False
    targetTime = datetime.time(hour=hour, minute=minute, tzinfo=local_tz)
    with open("time_file.txt", "w", encoding="UTF-8") as time_file:
            time_file.writelines(content[1]+"\n"+content[2])
    return True

# Obtains the bot's login token from the token_file
with open("token_file.txt", "r", encoding="UTF-8") as token_file:
    token = token_file.read()

# Runs the bot with the token
client.run(token)