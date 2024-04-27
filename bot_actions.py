import discord
from discord.ext import commands
from datetime import datetime
intents = discord.Intents.all()
from commands import suffix_enabled_string
bot = commands.Bot(command_prefix="/", intents=intents, case_insensitive=True)

# ユーザーの滞在時間を記録するための辞書
voice_times = {}

async def record_time(member, before, after):
    # ユーザーがボイスチャンネルに参加したとき
    if before.channel is None and after.channel is not None:
        voice_times[member.id] = datetime.now()
        print(f"{member.display_name} がボイスチャンネルに参加しました : ({voice_times[member.id]})")

    # ユーザーがボイスチャンネルから退出したとき
    elif before.channel is not None and after.channel is None:
        if member.id in voice_times:
            enter_time = voice_times.pop(member.id)
            stay_duration = datetime.now() - enter_time
            minutes = stay_duration.total_seconds() / 60  # 滞在時間を分に変換
            print(f"{member.display_name} がボイスチャンネルから退出しました : 滞在時間 {minutes} 分")
            await update_ranking(member, minutes)

async def update_ranking(member, minutes):
    guild = member.guild
    ranking_channel = discord.utils.get(guild.channels, name="vc滞在時間ランキング")
    if not ranking_channel:
        ranking_channel = await guild.create_text_channel("vc滞在時間ランキング")

    messages = []
    async for message in ranking_channel.history(limit=200):
        messages.append(message)
    for message in messages:
        if member.display_name in message.content:
            existing_minutes = extract_duration(message.content)
            new_minutes = existing_minutes + minutes
            new_message = f"{member.display_name} の滞在時間: {format_duration(new_minutes)}"
            await message.edit(content=new_message)
            return

    # 新規メッセージとして滞在時間を投稿
    await ranking_channel.send(f"{member.display_name} の滞在時間: {format_duration(minutes)}",silent=True)

def extract_duration(content):
    # 既存の滞在時間（分）を抽出
    duration_str = content.split(": ")[1].replace("分", "")
    return int(duration_str)

async def on_voice_state_update(member, before, after):
    await record_time(member, before, after)

def format_duration(minutes):
    # 分を時間と分に変換
    hours = minutes // 60
    remaining_minutes = int(minutes % 60)
    if hours > 0:
        return f"{hours}時間{remaining_minutes}分"
    else:
        return f"{remaining_minutes}分"

async def replace_suffix(message):
    suffix_channel = discord.utils.get(message.guild.text_channels, name="語尾db")
    if message.channel.name == "語尾db":
        return
    if suffix_channel:
        async for msg in suffix_channel.history(limit=200):
            # user.name (display.name) suffix の形式で保存されている
            user_id, suffix, is_enabled = msg.content.split(" ")
            print(f"ユーザーID: {user_id}, 語尾: {suffix} 有効: {is_enabled}")
            if is_enabled == suffix_enabled_string(False):
                print("無効化されています")
                continue
            if str(message.author.name) == user_id:
                print("登録されたユーザーが発言しました")
                print(f"ユーザーID: {user_id}, 語尾: {suffix}")
                new_content = f"{message.content}{suffix}"
                emoji = discord.utils.get(message.guild.emojis, name=message.author.name)
                # embedで
                embed = discord.Embed(title=message.author.display_name, description=new_content)
                if emoji:
                    embed.set_thumbnail(url=emoji.url)
                await message.delete()
                await message.channel.send(embed=embed)
                break
    else:
        print("語尾データなし")
