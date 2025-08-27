import os
import random
import discord
import asyncio
import time
import uuid
from discord.ext import commands

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
# intents.members = True  # 이 권한이 문제를 일으킴 - 주석 처리
bot = commands.Bot(command_prefix="!", intents=intents)  # prefix는 유지하되 슬래시 명령어 추가

# 게임 상태 저장용 변수
games = {}  # {guild_id: {"players": [], "turn_index": 0, "active": True, "paused": False, "last_turn_time": timestamp, "turn_count": 0}}
active_timers = {}  # {guild_id: task} - 활성 타이머 추적
starting_games = set()  # 현재 게임 시작 중인 서버 ID들

# 봇 인스턴스 추적
bot_instance_id = str(uuid.uuid4())[:8]
print(f"🆔 봇 인스턴스 ID: {bot_instance_id}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Connected to {len(bot.guilds)} guild(s)")
    
    # 봇 재시작 시 게임 상태 초기화
    global games, active_timers, starting_games
    games.clear()
    active_timers.clear()
    starting_games.clear()
    print("🧹 게임 상태 초기화 완료")
    
    # 슬래시 명령어 동기화 시도
    try:
        print("🔄 슬래시 명령어 동기화 중...")
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} 개의 슬래시 명령어가 동기화되었습니다!")
        print("📋 동기화된 명령어:")
        for cmd in synced:
            print(f"  - /{cmd.name}: {cmd.description}")
    except Exception as e:
        print(f"⚠️ 슬래시 명령어 동기화 실패: {e}")
        print("💡 봇이 서버에 제대로 초대되었는지 확인하세요.")

@bot.command(name="start")
async def start(ctx, *members: discord.Member):
    """새로운 젠가 게임을 시작합니다."""
    if not members:
        await ctx.send("⚠️ 최소 한 명 이상의 참가자를 멘션해주세요.\n사용법: `!start @사용자1 @사용자2 @사용자3` 또는 `/start @사용자1 @사용자2 @사용자3`")
        return

@bot.tree.command(name="start", description="젠가 게임을 시작합니다")
async def start_slash(interaction: discord.Interaction, members: str):
    """슬래시 명령어로 젠가 게임을 시작합니다."""
    # 멘션된 사용자들을 파싱
    if not members or not members.strip():
        await interaction.response.send_message("⚠️ 최소 한 명 이상의 참가자를 멘션해주세요.\n사용법: `/start @사용자1 @사용자2 @사용자3`")
        return
    
    # 멘션된 사용자들을 찾기
    mentioned_members = []
    for member_id in members.split():
        if member_id.startswith('<@') and member_id.endswith('>'):
            try:
                member_id = int(member_id[2:-1].replace('!', ''))
                member = interaction.guild.get_member(member_id)
                if member:
                    mentioned_members.append(member)
            except:
                continue
    
    if not mentioned_members:
        await interaction.response.send_message("⚠️ 유효한 사용자를 멘션해주세요.")
        return
    
    # 기존 start 함수의 로직을 재사용
    ctx = await bot.get_context(interaction.message) if interaction.message else None
    if not ctx:
        # 가상의 context 객체 생성
        class VirtualContext:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author
                self.send = interaction.response.send_message
        
        ctx = VirtualContext(interaction.guild, interaction.user)
    
    # start 함수 호출
    await start(ctx, *mentioned_members)

    guild_id = ctx.guild.id
    
    # 파일 기반 중복 실행 방지
    lock_file = f"lock_{guild_id}.txt"
    if os.path.exists(lock_file):
        await ctx.send("⚠️ 다른 봇 인스턴스가 게임을 시작하고 있습니다. 잠시 기다려주세요.")
        return
    
    # 락 파일 생성
    try:
        with open(lock_file, 'w') as f:
            f.write(f"{bot_instance_id}\n{time.time()}")
    except:
        await ctx.send("⚠️ 게임 시작에 실패했습니다. 다시 시도해주세요.")
        return
    
    # 중복 실행 방지
    if guild_id in starting_games:
        os.remove(lock_file)
        await ctx.send("⚠️ 게임이 이미 시작되고 있습니다. 잠시 기다려주세요.")
        return
    
    # 이미 게임이 진행 중인지 확인
    if guild_id in games and games[guild_id]["active"]:
        os.remove(lock_file)
        await ctx.send("⚠️ 이미 진행 중인 게임이 있습니다. `!stop`으로 기존 게임을 중단한 후 다시 시작하세요.")
        return
    
    # 게임 시작 플래그 설정
    starting_games.add(guild_id)
    
    # 기존 게임 데이터가 있으면 완전히 정리
    if guild_id in games:
        del games[guild_id]
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    players = list(members)
    random.shuffle(players)

    games[guild_id] = {
        "players": players,
        "turn_index": 0,
        "active": True,
        "paused": False,
        "last_turn_time": time.time(),
        "turn_count": 0
    }
    
    # 자동 선택 타이머 시작 (중복 방지)
    task = asyncio.create_task(auto_pick_timer(ctx.guild))
    active_timers[guild_id] = task

    order = " → ".join([p.mention for p in players])
    first = players[0].mention
    await ctx.send(f"🧩 젠가 게임 시작! (봇 ID: {bot_instance_id})\n👉 순서: {order}\n첫 번째 차례: {first}\n\n`!pick` 명령어로 블록을 뽑으세요!")
    
    # 게임 시작 플래그 해제
    starting_games.discard(guild_id)
    
    # 락 파일 제거
    try:
        os.remove(lock_file)
    except:
        pass

