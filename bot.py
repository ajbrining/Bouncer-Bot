import discord
from discord.utils import get
from discord.ext import commands
from yaml import load, FullLoader
import pymongo


# set up intents
intents = discord.Intents.default()
intents.members = True

# create our client object
client = commands.Bot(command_prefix=commands.when_mentioned,
                      help_command=None,
                      intents=intents)

# load the configuration file
with open('config.yaml') as f:
    config = load(f, Loader=FullLoader)

# connect to mongodb, get our database, and load collections
mongo = pymongo.MongoClient()
db = mongo.bouncer_bot
intros = db.intros
servers = db.servers

# a list of the settings that can be stored in the DB
settings = ['intro_channel', 'log_channel', 'mod_role',
            'unveri_role', 'verified_role', 'nsfw_role',
            'minor_role', 'adult_role']
alias = {'intros': 'intro_channel',
         'logs': 'log_channel',
         'moderator': 'mod_role',
         'unverified': 'unveri_role',
         'verified': 'verified_role',
         'nsfw': 'nsfw_role',
         'minor': 'minor_role',
         'adult': 'adult_role'}

# posts the intro and is only called once all info has been collected
async def send_intro(user_id):
    intro = intros.find_one({'_id': user_id})

    server = client.get_guild(intro['server'])
    member = get(server.members, id=user_id)

    server_config = servers.find_one({'_id': server.id})

    verified_role = get(server.roles, id=server_config['verified_role'])
    await member.add_roles(verified_role)

    try:
        unveri_role = get(server.roles, id=server_config['unveri_role'])
        await member.remove_roles(unveri_role)
    except KeyError:
        pass

    if intro['age'] >= 18:
        age = '18+'

        adult_role = get(server.roles, id=server_config['adult_role'])
        await member.add_roles(adult_role)

        if intro['nsfw']:
            nsfw_role = get(server.roles, id=server_config['nsfw_role'])
            await member.add_roles(nsfw_role)
    else:
        age = 'Minor'

        minor_role = get(server.roles, id=server_config['minor_role'])
        await member.add_roles(minor_role)

    message = "Welcome, {0}!\nName: {1}\nAge: {2}\nPronouns: {3}\nAbout Me: {4}"
    message = message.format(member.mention, intro['name'], age, intro['pronouns'], intro['about'])
    channel = get(server.channels, id=server_config['intro_channel'])
    await channel.send(message)

    await client.get_user(intro['_id']).send("Okay, you're all set. Be good and have fun!")
    intros.delete_one({'_id': intro.id, 'server': server.id})

async def init_intro(user, server):
    intros.insert_one({'_id': user.id, 'server': server.id, 'question': 1})

    await user.send("Hey there, welcome to **" + server.name + "**! Let's get your introduction taken care of so you can access the whole server. \n"
                    + "I'm going to ask you 4 or 5 questions, and I'll post your answers as your introduction for everyone to see. \n"
                    + "If you don't want to do that, there's no harm in leaving. Once you're gone I'll forget you were ever here!\n\n"
                    + "First off, how old are you? (we wont post your age, only a label such as 'Minor' or '18+')")

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
    activity = discord.Activity(name='for newcomers', type=discord.ActivityType.watching)
    await client.change_presence(activity=activity)

@client.event
async def on_guild_join(server):
    servers.insert_one({'_id': server.id})

@client.event
async def on_guild_remove(server):
    servers.delete_one({'_id': server.id})
    intros.delete_many({'server': server.id})

@client.event
async def on_member_join(member):
    await init_intro(member, member.guild)

@client.event
async def on_member_remove(member):
    try:
        intros.delete_one({'_id': member.id, 'server': member.guild.id})
    except pymongo.errors.InvalidOperation:
        pass
    server_config = servers.find_one({'_id': member.guild.id})
    channel = get(member.guild.channels, id=server_config['intro_channel'])
    async for message in channel.history():
        if member.mentioned_in(message) or member.id == message.author.id:
            await message.delete()

