import os
import discord
import random
import requests
import json
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
    tenor_token = input("Enter Tenor Token: ")
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


@bot.command(name='multiply', help='Multiplies number A by number B. Example: multiply 2 6')
async def multiply(ctx, num_a, num_b):
    try:
        response = num_a + ' times ' + num_b + ' = ' + str(int(num_a) * int(num_b))
    except ValueError:
        response = 'Are you trying to perform magic again? Can you not?'
    finally:
        if response is None:
            response = on_command_error_message_GenericMessage
        await ctx.send(response)


@bot.command(name='hello', help='Says hello!')
async def hello(ctx):
    response = 'Hello ' + str(ctx.author) + '! Lovely conversation in ' + str(ctx.channel) + ', eh?'
    async with ctx.channel.typing():
        await ctx.send(response)


@bot.command(name='stop', hidden=True)
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


bot.run(input("Enter Discord Token: "))

