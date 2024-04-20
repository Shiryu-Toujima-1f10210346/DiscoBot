import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
from dateutil.parser import parse
from gtts import gTTS ,lang
import os 
from ui import ConfirmButton
import time

def setup(bot):

    bot.remove_command('help')

    @bot.command(description="pingを返します")
    async def ping(ctx):
        latency = bot.latency
        await ctx.reply(f'Latency: {(latency * 1000):.2f}ms', mention_author=False)

    @bot.command(description="これです")
    async def help(ctx):
        help_message = "```"
        sorted_commands = sorted(bot.commands, key=lambda x: x.name)
        for command in sorted_commands:
            help_message += f"!{command.name}: {command.description}\n\n"
        help_message += "```"
        embed = discord.Embed(title="コマンド一覧(アルファベット順)", color=0x00ff00, description=help_message)
        await ctx.reply(embed=embed, mention_author=False)

    @bot.command(description="ボイスチャンネルに入室します")
    async def join(ctx):
        if ctx.author.voice is None:
            await ctx.reply("ボイスチャンネルに参加してから再度試してください。", mention_author=False)
        else:
            channel = ctx.author.voice.channel
            if ctx.voice_client is not None:
                await ctx.reply("既にボイスチャンネルに入室しています。", mention_author=False)
            else:
                await channel.connect()

    @bot.command(description="ボイスチャンネルから退出します")
    async def leave(ctx):
        if ctx.voice_client is None:
            await ctx.reply("ボイスチャンネルに参加していません。", mention_author=False)
        else:
            await ctx.voice_client.disconnect()

    @bot.command(description="ttsで突然しゃべります")
    async def tts(ctx, *, message):
        await ctx.reply(message, tts=True, mention_author=False)

    @bot.command(description="指定したユーザーをミュートします")
    async def mute(ctx, member: discord.Member):
        await member.edit(mute=True)
        await ctx.reply(f"{member.mention}をミュートしました", mention_author=False)

    @bot.command(description="指定したユーザーのミュートを解除します")
    async def unmute(ctx, member: discord.Member):
        await member.edit(mute=False)
        await ctx.reply(f"{member.mention}のミュートを解除しました", mention_author=False)

    class GTTSEngine:
        def save_speech(self, text, lang_code, path):
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(path)

    async def play_speech(voice_client: discord.VoiceClient, path):
        if voice_client.is_playing():
            voice_client.stop()
        voice_client.play(discord.FFmpegPCMAudio(source=path))
        while voice_client.is_playing():
            await asyncio.sleep(1)

    @bot.command(description="ボイスチャンネル内で言語に応じて喋ります")
    async def say(ctx, lang_code: str, *, message: str):
        was_connected = ctx.voice_client is not None  # ボットが既に接続されているかをチェック
        supported_langs = lang.tts_langs()  # gttsがサポートする言語のリストを取得

        if not was_connected:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.reply("ボイスチャンネルに参加してから再度試してください。", mention_author=False)
                return

        if lang_code not in supported_langs:
            await ctx.reply("サポートされていない言語です。", mention_author=False)
            return

        tts = GTTSEngine()
        path = f"speech_{lang_code}.mp3"  # 言語ごとにファイル名を設定
        tts.save_speech(message, lang_code, path)
        await play_speech(ctx.voice_client, path)
        os.remove(path)  # 再生後にファイルを削除

        if not was_connected:
            await ctx.voice_client.disconnect()  # ボットが元々接続されていなかった場合、切断します

    @bot.command(description="VC対応言語の一覧を表示します")
    async def langlist(ctx):
        with open('languagelist.txt', 'rb') as file:
            await ctx.reply("対応言語一覧\nSupported Languages", file=discord.File(file, 'languagelist.txt'), mention_author=False)

    @bot.command(description="指定したメッセージに指定したリアクションをつけます")
    async def react(ctx, message_id: int, reaction: str):
        message = await ctx.fetch_message(message_id)
        await message.add_reaction(reaction)
        await ctx.reply("リアクションを追加しました", mention_author=False)

    @bot.command(description="N個の選択肢がある投票を作成します")
    async def vote(ctx, num: str):
        try:
            num = int(num)
            if num < 2 or num > 10:
                await ctx.reply("選択肢は2〜10個までです😡", mention_author=False)
                return
            message = await ctx.reply("投票")  # 投票メッセージ自体にはリプライ不要
            for i in range(1, num + 1):
                await message.add_reaction(f"{i}\u20e3")
        except ValueError:
            await ctx.reply("選択肢の数は整数で指定してください😡", mention_author=False)
        except Exception as e:
            await ctx.reply(str(e), mention_author=False)

    @bot.command(description="指定したユーザーにDMを送信します")
    async def dm(ctx, member: discord.Member, *, message):
        await member.send(message)
        await ctx.reply("DMを送信しました", mention_author=False)

    @bot.command(description="イベントを作成します YYYY-MM-DD HH:MM イベント名")
    async def event(ctx, date: str=None, time: str=None, event_name: str=None, channel_name: str = None):
        if date is None or time is None or event_name is None:
            await ctx.reply("日時、イベント名を指定してください", mention_author=False)
            return
        try:
            if ctx.author.voice is None and channel_name is not None:
                channel_id = discord.utils.get(ctx.guild.voice_channels, name=channel_name).id
            elif ctx.author.voice is not None:
                channel_id = ctx.author.voice.channel.id
            else:
                await ctx.reply("ボイスチャンネル名を指定するか、ボイスチャンネルに参加してください。", mention_author=False)
                return
            date_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").astimezone()
            channel = ctx.guild.get_channel(channel_id)
            await ctx.guild.create_scheduled_event(name=event_name, description="Botにより作成", start_time=date_time, entity_type=discord.EntityType.voice, channel=channel, privacy_level=discord.PrivacyLevel.guild_only)
            await ctx.reply("イベントを作成しました", mention_author=False)
            # Googleカレンダーに登録できるURLを生成
            await ctx.send(f"Googleカレンダーに登録する場合は[こちら](https://calendar.google.com/calendar/u/0/r/eventedit?dates={date_time.strftime('%Y%m%dT%H%M%S')}/{(date_time + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}&details=Botにより作成&location=Discord：「{ctx.guild.name}」サーバー&text={event_name})")

        except Exception as e:
            await ctx.reply(f"**エラーが発生しました**\n引数が間違っている可能性があります｡\n2024-04-01 12:00 会議 のように指定してください｡", mention_author=False)
            print(e)


    @bot.command(description="指定したイベントをキャンセルします")
    async def cancel(ctx, *, event_name):
        event = discord.utils.get(ctx.guild.scheduled_events, name=event_name)
        if event is None:
            await ctx.send("指定されたイベントが見つかりませんでした。")
            return

        confirm = ConfirmButton()
        message = await ctx.send("このイベントをキャンセルしますか？", view=confirm)
        await confirm.wait()  # ボタンの応答を待機

        if confirm.value == "YES":
            await event.delete()
            await message.edit(content="イベントがキャンセルされました。", view=None)
        elif confirm.value == "NO":
            await message.delete()
            await ctx.message.delete()

    @bot.command(description="指定したチャンネルのメッセージをすべて取得し、txtファイルとして保存、送信します。")
    async def getlog(ctx, channel_name: str):
        channel = discord.utils.get(ctx.guild.channels, name=channel_name)
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel.id}"
        if channel is None:
            await ctx.reply(f'チャンネル {channel_name} が見つかりません。')
            return

        start_time = time.time()

        try:
            with open(f'{channel_name}_log.txt', 'w', encoding='utf-8') as file:
                async for message in channel.history(limit=None):
                    file.write(f'{message.created_at} - {message.author.display_name}: {message.content}\n')
            execution_time = time.time() - start_time
            await ctx.reply(f'{channel_link} のメッセージログを {channel_name}_log.txt に保存しました。処理時間：{execution_time:.2f}秒', file=discord.File(f'{channel_name}_log.txt'))
            os.remove(f'{channel_name}_log.txt')
        except Exception as e:
            await ctx.send(f'エラーが発生しました: {str(e)}')
