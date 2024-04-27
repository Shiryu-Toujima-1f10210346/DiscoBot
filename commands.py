import discord
from discord import app_commands
from gtts import gTTS, lang
import os
import asyncio
import datetime
from datetime import timedelta
import io
import aiohttp
from PIL import Image, ImageOps

def setup(bot):
    tree = bot.tree

    @tree.command(name="help", description="コマンド一覧を表示します")
    async def help(interaction: discord.Interaction):
        help_message = "```"
        for command in sorted(tree.get_commands(), key=lambda c: c.name):
            help_message += f"/{command.name}: {command.description}\n\n"

        help_message += "```"
        embed = discord.Embed(title="コマンド一覧(アルファベット順)", color=0x00ff00, description=help_message)
        await interaction.response.send_message(embed=embed)

    ####################################################################################
    ####################################################################################

    @tree.command(name="ping", description="pingを返します")
    async def ping(interaction: discord.Interaction):
        latency = bot.latency
        await interaction.response.send_message(f"Latency: {(latency * 1000):.2f}ms")

    ####################################################################################
    ####################################################################################

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
                await interaction.response.send_message("ボイスチャンネルに入室しました。")

    ####################################################################################
    ####################################################################################

    @tree.command(name="leave", description="ボイスチャンネルから退出します")
    async def leave(interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message(
                "ボイスチャンネルに参加していません。"
            )
        else:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("ボイスチャンネルから退出しました。")

    ####################################################################################
    ####################################################################################

    @tree.command(name="tts", description="ttsで突然しゃべります")
    async def tts(interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message, tts=True)

    ####################################################################################
    ####################################################################################

    @tree.command(name="mute", description="指定したユーザーをミュートします")
    @app_commands.describe(member="ミュートするメンバー")
    async def mute(interaction: discord.Interaction, member: discord.Member):
        try:
            await member.edit(mute=True)
            await interaction.response.send_message(
                f"{member.mention} をミュートしました"
            )
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="unmute", description="指定したユーザーのミュートを解除します")
    @app_commands.describe(member="ミュートを解除するメンバー")
    async def unmute(interaction: discord.Interaction, member: discord.Member):
        try:
            await member.edit(mute=False)
            await interaction.response.send_message(
                f"{member.mention} のミュートを解除しました"
            )
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="say", description="ボイスチャンネル内で言語に応じて喋ります")
    @app_commands.describe(lang_code="言語コード", message="話すメッセージ")
    async def say(interaction: discord.Interaction, lang_code: str, message: str):
        await interaction.response.defer()
        try:
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
            await asyncio.sleep(len(message) / 3)  # おおよその再生時間を計算
            os.remove(path)

            if was_connected:
                await interaction.guild.voice_client.disconnect()
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")
        else:
            await interaction.followup.send_message(f"{interaction.user.mention}に{message}と言わされました･･･")
            
    ####################################################################################
    ####################################################################################

    @tree.command(name="langlist", description="VC対応言語の一覧を表示します")
    async def langlist(interaction: discord.Interaction):
        with open("languagelist.txt", "rb") as file:
            await interaction.response.send_message(
                "対応言語一覧\nSupported Languages",
                file=discord.File(file, "languagelist.txt"),
            )

    ####################################################################################
    ####################################################################################

    @tree.command(
        name="react", description="指定したメッセージに指定したリアクションをつけます"
    )
    @app_commands.describe(
        message_id="リアクションをつけるメッセージのID", reaction="リアクション"
    )
    async def react(interaction: discord.Interaction, message_id: str, reaction: str):
        try:
            message_id = int(message_id)
            message_id = int(message_id)
            message = await interaction.channel.fetch_message(message_id)
            await message.add_reaction(reaction)

            await interaction.response.send_message(
                f"{message.jump_url}\nに{reaction}をつけました"
            )
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="vote", description="N個の選択肢がある投票を作成します")
    @app_commands.describe(num="選択肢の数")
    async def vote(interaction: discord.Interaction, num: int):
        try:
            if num < 2 or num >= 10:
                await interaction.response.send_message("選択肢は2〜10個までです😡", ephemeral=True)
                return
            await interaction.response.defer()
            message = await interaction.followup.send("以下にリアクションをクリックして投票してください:")
            for i in range(1, num + 1):
                await message.add_reaction(f"{i}\u20e3")
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="dm", description="指定したユーザーにDMを送信します")
    @app_commands.describe(member="DMを送るメンバー", message="メッセージ内容")
    async def dm(
        interaction: discord.Interaction, member: discord.Member, message: str
    ):
        try:
            await member.send(f'from:{member.display_name} {message}')
            await interaction.response.send_message("DMを送信しました")
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(
        name="event", description="イベントを作成します YYYY-MM-DD HH:MM イベント名"
    )
    @app_commands.describe(
        date="イベントの日付 YYYY-MM-DD",
        time="イベントの時間 HH:MM",
        event_name="イベント名",
        hour="合計時間(単位: 時間)",
        location="イベントの場所",
    )
    async def event(
        interaction: discord.Interaction,
        date: str,
        time: str,
        event_name: str,
        hour: float,
        location: str,
    ):
        try:
            date_time = datetime.strptime(
                f"{date} {time}", "%Y-%m-%d %H:%M"
            ).astimezone()

            await interaction.guild.create_scheduled_event(
                name=event_name,
                description="Botにより作成",
                start_time=date_time,
                end_time = date_time + timedelta(minutes=hour*60),
                entity_type=discord.EntityType.external,
                location=location,
                privacy_level=discord.PrivacyLevel.guild_only,
            )
            await interaction.response.send_message(
                f"イベントを作成しました: {event_name} @ {date_time}"
            )
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(
        name="eventvc", description="VCイベントを作成します YYYY-MM-DD HH:MM イベント名"
    )
    @app_commands.describe(
        date="イベントの日付 ex) 2024-04-15",
        time="イベントの時間 HH:MM",
        event_name="イベント名",
        channel_name="イベントの場所",
    )
    async def eventvc(
        interaction: discord.Interaction,
        date: str,
        time: str,
        event_name: str,
        channel_name: str = None,
    ):
        try:
            # ユーザーがVCに存在していたらそのVCのIDを取得
            if interaction.user.voice:
                channel_id = interaction.user.voice.channel.id
            elif channel_name is None:
                await interaction.response.send_message("VCに参加するか､VC名を指定してください")
                return
            else:
                channel_id = discord.utils.get(
                    interaction.guild.voice_channels, name=channel_name
                ).id
            channel = interaction.guild.get_channel(channel_id)
            date_time = datetime.strptime(
                f"{date} {time}", "%Y-%m-%d %H:%M"
            ).astimezone()

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

    ####################################################################################
    ####################################################################################

    @tree.command(name="cancel", description="指定したイベントをキャンセルします")
    @app_commands.describe(event_name="キャンセルするイベント名")
    async def cancel(interaction: discord.Interaction, event_name: str):
        try :
            event = discord.utils.get(interaction.guild.scheduled_events, name=event_name)
            if event is None:
                await interaction.response.send_message(
                    "指定されたイベントが見つかりませんでした。"
                )
                return
            await event.delete()
            await interaction.response.send_message(f"イベント:{event_name} がキャンセルされました。")
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################
    @tree.command(
        name="getlog",
        description="指定したチャンネルのメッセージログを取得し、txtファイルで送信します",
    )
    @app_commands.describe(channel_name="ログを取得するチャンネル名")
    async def getlog(
        interaction: discord.Interaction, channel_name: str, limit: int = 200
    ):
        start_time = datetime.datetime.now()  # 処理開始時間を記録

        try:
            await interaction.response.defer()  # 応答を遅延させる

            channel = discord.utils.get(
                interaction.guild.text_channels, name=channel_name
            )
            if channel is None:
                await interaction.followup.send(
                    "指定されたチャンネルが見つかりませんでした。"
                )
                return

            message_count = 0  # メッセージの数をカウントする変数を初期化
            with open("log.txt", "w") as file:
                async for message in channel.history(limit=limit):
                    file.write(f"{message.author.display_name}: {message.content}\n")
                    message_count += 1  # メッセージを1つ取得するごとにカウントを増やす

            end_time = datetime.datetime.now()  # 処理終了時間を記録
            duration = (end_time - start_time).total_seconds()  # 処理時間を秒単位で計算

            await interaction.followup.send(
                f"{message_count}個のメッセージを保存しました。処理時間: {duration}秒",
                file=discord.File("log.txt"),
            )
            os.remove("log.txt")
        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="eventlist", description="イベント一覧を表示します")
    async def eventlist(interaction: discord.Interaction):
        try:
            event_list = ""
            for event in interaction.guild.scheduled_events:
                event_list += f"{event.name} @ {event.start_time}\n"
            await interaction.response.send_message(event_list)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}")

    ####################################################################################
    ####################################################################################

    @tree.command(name="gobireg", description="ユーザーの語尾を登録します")
    @app_commands.describe(user="語尾を変更するユーザー", suffix="設定する語尾")
    async def register_suffix(
        interaction: discord.Interaction, user: discord.User, suffix: str
    ):
        if len(suffix) > 20:
            await interaction.response.send_message("語尾は20文字以内にしてください")
            return
        # 語尾DBチャンネルを確認、なければ作成
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if not suffix_channel:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(send_messages=True),
            }
            suffix_channel = await interaction.guild.create_text_channel(
                "語尾db", overwrites=overwrites
            )
            print("語尾DBチャンネルが見つからなかったので作成")

        # 既存の語尾データを検索し、更新が必要か判断
        async for msg in suffix_channel.history(limit=200):
            user_name, _ = msg.content.split(maxsplit=1)
            if str(user.name) == user_name:
                await msg.edit(
                    content=f"{user.name} {suffix} {suffix_enabled_string(True)}"
                )
                await interaction.response.send_message(
                    f"{user.name}({user.display_name})の語尾を更新しました: {suffix}"
                )
                return

        emoji = discord.utils.get(interaction.guild.emojis, name=user.name)
        if not emoji:
            print(f"このユーザーの絵文字(:{user.name}:)を作成します")
            await create_emoji(interaction, user)
        else:
            print(f"このユーザーの絵文字:({user.name}):はすでに登録されています")

        await suffix_channel.send(
            f"{user.name} {suffix} {suffix_enabled_string(True)}", silent=True
        )
        await interaction.response.send_message(
            f"{user.name} ({user.display_name}) の語尾を登録しました: {suffix}"
        )

    async def create_emoji(interaction: discord.Interaction, member: discord.Member):
        emoji_url = member.display_avatar.url
        emoji_name = f"{member.name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as resp:
                if resp.status != 200:
                    return
                image_data = await resp.read()
                image = Image.open(io.BytesIO(image_data))

                # 画像をリサイズしてファイルサイズを確認
                max_size = (128, 128)  # 絵文字の最大サイズは128x128ピクセル
                image = ImageOps.contain(image, max_size)
                with io.BytesIO() as image_binary:
                    image.save(image_binary, format='PNG')
                    image_binary.seek(0)
                    image_bytes = image_binary.read()

                    # ファイルサイズが256KB以下か確認
                    if len(image_bytes) > 256 * 1024:
                        print("画像ファイルが大きすぎます。")
                        return
                    await interaction.guild.create_custom_emoji(name=emoji_name, image=image_bytes)

    @tree.command(name="gobidelete", description="ユーザーの語尾を削除します")
    @app_commands.describe(user="語尾を削除するユーザー")
    async def delete_suffix(interaction: discord.Interaction, user: discord.User):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, suffix= msg.content.split(maxsplit=1)
                if str(user.name) == user_name:
                    await msg.delete()
                    await interaction.response.send_message(f"{user.name}({user.display_name})の語尾を削除しました")
                    break
            else:
                await interaction.response.send_message(
                    f"{user.name}({user.display_name})の語尾が見つかりませんでした"
                )
        else:
            await interaction.response.send_message("語尾データなし")

    @tree.command(name="gobiupdate", description="ユーザーの語尾を更新します")
    @app_commands.describe(user="語尾を更新するユーザー", suffix="新しい語尾")
    async def update_suffix(interaction: discord.Interaction, user: discord.User, suffix: str):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, _ = msg.content.split(maxsplit=1)
                if str(user.name) == user_name:
                    await msg.edit(content=f"{user.name} {suffix} {suffix_enabled_string(True)}")
                    await interaction.response.send_message(f"{user.name}({user.display_name})の語尾を更新しました: {suffix}")
                    break
            else:
                await interaction.response.send_message(
                    f"{user.name}({user.display_name})の語尾が見つかりませんでした"
                )
        else:
            await interaction.response.send_message("語尾データなし")

    @tree.command(name="gobilist", description="語尾一覧を表示します")
    async def list_suffix(interaction: discord.Interaction):
        suffix_channel = discord.utils.get(
            interaction.guild.text_channels, name="語尾db"
        )
        embed = discord.Embed(title="語尾一覧", color=0x00FF00)
        messages = []
        async for message in suffix_channel.history(limit=200):
            messages.append(message)
        if not messages:
            await interaction.response.send_message("語尾データなし")
            return
        suffix_list = []
        for message in messages:
            user_id, suffix = message.content.split(maxsplit=1)
            user = discord.utils.get(interaction.guild.members, name=user_id)
            if user:
                suffix_list.append(f"{user.display_name}: {suffix}")
            else:
                suffix_list.append(f"{user_id}: {suffix}")
        embed.description = "\n".join(suffix_list)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="gobienable", description="ユーザーの語尾を有効にします")
    @app_commands.describe(user="語尾を有効にするユーザー")
    async def enable_suffix(interaction: discord.Interaction, user: discord.User):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, suffix, is_enabled = msg.content.split(maxsplit=2)
                if str(user.name) == user_name:
                    await msg.edit(content=f"{user.name} {suffix} {suffix_enabled_string(True)}")
                    await interaction.response.send_message(f"{user.name}({user.display_name})の語尾を有効にしました")
                    break
            else:
                await interaction.response.send_message(
                    f"{user.name}({user.display_name})の語尾が見つかりませんでした"
                )
        else:
            await interaction.response.send_message("語尾データなし")

    @tree.command(name="gobidisable", description="ユーザーの語尾を無効にします")
    @app_commands.describe(user="語尾を無効にするユーザー")
    async def disable_suffix(interaction: discord.Interaction, user: discord.User):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, suffix, is_enabled = msg.content.split(maxsplit=2)
                if str(user.name) == user_name:
                    await msg.edit(content=f"{user.name} {suffix} {suffix_enabled_string(False)}")
                    await interaction.response.send_message(f"{user.name}({user.display_name})の語尾を無効にしました")
                    break
            else:
                await interaction.response.send_message(
                    f"{user.name}({user.display_name})の語尾が見つかりませんでした"
                )
        else:
            await interaction.response.send_message("語尾データなし")

    @tree.command(name="gobienableall", description="全ての語尾を有効にします")
    async def enable_all_suffix(interaction: discord.Interaction):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, suffix, is_enabled = msg.content.split(maxsplit=2)
                await msg.edit(content=f"{user_name} {suffix} {suffix_enabled_string(True)}")
            await interaction.response.send_message("全ての語尾を有効にしました")
        else:
            await interaction.response.send_message("語尾データなし")
    
    @tree.command(name="gobidisableall", description="全ての語尾を無効にします")
    async def disable_all_suffix(interaction: discord.Interaction):
        suffix_channel = discord.utils.get(interaction.guild.text_channels, name="語尾db")
        if suffix_channel:
            async for msg in suffix_channel.history(limit=200):
                user_name, suffix, is_enabled = msg.content.split(maxsplit=2)
                await msg.edit(content=f"{user_name} {suffix} {suffix_enabled_string(False)}")
            await interaction.response.send_message("全ての語尾を無効にしました")
        else:
            await interaction.response.send_message("語尾データなし")

    ####################################################################################
    ####################################################################################

    @tree.command(name="update", description="botのアップデートを行います")
    async def update(interaction: discord.Interaction):
        await interaction.response.send_message(
            "以下のリンクからBotを再び追加してください｡\n(現在のBotを追い出す必要はありません)\n[こちら](https://discord.com/oauth2/authorize?client_id=1233179658418131025&permissions=8&scope=bot)"
        )

    ####################################################################################
    ####################################################################################
    @tree.command(name="rom", description="聞き専モードを有効にします")
    async def rom(interaction: discord.Interaction ):
        role = discord.utils.get(interaction.guild.roles, name="聞き専")
        if not role:
            role = await interaction.guild.create_role(name="聞き専")
        await interaction.user.remove_roles(role)
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"{interaction.user.display_name} が聞き専モードになりました")

    @tree.command(name="romend", description="聞き専モードが有効になっていた間のメッセージをすべて削除します")
    async def romend(interaction: discord.Interaction):
        if not discord.utils.get(interaction.user.roles, name="聞き専"):
            await interaction.response.send_message("聞き専モードになっていません")
            return
        async for msg in interaction.channel.history(limit=200):
            if msg.author == interaction.user:
                await msg.delete()
            if msg.content == f"{interaction.user.display_name} が聞き専モードになりました":
                await msg.delete()
                break

        await interaction.response.send_message(f"{interaction.user.display_name} が聞き専モードを解除しました")

    ####################################################################################
    ####################################################################################

    @tree.command(name="ranking", description="VC滞在時間ランキングを表示します")
    async def ranking(interaction: discord.Interaction):
        ranking_channel = discord.utils.get(interaction.guild.text_channels, name="vc滞在時間ランキング")
        if ranking_channel:
            messages = []
            async for message in ranking_channel.history(limit=200):
                messages.append(message)
            user_times = []
            for message in messages:
                user_mention, duration = parse_duration(message.content)
                user = interaction.guild.get_member(int(user_mention.strip("<@!>")))
                if user:  # ユーザーが見つかった場合
                    user_times.append((user.display_name, duration))
            user_times.sort(key=lambda x: x[1], reverse=True)

            ranking_messages = []
            for rank, (user, duration) in enumerate(user_times, start=1):
                hours, minutes = divmod(duration, 60)
                ranking_messages.append(f"{rank}位: {user} {hours}時間{minutes}分")
            embed = discord.Embed(title="VC滞在時間ランキング", color=0x00ff00)
            embed.add_field(name="ランキング", value="\n".join(ranking_messages))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("まだランキングが作成されていません")

    def parse_duration(content):
        # "ユーザー名 の滞在時間: n時間n分" から必要な情報を抽出
        user_info, duration_str = content.split(" の滞在時間: ")
        hours, minutes = 0, 0
        if "時間" in duration_str:
            hours, minutes = duration_str.split("時間")
            minutes = minutes.replace("分", "")
        else:
            minutes = duration_str.replace("分", "")
        total_minutes = int(hours) * 60 + int(minutes)
        return user_info, total_minutes


####################################################################################
####################################################################################

def suffix_enabled_string(is_enabled: bool):
    return "有効" if is_enabled else "無効"
