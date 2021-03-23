import discord
import random
import requests
import json
import re
import sys
import psycopg2
import asyncio
import datetime
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

start_time = datetime.datetime.now().replace(microsecond=0)

voting_messages = []
reacted_messages = []
queue_messages = []
queue_channel = None

baddog_images = [
    'https://tenor.com/view/lilo-and-stitch-stitch-bad-dog-spray-spraying-gif-5134293',
    'https://tenor.com/view/modern-family-goaway-squirt-bottle-shoo-gif-4979455',
    'https://tenor.com/view/gravity-falls-bill-gravityfalls-no-gif-14949051',
]

spank_images = [
    'https://tenor.com/view/spank-tomandjerry-gif-5196956',
    'https://tenor.com/view/spank-spanking-looneytunes-foghornleghorn-gif-7391212',
    'https://tenor.com/view/cats-funny-spank-slap-gif-15308590',
    'https://tenor.com/view/weeds-esteban-spanking-gif-4938822',
    'https://tenor.com/view/hot-spank-butt-slap-butt-butt-grab-gif-12569697',
    'https://tenor.com/view/office-gif-4457011',
    'https://tenor.com/view/slapping-gif-18392559',
    'https://tenor.com/view/bad-beat-spank-punishment-gif-13569259',
    'https://tenor.com/view/chris-jericho-trish-stratus-spanking-wwe-wwf-gif-14318603',
    'https://tenor.com/view/spanking-sexy-time-sex-cute-couple-bed-time-gif-17087903',
]

hug_images = [
    'https://tenor.com/view/anime-hug-sweet-love-gif-14246498',
    'https://tenor.com/view/hug-anime-gif-10195705',
    'https://tenor.com/view/hug-anime-gif-11074788',
    'https://tenor.com/view/hug-cuddle-comfort-love-friends-gif-5166500',
    'https://tenor.com/view/hug-anime-sweet-couple-gif-12668480',
    'https://tenor.com/view/hug-anime-gif-7552077',
    'https://tenor.com/view/hug-kon-anime-sweet-cute-gif-17509833',
    'https://tenor.com/view/anime-hug-hug-hugs-anime-girl-anime-girl-hug-gif-16787485',
    'https://tenor.com/view/hugmati-gif-18302861',
    'https://tenor.com/view/sweet-kitty-love-cats-couple-gif-12796047',
    'https://tenor.com/view/cat-love-huge-hug-big-gif-11990658',
    'https://tenor.com/view/cuddle-love-cat-gif-13393256',
    'https://tenor.com/view/anh-thien-be-heo-chuppy-bunny-hug-love-couple-gif-17750801',
    'https://tenor.com/view/cuddle-hug-anime-bunny-costumes-happy-gif-17956092',
    'https://tenor.com/view/good-night-mommy-cuddle-koala-gif-18431601',
]


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


async def poll_check(poll_channel, announce_channel):
    while True:
        threshold = datetime.datetime.now() - datetime.timedelta(weeks=1)
        channel = poll_channel
        message = await channel.history(limit=1, oldest_first=False).flatten()
        date = message[0].created_at

        if date > threshold:
            await announce_channel.send("There's a poll running! Head to {} to cast your vote!".format(channel.mention))

        # Repeat once every 12 hours
        await asyncio.sleep(43200)

        # Repeat every minute for testing
        # await asyncio.sleep(60)


