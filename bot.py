import os
import discord
import random
import requests
import json
import re
import sys
import datetime
import psycopg2
from discord.ext import commands
from dotenv import load_dotenv

"""
Reading messages we will be using from the .env file included with the bot
This method allows editing of the messages without digging through code
"""
load_dotenv()
owner = int(os.getenv('OWNER_ID'))
command_prefix = os.getenv('COMMAND_PREFIX')
on_command_error_message_GenericMessage = os.getenv('ON_COMMAND_ERROR_MESSAGE_GENERICMESSAGE')
on_command_error_message_CommandInvokeError = os.getenv('ON_COMMAND_ERROR_MESSAGE_COMMANDINVOKEERROR')
on_command_error_message_CheckFailure = os.getenv('ON_COMMAND_ERROR_MESSAGE_CHECKFAILURE')

bot = commands.Bot(command_prefix=command_prefix, owner_id=owner)

forbidden_words = []


class DatabaseConnection:
    def __init__(self):
        self.connection = psycopg2.connect(database='boogerball')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()


Boogerball = DatabaseConnection()

# TODO: Write a function to collect all of the forbidden words and stick them in the above list

# TODO: Write a function to save current attributes of a forbidden word to SQL


def tenor_get(search_term, limit):
    apikey = tenor_token

    r = requests.get("https://api.tenor.com/v1/search?q=%s&key=%s&limit=%s" % (search_term, apikey, limit))

    if r.status_code == 200:
        gifs = json.loads(r.content)
    else:
        gifs = None

    return gifs


def wikipedia_get(argument):
    found = None
    wiki = requests.get(
        'https://en.wikipedia.org/w/api.php?action=opensearch&search="{}"&limit=1&namespace=0&format=json'
        .format(argument))
    if wiki.status_code == 200:
        article = json.loads(wiki.content)

        for results in article:
            if 'https' in str(results):
                found = str(results).replace("['", "").replace("']", "")
            else:
                pass

    else:
        print("I'm having trouble talking to wikipedia. I'll tell my owner about it.")

    return found


def check_if_owner(ctx):
    """
    Bot commands can reference this command's output to determine if the invoking user is the owner of the bot

    :param ctx: instance of discord.ext.commands.Context
    :return: bool for the check of ctx.message.author.id against the defined owner ID in the declaration of bot
    """

    return bot.is_owner(ctx.message.author)


def tuple_to_str(obj, joinchar):
    result = "{}".format(joinchar).join(obj)
    return result


@bot.event
async def on_ready():
    global tenor_token
    print('\n')
    print(f'{bot.user.name} has connected to Discord!')
    tenor_token = str(sys.argv[2])
    await bot.change_presence(activity=discord.Game(name='an instrument!'))


@bot.event
async def on_command_error(ctx, error):
    error_parent_name = error.__class__.__name__

    if isinstance(error, commands.errors.CommandInvokeError):
        response = on_command_error_message_CommandInvokeError
    elif isinstance(error, commands.errors.CommandNotFound):
        response = False
    elif isinstance(error, commands.errors.CheckFailure):
        response = on_command_error_message_CheckFailure
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        response = 'I think you forgot to add something there. Check help for info.'
    else:
        response = False
        pass

    with open('stderr.log', 'a') as s:
        output = 'Command Error: {}, raised: {} \nDuring: {}\n'.format(error_parent_name, str(error), ctx.invoked_with)
        s.write(output)

    with ctx.channel.typing():
        if response is False:
            pass
        else:
            await ctx.send(response)


@bot.command(name='ping', help='Responds to your message. Used for testing purposes.')
async def ping(ctx):
    response = 'Pong!'
    await ctx.send(response)


@bot.command(name='stop', hidden=True, aliases=['bye', 'ciao'])
@commands.check(check_if_owner)
async def stop(ctx):
    response = 'Ok bye!'
    await ctx.send(response)
    await bot.close()


