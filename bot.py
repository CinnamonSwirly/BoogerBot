import os
import discord
import random
import requests
import json
import re
import sys
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


def tenor_get(search_term, limit):
    apikey = tenor_token

    r = requests.get("https://api.tenor.com/v1/search?q=%s&key=%s&limit=%s" % (search_term, apikey, limit))

    if r.status_code == 200:
        gifs = json.loads(r.content)
    else:
        gifs = None

    return gifs


def wikipedia_get():
    wiki = requests.get('https://en.wikipedia.org/wiki/Special:Random')
    if wiki.status_code == 200:
        article = wiki.text
    else:
        article = None

    if article is not None:
        title = article.split('<title>')[1].split(' - Wikipedia</title>')[0]
    else:
        title = None

    return title


def check_if_owner(ctx):
    """
    Bot commands can reference this command's output to determine if the invoking user is the owner of the bot

    :param ctx: instance of discord.ext.commands.Context
    :return: bool for the check of ctx.message.author.id against the defined owner ID in the declaration of bot
    """

    return bot.is_owner(ctx.message.author)


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


@bot.command(name='wikimix', help='Plays madlibs with wikipedia')
async def wikimix(ctx):
    async with ctx.channel.typing():
        response = 'Let me cook something up...'
        await ctx.send(response)
        mixes = [
            'Imagine {} mixed with {}'.format(wikipedia_get(), wikipedia_get()),
            'A new dish! {} and {} served with a side of {}'.format(wikipedia_get(), wikipedia_get(), wikipedia_get()),
            'Try the hot new dance! {}'.format(wikipedia_get()),
            'You know what really helps me relax? Bundling up with {} while remembering {}'.format(wikipedia_get(),
                                                                                                   wikipedia_get())
        ]
        mix = mixes[random.randint(0, len(mixes)-1)]
        await ctx.send(mix)


@bot.command(name='rps', help='Rock paper scissors! Syntax is rps [rock/paper/scissors]')
async def rps(ctx, selection):
    async with ctx.channel.typing():

        response = 'Oh you wanna go, huh?'
        await ctx.send(response)

        rps_dict = {
            0: 'rock',
            1: 'paper',
            2: 'scissors'
        }

        player_dict = {
            'rock': 0,
            'paper': 1,
            'scissors': 2
        }

        if str(selection).lower() in player_dict:
            player_pick = player_dict[str(selection.lower())]
            bots_pick = random.randint(0, 2)
            if bots_pick == player_pick:
                bots_response = 'Oh no! A tie! I picked {} too!'.format(rps_dict[bots_pick])
            else:
                rps_matrix = [[-1, 1, 0], [1, -1, 2], [0, 2, -1]]
                winner = rps_matrix[player_pick][bots_pick]
                if winner == player_pick:
                    bots_response = 'Darn it! You win, I picked {}.'.format(rps_dict[bots_pick])
                else:
                    bots_response = 'Boom! Get roasted nerd! I picked {}!'.format(rps_dict[bots_pick])
        else:
            bots_response = 'Hey, if you want to play, you have to say rps rock, rps paper or rps scissors'

        await ctx.send(bots_response)


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


@bot.event
async def on_message(message):
    if message.author != bot.user:
        channel = message.channel
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