@bot.event
async def on_ready():
    global tenor_token
    print('\n')
    print(f'{bot.user.name} has connected to Discord!')
    tenor_token = str(sys.argv[2])
    await bot.change_presence(activity=discord.Activity(name='$help', type=discord.ActivityType.listening))

    # Repopulate the voting messages in case of a bot reboot
    Boogerball.cursor.execute('SELECT message_ID FROM admissions')
    for ID in Boogerball.cursor.fetchall():
        voting_messages.append(ID[0])

    # Announces if there is a recent poll in the server
    poll_channel = await bot.fetch_channel(787401853809328148)
    announce_channel = await bot.fetch_channel(766490733632553004)
    await poll_check(poll_channel, announce_channel)

    # Only if you need to leave a guild
    """
    guilds = await bot.fetch_guilds().flatten()
    for guild in guilds:
        if 782196191935987732 == guild.id:
            guild = await bot.fetch_guild(782196191935987732)
            await guild.leave()
    """


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
    if member.guild.id == 782243401809920030:
        voting_channel = await bot.fetch_channel(787449046271918080)
        welcome_channel = await bot.fetch_channel(782292714845634601)

        await welcome_channel.send("Welcome to our cottage, <@!{}>! Please relax and be patient. Our community wants "
                                   "to stay chill, so we may want to get to know you before letting you in. Someone "
                                   "will come say hello soon!".format(member.id))

        voting_message = await voting_channel.send("<@!{}> has joined our server. Please get to know them and "
                                                   "vote here whether or not to let them in.".format(member.id))

        await voting_message.add_reaction("👍")
        await voting_message.add_reaction("👎")

        Boogerball.cursor.execute("INSERT INTO admissions (message_ID, member_ID) VALUES (%(one)s, %(two)s)",
                                  {'one': str(voting_message.id), 'two': str(member.id)})

        voting_messages.append(voting_message.id)

    else:
        pass


@bot.event
async def on_member_remove(member):
    if member.guild.id == 782243401809920030:
        Boogerball.cursor.execute('SELECT message_ID FROM admissions WHERE member_ID = %(one)s',
                                  {'one': str(member.id)})
        result = Boogerball.cursor.fetchone()

        if result is not None:
            result = result[0]
            voting_channel = await bot.fetch_channel(787449046271918080)
            message = await voting_channel.fetch_message(result)
            await message.edit(content=message.content + "\n\nUPDATE: This user left our server.")

            try:
                voting_messages.remove(result)
            except ValueError:
                pass

            Boogerball.cursor.execute('DELETE FROM admissions WHERE member_ID = %(one)s',
                                      {'one': str(member.id)})
        else:
            pass

        departure_channel = await bot.fetch_channel(787448656382787614)
        await departure_channel.send("{} has left the server.".format(member.name))
    else:
        pass


@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id in voting_messages:
        voting_channel = await bot.fetch_channel(787449046271918080)
        message = await voting_channel.fetch_message(payload.message_id)

        moderator_role = message.guild.get_role(782291841060044848)
        admission_role = message.guild.get_role(782292198183272448)

        moderator_count = len(moderator_role.members)
        majority = max(moderator_count // 3 + 1, 2)

        green = discord.utils.get(message.reactions, emoji="👍")
        red = discord.utils.get(message.reactions, emoji="👎")

        if green.count >= majority:
            Boogerball.cursor.execute('SELECT member_ID FROM admissions WHERE message_ID = %(one)s',
                                      {'one': str(payload.message_id)})
            result = Boogerball.cursor.fetchone()

            if result is not None:
                result = result[0]
                try:
                    newbie = await message.guild.fetch_member(result)
                except discord.errors.NotFound:
                    newbie = None
            else:
                newbie = None

            if newbie is not None:
                await newbie.add_roles(admission_role, reason='The community voted to allow them in.')
                await message.edit(content=message.content + "\n\nUPDATE: We confirmed this user!")

            voting_messages.remove(payload.message_id)
            Boogerball.cursor.execute('DELETE FROM admissions WHERE message_ID = %(one)s',
                                      {'one': str(payload.message_id)})
        if red.count >= majority:
            Boogerball.cursor.execute('SELECT member_ID FROM admissions WHERE message_ID = %(one)s',
                                      {'one': str(payload.message_id)})
            result = Boogerball.cursor.fetchone()[0]

            voting_messages.remove(payload.message_id)
            Boogerball.cursor.execute('DELETE FROM admissions WHERE message_ID = %(one)s',
                                      {'one': str(payload.message_id)})

            if result is not None:
                try:
                    newbie = await message.guild.fetch_member(result)
                except discord.errors.NotFound:
                    newbie = None
            else:
                newbie = None

            if newbie is not None:
                await message.guild.ban(newbie, reason='The community voted to reject you. Goodbye.')
                await message.edit(content=message.content + "\n\nUPDATE: We rejected this user.")

    elif payload.message_id in queue_messages:
        if payload.user_id != 766694635208310794:
            global queue_channel
            message = await queue_channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji)

            cancel = discord.utils.get(message.reactions, emoji="❌")

            if cancel > 0:
                queue_messages.clear()

    else:
        pass