@bot.command(name='boop', help='boop someone!')
async def boop(ctx, booped):
    gif = tenor_get("cute nose boop", 12)
    if gif is None:
        pick_a_gif = None
    else:
        pick_a_gif = gif['results'][random.randint(0, len(gif['results']))]['media'][0]['gif']['url']
    response = '*boops {}* '.format(booped) + pick_a_gif
    await ctx.send(response)


@bot.command(name='wiki', aliases=['wikipedia', 'lookup'], help='Looks up something on wikipedia.')
async def wiki(ctx, *args):
    async with ctx.channel.typing():
        if len(args) == 1:
            lookup_value = args[0]
        else:
            lookup_value = tuple_to_str(args, " ")
        find = wikipedia_get(lookup_value)
        if find is not None:
            response = find
        else:
            response = "No Results Found. Check your spelling and try again."
        await ctx.send(response)


@bot.command(name='rps', help='Rock paper scissors! Syntax is rps [rock/paper/scissors/stats]')
async def rps(ctx, selection):
    async with ctx.channel.typing():

        rps_dict = {
            0: 'rock',
            1: 'paper',
            2: 'scissors'
        }

        rps_sql_dict = {
            'rock': 'rocktimes',
            'paper': 'papetimes',
            'scissors': 'scistimes'
        }

        player_dict = {
            'rock': 0,
            'paper': 1,
            'scissors': 2
        }

        # If the player is here to check their stats...
        if str(selection).lower() == 'stats':
            Boogerball.cursor.execute("SELECT * FROM rps WHERE playerID = '{}'".format(ctx.message.author.id))
            stats = Boogerball.cursor.fetchone()
            if len(stats) != 0:
                response = "<@!{}>'s stats:\nYou've won {} games, lost {}, and tied {} times" \
                           "\nYou've used rock {} times, scissors {} times and paper {} times" \
                           "\nYou've won {} games in a row and played {} times".format(
                            ctx.message.author.id, stats[1], stats[2], stats[3], stats[4], stats[5],
                            stats[6], stats[7], stats[1] + stats[2] + stats[3])
            else:
                response = "I don't think you've played before, am I taking crazy pills?"
            await ctx.send(response)

        # If not, then the player must be here to play...
        elif str(selection).lower() in player_dict:

            # We need to make a row for this player in the DB if this is their first time playing
            Boogerball.cursor.execute("SELECT playerID FROM rps WHERE playerID = '{}';".format(
                    ctx.message.author.id))
            check = Boogerball.cursor.fetchall()
            if len(check) == 0:
                print("Player {} has no entry in rps table, creating...".format(ctx.message.author.id))
                Boogerball.cursor.execute("INSERT INTO rps (playerID, wincount, losecount, drawcount, rocktimes,"
                                          " scistimes, papetimes, streak) VALUES ('{}', 0, 0, 0, 0, 0, 0, 0);".format(
                                            str(ctx.message.author.id)))

            player_pick = player_dict[str(selection.lower())]
            bots_pick = random.randint(0, 2)

            # Let's log what the player picked for stat purposes
            player_sql_pick = rps_sql_dict[str(selection.lower())]
            Boogerball.cursor.execute("UPDATE rps SET {} = {} + 1".format(player_sql_pick, player_sql_pick))

            # The player and bot have picked the same thing, tie game!
            if bots_pick == player_pick:
                bots_response = 'Oh no! A tie! I picked {} too!'.format(rps_dict[bots_pick])
                print("Player {} has tied a game of rps, updating...".format(ctx.message.author.id))
                Boogerball.cursor.execute("UPDATE rps SET drawcount = drawcount + 1, streak = 0 WHERE "
                                          "playerID = '{}';".format(str(ctx.message.author.id)))

            # The player and the bot did not pick the same thing...
            else:
                rps_matrix = [[-1, 1, 0], [1, -1, 2], [0, 2, -1]]
                winner = rps_matrix[player_pick][bots_pick]

                # The player won!
                if winner == player_pick:
                    bots_response = 'Darn it! You win, I picked {}.'.format(rps_dict[bots_pick])
                    print("Player {} has won a game of rps, updating...".format(ctx.message.author.id))
                    Boogerball.cursor.execute("UPDATE rps SET wincount = wincount + 1, streak = streak + 1 WHERE "
                                              "playerID = '{}';".format(str(ctx.message.author.id)))

                # The bot won!
                else:
                    bots_response = 'Boom! Get roasted nerd! I picked {}!'.format(rps_dict[bots_pick])
                    print("Player {} has lost a game of rps, updating...".format(ctx.message.author.id))
                    Boogerball.cursor.execute("UPDATE rps SET losecount = losecount + 1, streak = 0 WHERE "
                                              "playerID = '{}';".format(str(ctx.message.author.id)))

        # The player did something wrong to end up here.
        else:
            bots_response = 'Hey, if you want to play, you have to say rps rock, rps paper or rps scissors'

        # Send the final result.
        await ctx.send(bots_response)

        # Let's check for a win streak and tell the whole channel if the person is on a roll!
        Boogerball.cursor.execute("SELECT streak FROM rps WHERE playerID = '{}'".format(str(ctx.message.author.id)))
        streak_check = Boogerball.cursor.fetchone()
        print("Player {} has won {} games in a row".format(ctx.message.author.id, streak_check[0]))
        if streak_check[0] % 3 == 0 and streak_check[0] > 1:
            await ctx.send("Oh snap <@!{}>! You're on a roll! You've won {} games in a row!".format(
                ctx.message.author.id, streak_check[0]))