@bot.command(name="pick")
async def pick(ctx):
    """자신의 차례일 때 블록을 뽑습니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="pick", description="자신의 차례일 때 블록을 뽑습니다")
async def pick_slash(interaction: discord.Interaction):
    """슬래시 명령어로 블록을 뽑습니다."""
    # 가상의 context 객체 생성
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await pick(ctx)

    if guild_id not in games or not games[guild_id]["active"]:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다. `!start`로 게임을 시작하세요.")
        return
    
    if games[guild_id]["paused"]:
        await ctx.send("⏸️ 게임이 일시중단되었습니다. `!resume`으로 게임을 재시작하세요.")
        return

    game = games[guild_id]
    players = game["players"]
    turn_index = game["turn_index"]
    current_player = players[turn_index]

    if ctx.author != current_player:
        await ctx.send(f"⚠️ 지금은 {current_player.mention} 차례입니다.")
        return

    # 젠가 무너질 확률 (10%)
    if random.random() < 0.1:
        game["turn_count"] += 1
        await ctx.send(f"💥 {ctx.author.mention} 이(가) 블록을 뽑다가 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!")
        game["active"] = False
        # 타이머 정리
        guild_id = ctx.guild.id
        if guild_id in active_timers:
            active_timers[guild_id].cancel()
            del active_timers[guild_id]
        return

    # 안전할 경우 → 다음 차례
    game["turn_count"] += 1  # 턴 카운터 증가
    next_index = (turn_index + 1) % len(players)
    game["turn_index"] = next_index
    game["last_turn_time"] = time.time()  # 턴 시간 업데이트
    next_player = players[next_index]
    await ctx.send(f"✅ {ctx.author.mention} 안전하게 블록을 뽑았습니다!\n📊 **{game['turn_count']}번째 턴** 완료!\n👉 다음 차례: {next_player.mention}")
    
    # 다음 플레이어를 위한 자동 선택 타이머 시작 (중복 방지)
    if guild_id in active_timers:
        active_timers[guild_id].cancel()  # 기존 타이머 취소
        del active_timers[guild_id]
    task = asyncio.create_task(auto_pick_timer(ctx.guild))
    active_timers[guild_id] = task

@bot.command(name="status")
async def status(ctx):
    """현재 게임 상태를 확인합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="status", description="현재 게임 상태를 확인합니다")
