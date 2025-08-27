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
bot = commands.Bot(command_prefix="!", intents=intents)

# 게임 상태 저장용 변수
games = {}  # {guild_id: {"players": [], "turn_index": 0, "active": True, "paused": False, "last_turn_time": timestamp, "turn_count": 0}}
active_timers = {}  # {guild_id: task} - 활성 타이머 추적
starting_games = set()  # 현재 게임 시작 중인 서버 ID들

# 봇 인스턴스 추적
bot_instance_id = str(uuid.uuid4())[:8]
print(f"🆔 봇 인스턴스 ID: {bot_instance_id}")



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
    
    # 60초가 지났는지 확인
    if current_time - last_turn_time >= 60:
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
            
            # 메시지를 보낼 채널 찾기
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

async def start_game(ctx, members):
    """게임 시작 로직 (공통 함수)"""
    if not members:
        await ctx.send("⚠️ 최소 한 명 이상의 참가자를 멘션해주세요.\n사용법: `!start @사용자1 @사용자2 @사용자3`")
        return

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

async def pick_block(ctx):
    """블록 뽑기 로직 (공통 함수)"""
    guild_id = ctx.guild.id

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

async def show_status(ctx):
    """게임 상태 표시 로직 (공통 함수)"""
    guild_id = ctx.guild.id
    
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

async def pause_game(ctx):
    """게임 일시중단 로직 (공통 함수)"""
    guild_id = ctx.guild.id
    
    if guild_id not in games or not games[guild_id]["active"]:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    if games[guild_id]["paused"]:
        await ctx.send("⏸️ 게임이 이미 일시중단되었습니다.")
        return
    
    games[guild_id]["paused"] = True
    await ctx.send("⏸️ 게임이 일시중단되었습니다. `!resume`으로 게임을 재시작할 수 있습니다.")

async def resume_game(ctx):
    """게임 재시작 로직 (공통 함수)"""
    guild_id = ctx.guild.id
    
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

async def stop_game(ctx):
    """게임 중단 로직 (공통 함수)"""
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 진행 중인 게임이 없습니다.")
        return
    
    # 타이머 정리
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    del games[guild_id]
    await ctx.send("⏹️ 게임이 중단되었습니다.")

async def end_game(ctx):
    """게임 강제 종료 로직 (공통 함수)"""
    guild_id = ctx.guild.id
    
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



async def show_help(ctx):
    """도움말 표시 로직 (공통 함수)"""
    help_text = """
🧩 **젠가 봇 명령어**

**!start @사용자1 @사용자2 @사용자3** - 젠가 게임 시작
**!pick** - 블록 뽑기 (자신의 차례일 때)
**!status** - 현재 게임 상태 확인
**!pause** - 게임 일시중단
**!resume** - 게임 재시작
**!stop** - 게임 중단
**!end** - 게임 강제 종료
**!help_command** - 도움말 보기

**게임 규칙:**
- 참가자들이 순서대로 블록을 뽑습니다
- 10% 확률로 젠가가 무너집니다
- **60초 안에 `!pick`을 하지 않으면 자동 선택됩니다!**
- 모든 블록을 뽑으면 승리!
    """
    await ctx.send(help_text)

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
    


# ! 명령어들
@bot.command(name="start")
async def start_command(ctx, *members: discord.Member):
    """새로운 젠가 게임을 시작합니다."""
    await start_game(ctx, members)

@bot.command(name="pick")
async def pick_command(ctx):
    """자신의 차례일 때 블록을 뽑습니다."""
    await pick_block(ctx)

@bot.command(name="status")
async def status_command(ctx):
    """현재 게임 상태를 확인합니다."""
    await show_status(ctx)

@bot.command(name="pause")
async def pause_command(ctx):
    """현재 게임을 일시중단합니다."""
    await pause_game(ctx)

@bot.command(name="resume")
async def resume_command(ctx):
    """일시중단된 게임을 재시작합니다."""
    await resume_game(ctx)

@bot.command(name="stop")
async def stop_command(ctx):
    """현재 게임을 중단합니다."""
    await stop_game(ctx)

@bot.command(name="end")
async def end_command(ctx):
    """현재 게임을 강제 종료합니다."""
    await end_game(ctx)



@bot.command(name="help_command")
async def help_command(ctx):
    """사용 가능한 명령어를 보여줍니다."""
    await show_help(ctx)



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
