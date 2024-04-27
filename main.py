import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from bot_actions import replace_suffix, record_time
from commands import setup


load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True


bot = commands.Bot(command_prefix="/", intents=intents, case_insensitive=True)


setup(bot)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    await bot.tree.sync()


@bot.event
async def on_message(message):
    # 語尾dbに書き込んでたら削除
    if message.channel.name == "語尾db" and message.author != bot.user:
        await message.delete()
    if message.author != bot.user:
        print(f"{message.author.display_name}: {message.content}")
    if message.author.bot or message.content.startswith(bot.command_prefix):
        return
    if any(
        message.content.startswith(prefix) for prefix in ("https", "http", "www", "!", "```", "！")
    ) :
        return
    if  message.attachments or message.mentions :
        return  
    if len(message.content) > 200:
        return 
    await replace_suffix(message) # 語尾DBチャンネルを取得

    await bot.process_commands(message)

# VCの滞在時間を記録
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    await record_time(member, before, after)
bot.run(TOKEN)