async def status_slash(interaction: discord.Interaction):
    """슬래시 명령어로 게임 상태를 확인합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await status(ctx)
    
    if guild_id not in games or not games[guild_id]["active"]:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    if games[guild_id]["paused"]:
        await ctx.send("⏸️ 게임이 일시중단되었습니다.")
        return
    
    game = games[guild_id]
    players = game["players"]
    current_player = players[game["turn_index"]]
    
    status_text = f"📊 게임 상태:\n참가자: {', '.join([p.mention for p in players])}\n현재 차례: {current_player.mention}\n📈 진행된 턴: {game['turn_count']}턴"
    
    if game["paused"]:
        status_text += "\n⏸️ **게임 일시중단됨**"
    
    await ctx.send(status_text)

async def auto_pick_timer(guild):
    """60초 후 자동으로 블록을 선택하는 타이머"""
    guild_id = guild.id
    
    # 60초 카운트다운
    for remaining in range(60, 0, -1):
        if guild_id not in games or not games[guild_id]["active"] or games[guild_id]["paused"]:
            # 타이머 정리
            if guild_id in active_timers:
                del active_timers[guild_id]
            return
        
        # 10초마다 남은 시간 표시
        if remaining % 10 == 0 or remaining <= 10:
            try:
                # 메시지를 보낼 채널 찾기
                if hasattr(guild, 'system_channel') and guild.system_channel:
                    await guild.system_channel.send(f"⏰ **{remaining}초** 남았습니다! `!pick` 명령어를 사용하세요!")
                else:
                    # system_channel이 없으면 첫 번째 텍스트 채널에 보내기
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await channel.send(f"⏰ **{remaining}초** 남았습니다! `!pick` 명령어를 사용하세요!")
                            break
            except:
                pass  # 메시지 전송 실패 시 무시
        
        await asyncio.sleep(1)  # 1초씩 대기
    
    guild_id = guild.id
    if guild_id not in games or not games[guild_id]["active"] or games[guild_id]["paused"]:
        # 타이머 정리
        if guild_id in active_timers:
            del active_timers[guild_id]
        return
    
    game = games[guild_id]
    current_time = time.time()
    last_turn_time = game.get("last_turn_time", 0)
    
    # 10초가 지났는지 확인
    if current_time - last_turn_time >= 10:
        players = game["players"]
        turn_index = game["turn_index"]
        current_player = players[turn_index]
        
        # 자동 선택으로 블록 뽑기
        if random.random() < 0.1:
            # 젠가가 무너진 경우
            game["turn_count"] += 1
            message = f"⏰ {current_player.mention} 60초 동안 응답하지 않아 자동 선택되었습니다!\n💥 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!"
            game["active"] = False
            
            # 타이머 정리
            if guild_id in active_timers:
                del active_timers[guild_id]
            
            # 메시지를 보낼 채널 찾기 (가장 최근에 사용된 채널 사용)
            if hasattr(guild, 'system_channel') and guild.system_channel:
                await guild.system_channel.send(message)
            else:
                # system_channel이 없으면 첫 번째 텍스트 채널에 보내기
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send(message)
                        break
            return
        else:
            # 안전하게 뽑기
            game["turn_count"] += 1
            next_index = (turn_index + 1) % len(players)
            game["turn_index"] = next_index
            game["last_turn_time"] = time.time()
            next_player = players[next_index]
            message = f"⏰ {current_player.mention} 60초 동안 응답하지 않아 자동 선택되었습니다!\n✅ 안전하게 블록을 뽑았습니다!\n📊 **{game['turn_count']}번째 턴** 완료!\n👉 다음 차례: {next_player.mention}"
            
            # 메시지를 보낼 채널 찾기
            if hasattr(guild, 'system_channel') and guild.system_channel:
                await guild.system_channel.send(message)
            else:
                # system_channel이 없으면 첫 번째 텍스트 채널에 보내기
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send(message)
                        break
            
            # 다음 플레이어를 위한 타이머 시작 (중복 방지)
            if guild_id in active_timers:
                active_timers[guild_id].cancel()  # 기존 타이머 취소
                del active_timers[guild_id]
            task = asyncio.create_task(auto_pick_timer(guild))
            active_timers[guild_id] = task

@bot.command(name="pause")
async def pause(ctx):
    """현재 게임을 일시중단합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="pause", description="현재 게임을 일시중단합니다")
async def pause_slash(interaction: discord.Interaction):
    """슬래시 명령어로 게임을 일시중단합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await pause(ctx)
    
    if guild_id not in games or not games[guild_id]["active"]:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    if games[guild_id]["paused"]:
        await ctx.send("⏸️ 게임이 이미 일시중단되었습니다.")
        return
    
    games[guild_id]["paused"] = True
    await ctx.send("⏸️ 게임이 일시중단되었습니다. `!resume`으로 게임을 재시작할 수 있습니다.")

@bot.command(name="resume")
async def resume(ctx):
    """일시중단된 게임을 재시작합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="resume", description="일시중단된 게임을 재시작합니다")
async def resume_slash(interaction: discord.Interaction):
    """슬래시 명령어로 게임을 재시작합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await resume(ctx)
    
    if guild_id not in games or not games[guild_id]["active"]:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    if not games[guild_id]["paused"]:
        await ctx.send("▶️ 게임이 이미 진행 중입니다.")
        return
    
    games[guild_id]["paused"] = False
    games[guild_id]["last_turn_time"] = time.time()  # 타이머 재시작
    
    # 자동 선택 타이머 재시작 (중복 방지)
    if guild_id in active_timers:
        active_timers[guild_id].cancel()  # 기존 타이머 취소
        del active_timers[guild_id]
    task = asyncio.create_task(auto_pick_timer(ctx.guild))
    active_timers[guild_id] = task
    
    current_player = games[guild_id]["players"][games[guild_id]["turn_index"]]
    await ctx.send(f"▶️ 게임이 재시작되었습니다!\n👉 현재 차례: {current_player.mention}\n⏰ 60초 타이머가 시작되었습니다!")

@bot.command(name="stop")
async def stop(ctx):
    """현재 게임을 중단합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="stop", description="현재 게임을 중단합니다")
