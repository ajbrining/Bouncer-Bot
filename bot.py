import discord
from discord.utils import get
from discord.ext import commands
from yaml import load, FullLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import Intro, Server, Base

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

# initialize in-memory sqlite session
memory_engine = create_engine('sqlite:///:memory:')
Memory = sessionmaker(bind=memory_engine)
memory = Memory()

# initialize on-disk sqlite session
storage_engine = create_engine('sqlite:///sqlite.db')
Storage = sessionmaker(bind=storage_engine)
storage = Storage()

# perform all needed sql things that we've abstracted
Base.metadata.create_all(memory_engine)
Base.metadata.create_all(storage_engine)

# posts the intro and is only called once all info has been collected
async def send_intro(data):
    server = client.get_guild(data.server)
    member = get(server.members, id=data.id)

    query = storage.query(Server).filter_by(id=server.id)
    server_config = query.first()

    member_role = get(server.roles, id=server_config.member_role)
    unveri_role = get(server.roles, id=server_config.unveri_role)
    await member.add_roles(member_role)
    await member.remove_roles(unveri_role)

    if data.age >= 18:
        age = '18+'

        adult_role = get(server.roles, id=server_config.adult_role)
        await member.add_roles(adult_role)

        if data.nsfw:
            nsfw_role = get(server.roles, id=server_config.nsfw_role)
            await member.add_roles(nsfw_role)
    else:
        age = 'Minor'

        minor_role = get(server.roles, id=server_config.minor_role)
        await member.add_roles(minor_role)

    message = "Welcome, {0}!\nName: {1}\nAge: {2}\nPronouns: {3}\nAbout Me: {4}"
    message = message.format(member.mention, data.name, age, data.pronouns, data.about)
    channel = get(server.channels, id=server_config.intro_channel)
    await channel.send(message)

    await client.get_user(data.id).send("Okay, you're all set! Be sure to stop by #role-react so you can grab any additional roles you want.")
    memory.query(Intro).filter_by(id=data.id).delete()

async def init_intro(user, server):
    intro = Intro(id=user.id, server=server.id, question=1)

    memory.add(intro)
    memory.commit()

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
    server_config = Server(id=server.id)

    storage.add(server_config)
    storage.commit()

@client.event
async def on_guild_remove(server):
    storage.query(Server).filter_by(id=server.id).delete()
    memory.query(Intro).filter_by(server=server.id).delete()

@client.event
async def on_member_join(member):
    await init_intro(member, member.guild)

@client.event
async def on_member_remove(member):
    memory.query(Intro).filter_by(id=member.id).delete()
    query = storage.query(Server).filter_by(id=member.guild.id)
    server_config = query.first()
    channel = get(member.guild.channels, name=server_config.intro_channel)
    async for message in channel.history():
        if member.mentioned_in(message) or member.id == message.author.id:
            await message.delete()

@client.event
async def on_message(message):
    if type(message.channel) is not discord.DMChannel:
        await client.process_commands(message)
        return

    if message.author != client.user:
        query = memory.query(Intro).filter_by(id=message.author.id)
        result = query.first()
        if result:
            if result.question == 1:
                try:
                    age = int(message.content)

                    query = storage.query(Server).filter_by(id=result.server)
                    server_config = query.first()

                    server = client.get_guild(server_config.id)

                    log_channel = get(server.channels, id=server_config.log_channel)
                    mod_role = get(server.roles, id=server_config.mod_role)
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

                    memory.query(Intro).filter_by(id=message.author.id).update({'age': age, 'question': 2})
                    await message.author.send("What name would you like to be called?")
                except ValueError:
                    await message.author.send("Please respond with a numeric value.")
            elif result.question == 2:
                name = message.content
                memory.query(Intro).filter_by(id=message.author.id).update({'name': name, 'question': 3})
                await message.author.send("What are your preferred pronouns?")
            elif result.question == 3:
                pronouns = message.content
                memory.query(Intro).filter_by(id=message.author.id).update({'pronouns': pronouns, 'question': 4})
                await message.author.send("Tell us about yourself in a sentence.")
            elif result.question == 4:
                about = message.content
                memory.query(Intro).filter_by(id=message.author.id).update({'about': about, 'question': 5})
                if result.age >= 18:
                    await message.author.send("Do you want to access NSFW content? (a Mod/Admin can help if you change your mind)")
                else:
                    query = memory.query(Intro).filter_by(id=message.author.id)
                    result = query.first()
                    await send_intro(result)
            elif result.question == 5:
                if result.age < 18:
                    return
                if message.content.lower() in config['yes_words']:
                    nsfw = True
                elif message.content.lower() in config['no_words']:
                    nsfw = False
                else:
                    await message.author.send("I'm sorry, I didn't get that. Please answer 'yes' or 'no'.")
                    return

                result.nsfw = nsfw

                await send_intro(result)

        else: 
            test_id = 0
            server = None
            while not server:
                server_config = storage.query(Server).order_by(Server.id.asc().filter(Server.id > test_id).first())
                if not server_config:
                    break

                test_id = server_config.id
                test_server =  client.get_guild(test_id)
                if test_server.get_member(message.author.id):
                    server = test_server

            if server:
                channel = get(server.channels, id=server_config.intro_channel)
                intros = []
                async for intro in channel.history():
                    if str(message.author.id) in intro.content or message.author.id == intro.author.id:
                        intros.append(intro)
                        break

                if intros:
                    await message.author.send("It looks like you've already got an intro. If you are missing any roles or are having any issues, please contact a Mod or Admin.")
                else:
                    await init_intro(message.author)
            else:
                await message.author.send("Do I know you? It looks like we aren't in any servers together.")

