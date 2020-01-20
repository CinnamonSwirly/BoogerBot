import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

"""
Reading messages we will be using from the .env file included with the bot
This method allows editing of the messages without digging through code
"""
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
owner = int(os.getenv('OWNER_ID'))
command_prefix = os.getenv('COMMAND_PREFIX')
on_command_error_message_GenericMessage = os.getenv('ON_COMMAND_ERROR_MESSAGE_GENERICMESSAGE')
on_command_error_message_CommandInvokeError = os.getenv('ON_COMMAND_ERROR_MESSAGE_COMMANDINVOKEERROR')
on_command_error_message_CheckFailure = os.getenv('ON_COMMAND_ERROR_MESSAGE_CHECKFAILURE')


bot = commands.Bot(command_prefix=command_prefix, owner_id=owner)


def check_if_owner(ctx):
    """
    Bot commands can reference this command's output to determine if the invoking user is the owner of the bot

    :param ctx: instance of discord.ext.commands.Context
    :return: bool for the check of ctx.message.author.id against the defined owner ID in the declaration of bot
    """

    return bot.is_owner(ctx.message.author.id)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
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
    with ctx.channel.typing():
        await ctx.send(response)


@bot.command(name='stop', hidden=True)
@commands.check(check_if_owner)
async def stop(ctx):
    await bot.close()


bot.run(token)
