import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS, lang
import os
import asyncio
from datetime import datetime, timedelta

def setup(bot):
    tree = bot.tree

    bot.remove_command("help")

    @tree.command(name="help", description="コマンド一覧を表示します")
    async def help(interaction: discord.Interaction):
        help_message = "```"
        for command in sorted(tree.get_commands(), key=lambda c: c.name):
            help_message += f"/{command.name}: {command.description}\n\n"

        help_message += "```"
        embed = discord.Embed(title="コマンド一覧(アルファベット順)", color=0x00ff00, description=help_message)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="ping", description="pingを返します")
    async def ping(interaction: discord.Interaction):
        latency = bot.latency
        await interaction.response.send_message(f"Latency: {(latency * 1000):.2f}ms")

    @tree.command(name="join", description="ボイスチャンネルに入室します")
    async def join(interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message(
                "ボイスチャンネルに参加してから再度試してください。"
            )
        else:
            channel = interaction.user.voice.channel
            if interaction.guild.voice_client is not None:
                await interaction.response.send_message(
                    "既にボイスチャンネルに入室しています。"
                )
            else:
                await channel.connect()
                await interaction.followup.send("ボイスチャンネルに入室しました。")

    @tree.command(name="leave", description="ボイスチャンネルから退出します")
    async def leave(interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message(
                "ボイスチャンネルに参加していません。"
            )
        else:
            await interaction.guild.voice_client.disconnect()
            await interaction.followup.send("ボイスチャンネルから退出しました。")

    @tree.command(name="tts", description="ttsで突然しゃべります")
    async def tts(interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message, tts=True)

    @tree.command(name="mute", description="指定したユーザーをミュートします")
    @app_commands.describe(member="ミュートするメンバー")
    async def mute(interaction: discord.Interaction, member: discord.Member):
        await member.edit(mute=True)
        await interaction.response.send_message(
            f"{member.mention} をミュートしました"
        )

    @tree.command(name="unmute", description="指定したユーザーのミュートを解除します")
    @app_commands.describe(member="ミュートを解除するメンバー")
    async def unmute(interaction: discord.Interaction, member: discord.Member):
        # memberを見やすくprint
        await member.edit(mute=False)
        await interaction.response.send_message(
            f"{member.mention} のミュートを解除しました"
        )

    @tree.command(name="say", description="ボイスチャンネル内で言語に応じて喋ります")
    @app_commands.describe(lang_code="言語コード", message="話すメッセージ")
    async def say(interaction: discord.Interaction, lang_code: str, message: str):
        # botがVCに参加しているか確認
        was_connected = interaction.guild.voice_client is None
        print("botがVCに参加しているか確認", was_connected)
        supported_langs = lang.tts_langs()
        if lang_code not in supported_langs:
            await interaction.response.send_message("サポートされていない言語です。")
            return

        path = f"speech_{lang_code}.mp3"
        tts = gTTS(text=message, lang=lang_code)
        tts.save(path)

        if interaction.guild.voice_client is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.response.send_message(
                    "ボイスチャンネルに参加してから再度試してください。"
                )
                return

        source = discord.FFmpegPCMAudio(path)
        interaction.guild.voice_client.play(source)

        # 再生が終了したらファイルを削除
        await asyncio.sleep(len(message) / 5)  # おおよその再生時間を計算
        os.remove(path)

        if not was_connected:
            await interaction.guild.voice_client.disconnect()

    @tree.command(name="langlist", description="VC対応言語の一覧を表示します")
    async def langlist(interaction: discord.Interaction):
        with open("languagelist.txt", "rb") as file:
            await interaction.response.send_message(
                "対応言語一覧\nSupported Languages",
                file=discord.File(file, "languagelist.txt"),
            )

    @tree.command(
        name="react", description="指定したメッセージに指定したリアクションをつけます"
    )
    @app_commands.describe(
        message_id="リアクションをつけるメッセージのID", reaction="リアクション"
    )
    async def react(interaction: discord.Interaction, message_id: int, reaction: str):
        message = await interaction.channel.fetch_message(message_id)
        await message.add_reaction(reaction)
        await interaction.response.send_message("リアクションを追加しました")

    @tree.command(name="vote", description="N個の選択肢がある投票を作成します")
    @app_commands.describe(num="選択肢の数")
    async def vote(interaction: discord.Interaction, num: int):
        if num < 2 or num >= 10:
            await interaction.response.send_message("選択肢は2〜10個までです😡", ephemeral=True)
            return  
        await interaction.response.defer()  
        message = await interaction.followup.send("以下にリアクションをクリックして投票してください:")
        for i in range(1, num + 1):
            await message.add_reaction(f"{i}\u20e3")    

    @tree.command(name="dm", description="指定したユーザーにDMを送信します")
    @app_commands.describe(member="DMを送るメンバー", message="メッセージ内容")
    async def dm(
        interaction: discord.Interaction, member: discord.Member, message: str
    ):
        await member.send(message)
        await interaction.response.send_message("DMを送信しました")

    @tree.command(
        name="event", description="イベントを作成します YYYY-MM-DD HH:MM イベント名"
    )
    @app_commands.describe(
        date="イベントの日付 YYYY-MM-DD",
        time="イベントの時間 HH:MM",
        event_name="イベント名",
        channel_name="ボイスチャンネル名",
    )
    async def event(
        interaction: discord.Interaction,
        date: str,
        time: str,
        event_name: str,
        channel_name: str = None,
    ):
        try:
            channel_id = discord.utils.get(
                interaction.guild.voice_channels, name=channel_name
            ).id
            date_time = datetime.strptime(
                f"{date} {time}", "%Y-%m-%d %H:%M"
            ).astimezone()
            channel = interaction.guild.get_channel(channel_id)
            await interaction.guild.create_scheduled_event(
                name=event_name,
                description="Botにより作成",
                start_time=date_time,
                entity_type=discord.EntityType.voice,
                channel=channel,
                privacy_level=discord.PrivacyLevel.guild_only,
            )
            await interaction.response.send_message(
                f"イベントを作成しました: {event_name} @ {date_time}"
            )
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    @tree.command(name="cancel", description="指定したイベントをキャンセルします")
    @app_commands.describe(event_name="キャンセルするイベント名")
    async def cancel(interaction: discord.Interaction, event_name: str):
        event = discord.utils.get(interaction.guild.scheduled_events, name=event_name)
        if event is None:
            await interaction.response.send_message(
                "指定されたイベントが見つかりませんでした。"
            )
            return
        await event.delete()
        await interaction.followup.send("イベントがキャンセルされました。")