@client.event
async def on_message(message):
    if type(message.channel) is not discord.DMChannel:
        await client.process_commands(message)
        return

    if message.author != client.user:
        intro = intros.find_one({'_id': message.author.id})
        if not intro:
            found_server = None
            for server in message.author.mutual_guilds:
                server_config = servers.find_one({'_id': server.id})
                channel = get(server.channels, id=server_config['intro_channel'])

                posted_intros = []
                async for post in channel.history()
                    if str(message.author.id) in post.content or message.author.id == post.author.id:
                        posted_intros.append(intro)
                        break
                if not posted_intros:
                    init_intro(message.author, server)

            if not found_server:
                await message.author.send("It looks like you've already got an intro. If you are missing any roles or are having any issues, please contact a Mod or Admin.")
        else:
            if intro['question'] == 1:
                try:
                    age = int(message.content)

                    server_config = servers.find_one({'_id': intro['server']})

                    server = client.get_guild(server_config['_id'])

                    log_channel = get(server.channels, id=server_config['log_channel'])
                    mod_role = get(server.roles, id=server_config['mod_role'])
                    member = get(server.members, id=message.author.id)
                    if age < 13:
                        await message.author.send("I'm sorry, but it is against Discord's Terms of Service for people under the age of 13 to use Discord.\n"
                                                  + "In order to maintain our compliance with Discord's ToS, you have been removed from the server.\n"
                                                  + "You are more than welcome to rejoin once you are 13 or older.")

                        mod_message = "{mods}: {user} has been kicked for being underage."
                        mod_message = mod_message.format(mods=mod_role.mention, user=member.mention)
                        await log_channel.send(mod_message)

                        await member.kick(reason="Under 13")

                        return
                    elif age > 100:
                        await message.author.send("Very funny, but I'd appreciate it if you gave me your real age.")

                        mod_message = "{mods}: {user} lied about their age ({age})"
                        mod_message = mod_message.format(mods=mod_role.mention, user=message.author.mention, age=str(age))
                        await log_channel.send(mod_message)

                        return
                    elif age >= 40:
                        await message.author.send("ok boomer")

                        mod_message = "{mods}: {user} is a boomer ({age})"
                        mod_message = mod_message.format(mods=mod_role.mention, user=message.author.mention, age=str(age))
                        await log_channel.send(mod_message)

                    intros.update_one({'_id': message.author.id}, {'$set': {'question': 2, 'age': age}})
                    await message.author.send("What name would you like to be called?")
                except ValueError:
                    await message.author.send("Please respond with a numeric value.")
            elif intro['question'] == 2:
                name = message.content
                intros.update_one({'_id': message.author.id}, {'$set': {'name': name, 'question': 3}})
                await message.author.send("What are your preferred pronouns?")
            elif intro['question'] == 3:
                pronouns = message.content
                intros.update_one({'_id': message.author.id}, {'$set': {'pronouns': pronouns, 'question': 4}})
                await message.author.send("Tell us about yourself in a sentence.")
            elif intro['question'] == 4:
                about = message.content
                intros.update_one({'_id': message.author.id}, {'$set': {'about': about}})
                if intro['age'] >= 18:
                    intros.update_one({'_id': message.author.id}, {'$set': {'question': 5}})
                    await message.author.send("Do you want to access NSFW content? (a Mod/Admin can help if you change your mind)")
                else:
                    await send_intro(message.author.id)
            elif intro['question'] == 5:
                if message.content.lower() in config['yes_words']:
                    nsfw = True
                elif message.content.lower() in config['no_words']:
                    nsfw = False
                else:
                    await message.author.send("I'm sorry, I didn't get that. Please answer 'yes' or 'no'.")
                    return

                intros.update_one({'_id': message.author.id}, {'$set': {'nsfw': nsfw}})

                await send_intro(message.author.id)

@client.command(name='help')
async def _help(context):
    help_text = "**Commands**:\n\n" \
                + "**set_channel**\n" \
                + "> **Description**: Sets the any of the following channel settings:\n" \
                + ">     *intros* - the channel that the introductions will be posted in\n" \
                + ">     *logs* - the channel where messages to moderators will go\n" \
                + "> **Example**: @Bouncer Bot set_channel intros introductions\n\n" \
                + "**set_role**\n" \
                + "> **WARNING: Be sure to @ the role or put the name of the role in quotes**\n" \
                + "> **Description**: Sets the any of the following role settings:\n" \
                + ">     *moderator* - the role that is given to mods, will be used for @ mentions\n" \
                + ">     *unverified* - the role for those who have not been verified, will be removed upon introduction\n" \
                + ">     *verified* - the role to be given to those who give an introduction\n" \
                + ">     *nsfw* - the role that should be given to those who wish to access NSFW channels\n" \
                + ">     *minor* - the role that is given to those under 18\n" \
                + ">     *adult* - the role that is given to those over 18\n" \
                + "> **Example**: @Bouncer Bot set_role minor \"Under 18\"\n\n" \
                + "**status**\n" \
                + "> **Description**: Shows all settings and what they are set to. Takes no arguments.\n" \
                + "> **Example**: @Bouncer Bot status"

    await context.send(help_text)

@client.command()
async def set_channel(context, setting, channel: discord.TextChannel):
    if setting in alias and 'channel' in alias[setting]:
        servers.update_one({'_id': context.guild.id}, {'$set': {alias[setting]: channel.id}})
    else:
        await context.send("The setting \"{0}\" doesn't make sense.".format(setting))
        return

    await context.send("Success: {0} channel set to {1}.".format(setting, channel.mention))

@set_channel.error
async def channel_error(context, error):
    if isinstance(error, commands.ChannelNotFound):
        await context.send("**ERROR**: " + error.args[0])
    else:
        raise error

@client.command()
async def set_role(context, setting, role: discord.Role):
    if setting in alias and 'role' in alias[setting]:
        servers.update_one({'_id': context.guild.id}, {'$set': {alias[setting]: role.id}})
    else:
        await context.send("The setting \"{0}\" doesn't make sense.".format(setting))
        return

    await context.send("Success: {0} role set to {1}.".format(setting, role.mention))

@set_role.error
async def role_error(context, error):
    if isinstance(error, commands.RoleNotFound):
        await context.send("**ERROR**: " + error.args[0])
    else:
        raise error

@client.command()
async def status(context):
    server_config = servers.find_one({'_id': context.guild.id}, projection={'_id': False})

    expected = list(settings)

    message = ''
    for setting, value in server_config.items():
        expected.remove(setting)

        if 'role' in setting:
            role = get(context.guild.roles, id=value)
            message += '{0} is set to {1}.\n'.format(setting, role.mention)
        else:
            channel = get(context.guild.channels, id=value)
            message += '{0} is set to {1}.\n'.format(setting, channel.mention)

    for setting in expected:
        message += '**{0} is not set!**\n'.format(setting)

    message = message[:-1:] # remove the trailing linebreak

    await context.send(message)

if __name__ == '__main__':
    client.run(config['bot_token'])
