import discord
import random
import requests
import json
import re
import sys
import psycopg2
import asyncio
import time
from psycopg2 import sql
from discord.ext import commands

"""
Reading messages we will be using from the .env file included with the bot
This method allows editing of the messages without digging through code
"""
owner = 115947067511144451
command_prefix = '$'
on_command_error_message_GenericMessage = \
    'Something terrible happened, sorry. My owner will fix it.'
on_command_error_message_CommandInvokeError = \
    'Sorry, I ran into a problem. I let my owner know and they will work on it!'

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=command_prefix, owner_id=owner, intents=intents)

start_time = time.time()


class DatabaseConnection:
    def __init__(self):
        self.connection = psycopg2.connect(database='boogerball')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()


class CustomError(Exception):
    pass


class CannotDirectMessage(CustomError):
    def __init__(self):
        super(CannotDirectMessage, self).__init__("User has DMs blocked")


Boogerball = DatabaseConnection()


def check_plural(number, caps: bool = False):
    if number == 1:
        return ""
    else:
        if caps:
            return "S"
        else:
            return "s"


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


def check_if_command_allowed(command, server, user):
    # TODO: Check if the user has permission to execute the command
    pass


def check_if_nsfw(ctx):
    """
    Checks if the server has the NSFW tag enabled. Used to check if certain commands, like spanking, can be run.
    :param ctx: The ID of the guild (or server) the command is being called from
    :return: a boolean 1 or 0. 1 means yes, the server is nsfw, 0 means no, it is not.
    """
    if isinstance(ctx, discord.ext.commands.Context):
        ID = ctx.message.guild.id
    elif isinstance(ctx, discord.Guild):
        ID = ctx.id
    else:
        print(type(ctx))
        return 0

    Boogerball.cursor.execute("SELECT nsfw FROM guilds WHERE ID = %(ID)s",
                              {'ID': str(ID)})
    nsfw = Boogerball.cursor.fetchone()
    if len(nsfw) == 0:
        return 0
    elif nsfw[0] is True:
        return 1
    else:
        return 0


def tuple_to_str(obj, joinchar):
    result = "{}".format(joinchar).join(obj)
    return result


async def emoji_menu(context, starting_message: str, starting_emoji: list, success_message: str,
                     failure_message: str, timeout_value: int = 60, direct_message: bool = False,
                     style: str = "custom"):
    """
    Presents a message with emoji for the user to react. Returns the message used for the selection and the index of
    the provided starting_emoji list that corresponds to the user selection.
    :param context: Must be a Message or Member from the Discord API, Member is used when using direct messages
    :param starting_message: The initial message the user will be shown to help them choose options
    :param starting_emoji: A list of emojis in string format that the user must choose from
    :param success_message: The prompted message will be edited to show this if the user picks something
    :param failure_message: The prompted message will be edited to show this if the user does not pick anything
    :param timeout_value: The time to wait for the user to pick an emoji before showing the failure_message
    :param direct_message: A boolean to signal the function if we're in a DM.
    :param style: Chooses a premade menu, rather than having to specify all parameters to build your own
    :return: Returns a discord.py Message object and an int
    """
    # If the context sent is a user instead of a message, we must change how the check_prompt logic works later.
    if type(context).__name__ == 'Member':
        compare_user = context
    else:
        compare_user = context.author

    # Present the message and add the provided emoji as options
    try:
        prompt_message = await context.send(starting_message)
        for emoji in starting_emoji:
            await prompt_message.add_reaction(str(emoji))

        # Wait for the player to react back to the message
        def check_prompt(reaction, user):
            return user == compare_user and str(reaction.emoji) in starting_emoji \
                and reaction.message.id == prompt_message.id

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check_prompt)

            reaction_index = starting_emoji.index(str(reaction.emoji))

            if direct_message is False:
                # You can't do this in a DM, so only do this if not in a DM.
                await prompt_message.clear_reactions()

            await prompt_message.edit(content=success_message)

            return prompt_message, reaction_index

        except asyncio.TimeoutError:
            await prompt_message.clear_reactions()
            await prompt_message.edit(content=failure_message, suppress=True, delete_after=timeout_value)
    except discord.Forbidden:
        raise CannotDirectMessage