@bot.command(name='roll', help='rolls a dice. Syntax is roll d2 up to d1000')
async def roll(ctx, *args):
    async with ctx.channel.typing():
        if args is not None:
            if len(args) == 1:
                try:
                    dice_amount = 1
                    dice_sides = int(args[0].lower().replace('d', ''))
                except ValueError:
                    dice_amount = 0

            elif len(args) == 2:
                try:
                    dice_amount = int(args[0])
                    if dice_amount > 6:
                        notice = "I can't really handle more than 6 dice at a time, so I'll just roll 6."
                        dice_amount = 6
                        await ctx.send(notice)
                    dice_sides = int(args[1].lower().replace('d', ''))
                except ValueError:
                    dice_amount = 0

            else:
                dice_amount = 0

            if dice_amount > 0:
                response = 'Here are your dice!'

                for rolls in range(0, dice_amount):
                    dice_roll = random.randint(1, dice_sides)
                    response += '\nd{} {}: {}'.format(dice_sides, rolls + 1, dice_roll)
            else:
                response = "Look bucko, if you want me to roll a dice, do it like this: roll d2 or roll 2 d6"
        else:
            response = "Look bucko, if you want me to roll a dice, do it like this: roll d2 or roll 2 d6"

    await ctx.send(response)


@bot.command(name='forbid', help='Will set up a trigger so when a word is said, a message is posted. '
                                 'Syntax: forbid cookies AH! Now Im hungry, thanks &user, its only been &time since'
                                 ' someone reminded me about it. Yall have said it &times now')
async def forbid(ctx, keyword: str, *args):
    if args is not None:
        pass
        # TODO: Query SQL to ensure keyword does not have a row in ForbiddenWords


@bot.event
async def on_message(message):
    if message.author != bot.user:
        channel = message.channel
        # TODO: Run through the list of forbidden words to see if a message needs to be said
        if re.search(r'\b[t,T]rump\b', message.content, flags=re.IGNORECASE) is not None:
            response = "Oh god! Don't say his name!!"
            await channel.send(response)

        elif re.search(r'\b[u,U]w[u,U]\b', message.content, flags=re.IGNORECASE) is not None:
            uwu = {"r": "w", "R": "W", "l": "w", "L": "W"}
            response = message.content
            for x, y in uwu.items():
                response = response.replace(x, y)
            await channel.send(response)

    await bot.process_commands(message)

bot.run(str(sys.argv[1]))