@client.command(name='help')
async def _help(context):
    help_text = "**Commands**:\n\n" \
                + "**set_channel**\n" \
                + "> **Description**: Sets the any of the following channel settings:\n" \
                + ">     *intros* - the channel that the introductions will be posted in\n" \
                + ">     *logs* - the channel where messages to moderators will go\n" \
                + "> **Example**: @Bouncer Bot set_channel intros introductions\n\n" \
                + "**set_role**\n" \
                + "> **WARNING: Be sure to put the name of the role in quotes**\n" \
                + "> **Description**: Sets the any of the following role settings:\n" \
                + ">     *moderator* - the role that is given to mods, will be used for @ mentions\n" \
                + ">     *unverified* - the role for those who have not been verified, will be removed upon introduction\n" \
                + ">     *verified* - the role to be given to those who give an introduction\n" \
                + ">     *nsfw* - the role that should be given to those who wish to access NSFW channels\n" \
                + ">     *minor* - the role that is given to those under 18\n" \
                + ">     *adult* - the role that is given to those over 18\n" \
                + "> **Example**: @Bouncer Bot set minor \"Under 18\"\n\n" \
                + "**status**\n" \
                + "> **Description**: Shows all settings and what they are set to. Takes no arguments. " \
                + "> **Example**: @Bouncer Bot status"

    await context.send(help_text)

@client.command()
async def set_channel(context, setting, *, channel: discord.TextChannel):
    if setting == "intros":
        storage.query(Server).filter_by(id=context.guild.id).update(intro_channel=channel.id)
    elif setting == "logs":
        storage.query(Server).filter_by(id=context.guild.id).update(log_channel=channel.id)
    else:
        await context.send("The setting \"{0}\" does not exist.".format(setting))
        return

    await context.send("Success: {0} channel set to {1}.".format(setting, channel.mention))

@set_channel.error
async def channel_error(context, error):
    if isinstance(error, commands.ChannelNotFound):
        await context.send("**ERROR**: channel \"{0}\" does not exist in this server.".format(error.args))

@client.command()
async def set_role(context, setting, *, role: discord.Role):
    if setting == "moderator":
        storage.query(Server).filter_by(id=context.guild.id).update(mod_role=role.id)
    elif setting == "unverified":
        storage.query(Server).filter_by(id=context.guild.id).update(unveri_role=role.id)
    elif setting == "verified":
        storage.query(Server).filter_by(id=context.guild.id).update(member_role=role.id)
    elif setting == "nsfw":
        storage.query(Server).filter_by(id=context.guild.id).update(nsfw_role=role.id)
    elif setting == "minor":
        storage.query(Server).filter_by(id=context.guild.id).update(minor_role=role.id)
    elif setting == "adult":
        storage.query(Server).filter_by(id=context.guild.id).update(adult_role=role.id)
    else:
        await context.send("The setting \"{0}\" does not exist.".format(setting))
        return

    await context.send("Success: {0} role set to {1}.".format(setting, channel.mention))
    
@set_role.error
async def role_error(context, error):
    if isinstance(error, commands.RoleNotFound):
        await context.send("**ERROR**: channel \"{0}\" does not exist in this server.".format(error.args))

@client.command()
async def status(context):
    server_config = storage.query(Server).filter_by(id=context.guild.id).first()
    delattr(server_config, id)

    message = ''
    for setting, value in server_config.__dict__:
        if not value:
            message += '**{0} is not set!**\n'.format(setting)
        else:
            if 'role' in setting:
                role = get(context.guild.roles, id=value)
                message += '{0} is set to {1}.\n'.format(setting, role.mention)
            else:
                channel = get(context.guild.channels, id=value)
                message += '{0} is set to {1}.\n'.format(setting, channel.mention)

    message = message[:-1:] # remove the trailing linebreak

    await context.send(message)

if __name__ == '__main__':
    client.run(config['bot_token'])
