import discord
from discord.utils import get
from yaml import load, FullLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean

# create our client object
client = discord.Client()

# load the configuration file
with open('config.yaml') as f:
    config = load(f, Loader=FullLoader)

# initialize sqlite session in memory (doesn't need to write to disk at this time)
engine = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=engine)
session = Session()

# prepare the model for the intros table
Base = declarative_base()
class Intro(Base):
    __tablename__ = 'intros'

    id = Column(Integer, primary_key=True)
    question = Column(Integer)
    age = Column(Integer)
    name = Column(String)
    pronouns = Column(String)
    about = Column(String)
    nsfw = Column(Boolean)

# perform all needed sql things that we've abstracted
Base.metadata.create_all(engine)

# posts the intro and is only called once all info has been collected
async def send_intro(data):
    server = client.get_guild(config['server_id'])
    member = get(server.members, id=data.id)

    member_role = get(server.roles, name=config['member_role'])
    unveri_role = get(server.roles, name=config['unveri_role'])
    await member.add_roles(member_role)
    await member.remove_roles(unveri_role)

    if data.age >= 18:
        age = '18+'

        adult_role = get(server.roles, name=config['adult_role'])
        await member.add_roles(adult_role)

        if data.nsfw:
            nsfw_role = get(server.roles, name=config['nsfw_role'])
            await member.add_roles(nsfw_role)
    else:
        age = 'Minor'

        minor_role = get(server.roles, name=config['minor_role'])
        await member.add_roles(minor_role)

    message = "Welcome, {0}!\nName: {1}\nAge: {2}\nPronouns: {3}\nAbout Me: {4}"
    message = message.format(member.mention, data.name, age, data.pronouns, data.about)
    channel = get(server.channels, name=config['intro_channel'])
    await channel.send(message)

    await client.get_user(data.id).send("Okay, you're all set! Be sure to stop by #role-react so you can grab any additional roles you want.")
    session.query(Intro).filter_by(id=data.id).delete()

async def init_intro(user):
    intro = Intro(id=user.id, question=1)

    session.add(intro)
    session.commit()

    server = client.get_guild(config['server_id'])

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
async def on_member_join(member):
    await init_intro(member)

@client.event
async def on_member_remove(member):
    session.query(Intro).filter_by(id=member.id).delete()
    # TODO: look for their introduction and remove it if they have one
    channel = get(member.guild.channels, name=config['intro_channel'])
    async for message in channel.history():
        if member.mentioned_in(message) or member.id == message.author.id:
            await message.delete()

@client.event
async def on_message(message):
    if type(message.channel) is discord.DMChannel and message.author != client.user:
        query = session.query(Intro).filter_by(id=message.author.id)
        result = query.first()
        if result:
            if result.question == 1:
                try:
                    age = int(message.content)
                    server = client.get_guild(config['server_id'])
                    log_channel = get(server.channels, name=config['log_channel'])
                    mod_role = get(server.roles, name=config['mod_role'])
                    member = get(server.members, id=message.author.id)
                    if age < 13:
                        await message.author.send("I'm sorry, but it is against Discord's Terms of Service for people under the age of 13 to use Discord.\n"
                                                  + "In order to maintain our compliance with Discord's ToS, you have been removed from the server.\n"
                                                  + "You are more than welcome to rejoin once you are 13 or older.")

                        mod_message = "{mods}: {user} has been kicked for being underage."
                        mod_message = mod_message.format(mods=mod_role.mention, user=message.author.mention)
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

                    session.query(Intro).filter_by(id=message.author.id).update({'age': age, 'question': 2})
                    await message.author.send("What name would you like to be called?")
                except ValueError:
                    await message.author.send("Please respond with a numeric value.")
            elif result.question == 2:
                name = message.content
                session.query(Intro).filter_by(id=message.author.id).update({'name': name, 'question': 3})
                await message.author.send("What are your preferred pronouns?")
            elif result.question == 3:
                pronouns = message.content
                session.query(Intro).filter_by(id=message.author.id).update({'pronouns': pronouns, 'question': 4})
                await message.author.send("Tell us about yourself in a sentence.")
            elif result.question == 4:
                about = message.content
                session.query(Intro).filter_by(id=message.author.id).update({'about': about, 'question': 5})
                if result.age >= 18:
                    await message.author.send("Do you want to access NSFW content? (a Mod/Admin can help if you change your mind)")
                else:
                    query = session.query(Intro).filter_by(id=message.author.id)
                    result = query.first()
                    await send_intro(result)
            elif result.question == 5:
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
            server = client.get_guild(config['server_id'])
            channel = get(server.channels, name=config['intro_channel'])
            intros = []
            async for intro in channel.history():
                if str(message.author.id) in intro.content or message.author.id == intro.author.id:
                    intros.append(intro)
                    break

            if intros:
                await message.author.send("It looks like you've already got an intro. If you are missing any roles or are having any issues, please contact a Mod or Admin.")
            else:
                await init_intro(message.author)

if __name__ == '__main__':
    client.run(config['bot_token'])