async def admin_menu(author, guild):
    class Stop:
        value = 0

    while Stop.value != 1:
        prompt = 'Options for {}:\n\n🔞: Work with your server\'s NSFW tag\n👋: Close this menu'.format(guild)

        message, choice = await emoji_menu(context=author, starting_message=prompt, starting_emoji=['🔞', '👋'],
                                 success_message='Okay!', failure_message='Closing menu due to inactivity.',
                                 timeout_value=120, direct_message=True)

        dictionary_choice = {
            0: nsfw_menu,
            1: close_menu
        }
        Stop.value = await dictionary_choice[choice](author, guild)


async def nsfw_menu(author, guild):
    nsfw = check_if_nsfw(guild)
    dictionary_nsfw = {
        0: "OFF",
        1: "ON"
    }
    prompt = 'The NSFW tag for {} is currently: {}\n\nWhen this is ON, members can use NSFW commands.\n' \
             'What do you want to do with it?\n\n🔄: Switch the NSFW tag\n' \
             '🛑: Go back to the main menu'.format(guild, dictionary_nsfw[nsfw])
    message, choice = await emoji_menu(context=author, starting_message=prompt, starting_emoji=['🔄', '🛑'],
                                 success_message='Done!', failure_message='Closing menu due to inactivity.',
                                 timeout_value=120, direct_message=True)
    if choice == 0:
        new_nsfw = abs(nsfw - 1)
        dictionary_new_nsfw = {
            0: False,
            1: True
        }
        Boogerball.cursor.execute("UPDATE guilds SET nsfw = %(nsfw_flag)s WHERE ID = %(guild_id)s",
                                  {'nsfw_flag': str(dictionary_new_nsfw[new_nsfw]),
                                   'guild_id': str(guild.id)})

    return 0


async def close_menu(author, guild):
    return 1


@bot.event
async def on_ready():
    global tenor_token
    print('\n')
    print(f'{bot.user.name} has connected to Discord!')
    tenor_token = str(sys.argv[2])
    await bot.change_presence(activity=discord.Activity(name='$help', type=discord.ActivityType.listening))


@bot.event
async def on_command_error(ctx, error):
    error_parent_name = error.__class__.__name__

    dictionary_error = {
        "CommandInvokeError": str(on_command_error_message_CommandInvokeError),
        "CommandNotFound": False,
        "CheckFailure": False,
        "MissingRequiredArgument": "I think you forgot to add something there. Check help for info.",
        "BotMissingPermissions": "I don't have enough permissions to do do this! I need to manage emojis and manage"
                                 "messages. :(",
        "CannotDirectMessage": "I need to DM you to do this. Can you please allow DMs for a moment?"
    }

    if error_parent_name in dictionary_error.keys():
        if "CannotDirectMessage" in str(error):
            response = dictionary_error["CannotDirectMessage"]
        else:
            response = dictionary_error[error_parent_name]
    else:
        response = False

    with open('stderr.log', 'a') as s:
        output = 'Command Error: {}, raised: {} \nDuring: {}\n'.format(error_parent_name, str(error), ctx.invoked_with)
        s.write(output)

    if response is not False:
        with ctx.channel.typing():
            await ctx.send(response)


@bot.event
async def on_guild_join(guild):
    Boogerball.cursor.execute("INSERT INTO guilds (ID, nsfw) VALUES "
                              "(%(guild)s, false)",
                              {'guild': str(guild.id)})


@bot.event
async def on_member_join(member):
    # NOT IMPLEMENTED
    pass


@bot.command(name='ping', help='Responds to your message. Used for testing purposes.')
async def ping(ctx):
    response = 'Pong!'
    await ctx.send(response)


@bot.command(name='stop', hidden=True, aliases=['bye', 'ciao'])
@commands.is_owner()
async def stop(ctx):
    response = 'Ok bye!'
    await ctx.send(response)
    await bot.close()


