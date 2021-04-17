# Bouncer-Bot

## About

This Discord bot helps streamline the process of introducing new members.
When a user joins a server, BB will message the user and ask them a few questions so that it may post a nicely formatted intruduction for them.
Once the user has answered all the questions (assuming the user is of age according to Discord's TOS) they will be given roles according to their answers.
This assists with moderating as it can prevent rudimentary "self-bot" raids from affecting your server, ensures users have an introduction in place before interacting with members (assuming your role permissions are configured as such) without manual intervention, and alerting mods to suspicious or TOS violating users.

## Setting up

If you'd like to run this bot on your own, you are more than welcome to do so.

You'll first want to copy or rename [example-config.yaml](example-config.yaml) to config.yaml, then add your bot token and the server ID that you'd like to use it with in the appropriate variables.
Once you have the dependencies installed with `pip install -r requirements.txt`, you should be able to start the bot with `python3 bot.py`, or if you have a virtual environment installed in the same directory, you can run `./start_bot.py`.