@bot.event
async def on_reaction_add(reaction, user):
    if reaction.message.id in voting_messages:
        pass
    else:
        global reacted_messages
        guild = await bot.fetch_guild(782243401809920030)
        if reaction.message.guild == guild:
            spray = discord.utils.get(guild.emojis, id=784805549686259763)
            message = await reaction.message.channel.fetch_message(reaction.message.id)

            sprays = discord.utils.get(message.reactions, emoji=spray)

            if sprays is not None and sprays.count >= 3 and reaction.message.id not in reacted_messages:
                reacted_messages.append(reaction.message.id)
                image = baddog_images[random.randint(0, (len(baddog_images) - 1))]
                await reaction.message.channel.send("<@!{}>\n{}".format(reaction.message.author.id, image))


@bot.command(name='bump', help='Pretends to bump the server :P')
async def bump(ctx):
    global start_time
    difference = datetime.datetime.now().replace(microsecond=0) - start_time
    threshold = datetime.timedelta(hours=2)

    if difference >= threshold:
        await ctx.send("Server bumped! (Or was it?) 👍")
        thumbs_up = tenor_get(
            "thumbs up anime", 12)

        pick_a_gif = thumbs_up['results'][random.randint(0, 11)]['media'][0]['gif']['url']

        start_time = datetime.datetime.now().replace(microsecond=0)

        await ctx.send(pick_a_gif)
    else:
        delay = datetime.timedelta(hours=2) - difference
        await ctx.send("Ouch! Too fast! (or maybe too hard?) Wait {} before trying again."
                       .format(delay))


@bot.command(name='test_history', help='Looks at how old messages are in the channel')
async def test_history(ctx):
    poll_channel = await bot.fetch_channel(787401853809328148)
    announce_channel = await bot.fetch_channel(766490733632553004)
    await poll_check(poll_channel, announce_channel)


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
    uptime = datetime.datetime.now().replace(microsecond=0) - start_time
    end_time_string = "System Uptime: {}"\
        .format(uptime)
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

                    pick_a_gif = \
                        spank_images[random.randint(0, len(spank_images) - 1)]

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

                    pick_a_gif = \
                        hug_images[random.randint(0, len(hug_images) - 1)]
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


@bot.command(name='talk', help='Starts a speaking queue to manage conversations')
@commands.guild_only()
async def talk(message):
    if len(queue_messages) == 0:
        global queue_channel

        opening_message_dict = {
            "title": "Talking Queue",
            "colour": "#FFFFFF",
            "description": "Hey! You've started a talking queue! \nIf you want to talk, react with 👋"
                           "\nTo pass your turn to the next person, react with 🏁"
                           "\nTo stop the queue, react with ❌"
                           "\nIf you leave the voice chat, you have 1 minute to reconnect!"
                           "\n\nQueue:\nEmpty"
        }
        opening_message = discord.embeds.Embed.from_dict(opening_message_dict)

        queue_message = await message.channel.send(embed=opening_message)
        queue_messages.append(queue_message)

        queue_channel = message.channel
        await queue_message.add_reaction("👋")
        await queue_message.add_reaction("🏁")

    else:
        await message.channel.send("I'm already running a queue! I can't be in two places at once :(")


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