async def stop_slash(interaction: discord.Interaction):
    """슬래시 명령어로 게임을 중단합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await stop(ctx)
    
    if guild_id not in games:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    # 타이머 정리
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    del games[guild_id]
    await ctx.send("⏹️ 게임이 중단되었습니다.")

@bot.command(name="end")
async def end(ctx):
    """현재 게임을 강제 종료합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="end", description="현재 게임을 강제 종료합니다")
async def end_slash(interaction: discord.Interaction):
    """슬래시 명령어로 게임을 강제 종료합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await end(ctx)
    
    if guild_id not in games:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    game = games[guild_id]
    players = game["players"]
    turn_count = game["turn_count"]
    
    # 타이머 정리
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    del games[guild_id]
    await ctx.send(f"🏁 게임이 강제 종료되었습니다!\n📊 총 {turn_count}턴을 진행했습니다.\n👥 참가자: {', '.join([p.mention for p in players])}")

@bot.command(name="debug")
async def debug(ctx):
    """현재 봇 상태를 디버그합니다."""
    guild_id = ctx.guild.id

@bot.tree.command(name="debug", description="현재 봇 상태를 디버그합니다")
async def debug_slash(interaction: discord.Interaction):
    """슬래시 명령어로 봇 상태를 디버그합니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await debug(ctx)
    debug_info = f"🔍 **디버그 정보**\n"
    debug_info += f"봇 인스턴스 ID: {bot_instance_id}\n"
    debug_info += f"서버 ID: {guild_id}\n"
    debug_info += f"활성 게임 수: {len(games)}\n"
    debug_info += f"활성 타이머 수: {len(active_timers)}\n"
    debug_info += f"게임 시작 중: {'예' if guild_id in starting_games else '아니오'}\n"
    
    # 락 파일 확인
    lock_file = f"lock_{guild_id}.txt"
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                lock_content = f.read().strip()
            debug_info += f"락 파일: {lock_content}\n"
        except:
            debug_info += f"락 파일: 읽기 실패\n"
    else:
        debug_info += f"락 파일: 없음\n"
    
    if guild_id in games:
        game = games[guild_id]
        debug_info += f"현재 게임 상태: {'활성' if game['active'] else '비활성'}\n"
        debug_info += f"일시중단: {'예' if game['paused'] else '아니오'}\n"
        debug_info += f"진행된 턴: {game['turn_count']}턴\n"
        debug_info += f"참가자 수: {len(game['players'])}명\n"
    else:
        debug_info += "현재 게임: 없음\n"
    
    if guild_id in active_timers:
        debug_info += f"타이머 상태: 활성\n"
    else:
        debug_info += f"타이머 상태: 비활성\n"
    
    await ctx.send(debug_info)

@bot.command(name="help_command")
async def help_command(ctx):
    """사용 가능한 명령어를 보여줍니다."""
    help_text = """
🧩 **젠가 봇 명령어**

**!start @사용자1 @사용자2 @사용자3** - 젠가 게임 시작
**!pick** - 블록 뽑기 (자신의 차례일 때)
**!status** - 현재 게임 상태 확인
**!pause** - 게임 일시중단
**!resume** - 게임 재시작
**!stop** - 게임 중단
**!end** - 게임 강제 종료
**!debug** - 봇 상태 디버그
**!help_command** - 도움말 보기

**슬래시 명령어 (/)**
**/start @사용자1 @사용자2 @사용자3** - 젠가 게임 시작
**/pick** - 블록 뽑기
**/status** - 게임 상태 확인
**/pause** - 게임 일시중단
**/resume** - 게임 재시작
**/stop** - 게임 중단
**/end** - 게임 강제 종료
**/debug** - 봇 상태 디버그

**게임 규칙:**
- 참가자들이 순서대로 블록을 뽑습니다
- 10% 확률로 젠가가 무너집니다
- **60초 안에 `!pick` 또는 `/pick`을 하지 않으면 자동 선택됩니다!**
- 모든 블록을 뽑으면 승리!
    """
    await ctx.send(help_text)

@bot.tree.command(name="help", description="사용 가능한 명령어를 보여줍니다")
async def help_slash(interaction: discord.Interaction):
    """슬래시 명령어로 도움말을 보여줍니다."""
    class VirtualContext:
        def __init__(self, guild, author):
            self.guild = guild
            self.author = author
            self.send = interaction.response.send_message
    
    ctx = VirtualContext(interaction.guild, interaction.user)
    await help_command(ctx)

# 실행
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN 환경 변수를 설정하세요.")
        print("PowerShell: $env:DISCORD_TOKEN='your-token'")
        print("Command Prompt: set DISCORD_TOKEN=your-token")
    else:
        print("🚀 봇을 시작합니다...")
        bot.run(token)