@bot.command(name='stats', hidden=True, aliases=['stat', 'uptime'])
@commands.is_owner()
async def stats(ctx):
    uptime = round(time.time() - start_time)
    end_time_seconds = str(uptime % 60)
    end_time_minutes = str((uptime // 60) % 60)
    end_time_hours = str(((uptime // 60) // 60) % 24)
    end_time_days = str(((uptime // 60) // 60) // 24)
    end_time_string = "System Uptime: {} days, {} hours, {} minutes, {} seconds"\
        .format(end_time_days, end_time_hours, end_time_minutes, end_time_seconds)
    await ctx.send(end_time_string)


@bot.command(name='boop', help='boop someone!', hidden=True)
async def boop(ctx, booped):
    gif = tenor_get("cute nose boop", 12)
    if gif is None:
        pick_a_gif = None
    else:
        pick_a_gif = gif['results'][random.randint(0, len(gif['results']))]['media'][0]['gif']['url']
    response = '*boops {}* '.format(booped) + pick_a_gif
    await ctx.send(response)


@bot.command(name='wiki', aliases=['wikipedia', 'lookup'], help='Tries to look up something on wikipedia.')
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


@bot.command(name='rps', help='Rock paper scissors! Use "rps stats" for stats')
async def rps(ctx, selection='play'):
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

        # If the player is here to check their stats...
        if str(selection).lower() == 'stats':
            Boogerball.cursor.execute("SELECT * FROM rps WHERE playerID = %(playerID)s",
                                      {'playerID': str(ctx.message.author.id)})
            stats = Boogerball.cursor.fetchone()
            if stats is not None:
                response = "<@!%(authorid)d>'s stats:\nYou've won %(wincount)d game%(winplural)s, lost %(losecount)d," \
                           " and tied %(drawcount)d time%(drawplural)s" \
                           "\nYou've used rock %(rockcount)d time%(rockplural)s," \
                           " scissors %(sciscount)d time%(scisplural)s and paper %(papecount)d time%(papeplural)s" \
                           "\nYou've won %(streak)d game%(streakplural)s in a row and" \
                           " played %(playcount)d time%(playplural)s" % {
                                'authorid': ctx.message.author.id, 'wincount': stats[1],
                                'winplural': check_plural(stats[1]), 'losecount': stats[2], 'drawcount': stats[3],
                                'drawplural': check_plural(stats[3]), 'rockcount': stats[4],
                                'rockplural': check_plural(stats[4]), 'sciscount': stats[5],
                                'scisplural': check_plural(stats[5]), 'papecount': stats[6],
                                'papeplural': check_plural(stats[6]), 'streak': stats[7],
                                'streakplural': check_plural(stats[7]), 'playcount': stats[1] + stats[2] + stats[3],
                                'playplural': check_plural(stats[1] + stats[2] + stats[3])
                            }

            else:
                response = "I don't think you've played before, am I taking crazy pills?"
            await ctx.send(response)

        # If not, then the player must be here to play...
        elif str(selection).lower() == 'play':

            emoji_list = ["✊", "✋", "✌"]

            # Construct the game's prompt and get ready for the player's selection.
            prompt_message, player_pick = \
                await emoji_menu(context=ctx, starting_message="Oh you wanna go, huh? Choose your weapon then:",
                                 starting_emoji=emoji_list, failure_message="I didn't see a reaction from you,"
                                   "so I stopped.", timeout_value=60, success_message="Drumroll please...")

            if player_pick is not None:
                # We need to make a row for this player in the DB if this is their first time playing
                Boogerball.cursor.execute("SELECT playerID FROM rps WHERE playerID = %(playerID)s",
                                          {'playerID': str(ctx.message.author.id)})
                check = Boogerball.cursor.fetchall()
                if len(check) == 0:
                    Boogerball.cursor.execute("INSERT INTO rps (playerID, wincount, losecount, drawcount, rocktimes,"
                                              " scistimes, papetimes, streak) VALUES "
                                              "(%(playerID)s, 0, 0, 0, 0, 0, 0, 0)",
                                              {'playerID': str(ctx.message.author.id)})

                # Let the bot pick, too!
                bots_pick = random.randint(0, 2)

                # Let's log what the player picked for stat purposes
                player_sql_pick = rps_sql_dict[str(rps_dict[player_pick])]
                player_pick_sql = psycopg2.sql.SQL("""
                    UPDATE rps
                    SET {player_pick_column} = {player_pick_column} + 1
                    """).format(
                    player_pick_column=sql.Identifier(player_sql_pick))
                Boogerball.cursor.execute(player_pick_sql)

                # The player and bot have picked the same thing, tie game!
                if bots_pick == player_pick:
                    bots_response = 'Oh no! A tie! I picked {} too!'.format(rps_dict[bots_pick])
                    Boogerball.cursor.execute("UPDATE rps SET drawcount = drawcount + 1, streak = 0 WHERE "
                                              "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                # The player and the bot did not pick the same thing...
                else:
                    rps_matrix = [[-1, 1, 0], [1, -1, 2], [0, 2, -1]]
                    winner = rps_matrix[player_pick][bots_pick]

                    # The player won!
                    if winner == player_pick:
                        bots_response = 'Darn it! You win, I picked {}.'.format(rps_dict[bots_pick])
                        Boogerball.cursor.execute("UPDATE rps SET wincount = wincount + 1, streak = streak + 1 WHERE "
                                                  "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                    # The bot won!
                    else:
                        bots_response = 'Boom! Get roasted nerd! I picked {}!'.format(rps_dict[bots_pick])
                        Boogerball.cursor.execute("UPDATE rps SET losecount = losecount + 1, streak = 0 WHERE "
                                                  "playerID = %(playerID)s", {'playerID': str(ctx.message.author.id)})

                await prompt_message.edit(content=bots_response)

                # Let's check for a win streak and tell the whole channel if the person is on a roll!
                Boogerball.cursor.execute("SELECT streak FROM rps WHERE playerID = %(playerID)s",
                                          {'playerID': str(ctx.message.author.id)})
                streak_check = Boogerball.cursor.fetchone()
                if streak_check[0] % 3 == 0 and streak_check[0] > 1:
                    await ctx.send("Oh snap <@!{}>! You're on a roll! You've won {} games in a row!".format(
                        ctx.message.author.id, streak_check[0]))

        # The player did something wrong to end up here.
        else:
            bots_response = 'Huh, that was weird. I will tell my owner something went wrong here.'
            await ctx.send(bots_response)


@bot.command(name='roll', help='rolls a dice. Syntax is roll <number> d<sides of die>')
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


@bot.command(name='spank', help='Spanks people you mention. Keeps track, too!')
@commands.check(check_if_nsfw)
async def spank(ctx):
    async with ctx.channel.typing():
        if hasattr(ctx.message, 'raw_mentions'):
            if len(ctx.message.raw_mentions) > 0:
                for member_id in ctx.message.raw_mentions:
                    guild = ctx.author.guild

                    # Has this person been spanked before?
                    Boogerball.cursor.execute("SELECT ID FROM spanks WHERE ID = %(ID)s AND guild = %(guild)s",
                                              {'ID': str(member_id), 'guild': str(guild.id)})
                    check = Boogerball.cursor.fetchall()

                    # Make a new row if this is the first time this person has been spanked.
                    if len(check) == 0:
                        Boogerball.cursor.execute("INSERT INTO spanks (ID, guild, spanks) VALUES "
                                                  "(%(ID)s, %(guild)s, 1)",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Add to the spanks count if they've been here before.
                    else:
                        Boogerball.cursor.execute("UPDATE spanks SET spanks = spanks + 1 "
                                                  "WHERE ID = %(ID)s AND guild = %(guild)s",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Now get how many spanks they have in total.
                    Boogerball.cursor.execute("SELECT spanks FROM spanks WHERE ID = %(ID)s",
                                              {'ID': str(member_id)})
                    stats = Boogerball.cursor.fetchone()
                    spanks = stats[0]

                    # Let's have a few funny phrases to play with.
                    list_spank_phrases = [
                        "Lo! The spank bell doth toll for <@!{}>! Bask in the sound of a hand smacking the ass!"
                        " It has rung {} time{}!".format(str(member_id), str(spanks), check_plural(spanks)),
                        "Soups on! One spank for <@!{}>! Comin' right up! It's been served for them {} time{}!"
                        .format(str(member_id), str(spanks), check_plural(spanks)),
                        "THWACK! My favorite sound... And right now it's coming from <@!{}>'s ass!"
                        " I've heard it {} time{} so far!".format(str(member_id), str(spanks), check_plural(spanks)),
                        "M-M-M-MONSTER SPANK! GET DISCIPLINED <@!{}>! YOU'VE BEEN TAUGHT THIS LESSON {} TIME{}!"
                        .format(str(member_id), str(spanks), check_plural(spanks, caps=True))
                    ]

                    # Inform the victim of their spank!
                    await ctx.send(list_spank_phrases[random.randint(0, (len(list_spank_phrases) - 1))])

                    # Grab a spanking GIF from Tenor
                    spank_gif_search_terms = [
                        "spank", "bend over spank", "punishment spank", "discipline spank", "spanking", "ass smack"
                    ]
                    spank_gifs = tenor_get(
                        spank_gif_search_terms[random.randint(0, (len(spank_gif_search_terms) - 1))], 6)

                    pick_a_gif = \
                        spank_gifs['results'][random.randint(0, len(spank_gifs['results']) - 1)] \
                        ['media'][0]['gif']['url']

                    await ctx.send(pick_a_gif)

            else:
                await ctx.send("You didn't mention anyone! How will I ever know where to direct this frustration?!")


@bot.command(name='hug', help='Sends the user a hug GIF!')
async def hug(ctx):
    async with ctx.channel.typing():
        if hasattr(ctx.message, 'raw_mentions'):
            if len(ctx.message.raw_mentions) > 0:
                for member_id in ctx.message.raw_mentions:
                    guild = ctx.author.guild

                    # Has this person been hugged before?
                    Boogerball.cursor.execute(
                        "SELECT ID FROM hugs WHERE ID = %(ID)s AND guild = %(guild)s",
                        {'ID': str(member_id), 'guild': str(guild.id)})
                    check = Boogerball.cursor.fetchall()

                    # Make a new row if this is the first time this person has been hugged.
                    if len(check) == 0:
                        Boogerball.cursor.execute("INSERT INTO hugs (ID, guild, hugs) VALUES "
                                                  "(%(ID)s, %(guild)s, 1)",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Add to the hug count if they've been here before.
                    else:
                        Boogerball.cursor.execute("UPDATE hugs SET hugs = hugs + 1 "
                                                  "WHERE ID = %(ID)s AND guild = %(guild)s",
                                                  {'ID': str(member_id), 'guild': str(guild.id)})

                    # Let's have a few funny phrases to play with.
                    list_hug_phrases = [
                        "Special delivery for <@!{}>! Get hugged, nerd!"
                            .format(str(member_id)),
                        "Soups on! One hug for <@!{}>! Comin' right up!"
                            .format(str(member_id)),
                        "Guess who's getting a hug? <@!{}>!"
                            .format(str(member_id)),
                        "Extra! Extra! Read all about how <@!{}> is a cutie who got hugged!"
                            .format(str(member_id))
                    ]

                    # Inform the victim of their hug!
                    await ctx.send(list_hug_phrases[random.randint(0, (len(list_hug_phrases) - 1))])

                    # Grab a hugging GIF from Tenor
                    hug_gif_search_terms = [
                        "hug anime", "hug cute", "hug baymax", "hugging anime",
                        "snuggle cuddle hug cat love",
                        "tackle hug anime", "puppy cute hug", "animal cuddle hug"
                    ]
                    hug_gifs = tenor_get(
                        hug_gif_search_terms[random.randint(0, (len(hug_gif_search_terms) - 1))], 6)

                    pick_a_gif = \
                        hug_gifs['results'][random.randint(0, len(hug_gifs['results']) - 1)] \
                            ['media'][0]['gif']['url']

                    await ctx.send(pick_a_gif)

            else:
                await ctx.send(
                    "You didn't mention anyone! How will I ever know where to direct this frustration?!")


@bot.command(name='admin', help='Allows setup of various commands and permissions in the bot.')
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def admin(message):
    if message.author != bot.user:
        guild = message.author.guild
        user = message.author
        await admin_menu(user, guild)


@bot.event
async def on_message(message):
    if message.author != bot.user:
        channel = message.channel
        if re.search(r'\bdonald trump\b', message.content, flags=re.IGNORECASE) is not None:
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
