# -*- coding: utf-8 -*-
import os
import discord
from discord.ext import commands
import uuid
from discord.ext import commands
from modules import *

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

bot_instance_id = str(uuid.uuid4())[:8]
print(f"봇 인스턴스 ID: {bot_instance_id}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Connected to {len(bot.guilds)} guild(s)")
    
    global games, active_timers, starting_games
    games.clear()
    active_timers.clear()
    starting_games.clear()
    
    await load_user_points()
    
    print("🧹 게임 상태 초기화 완료")
    print("💾 포인트 데이터 로드 완료")

@bot.command(name="start")
async def start_command(ctx, *members: discord.Member):
    await start_game(ctx, *members)

@bot.command(name="bet")
async def bet_command(ctx, amount: int):
    await place_bet(ctx, amount)

@bot.command(name="pick")
async def pick_command(ctx):
    await pick_block(ctx)

@bot.command(name="pause")
async def pause_command(ctx):
    await pause_game(ctx)

@bot.command(name="resume")
async def resume_command(ctx):
    await resume_game(ctx)

@bot.command(name="stop")
async def stop_command(ctx):
    await stop_game(ctx)

@bot.command(name="status")
async def status_command(ctx):
    await show_status(ctx)

@bot.command(name="points")
async def points_command_handler(ctx):
    await points_command(ctx)

@bot.command(name="help")
async def help_command(ctx):
    await show_help(ctx)

@bot.command(name="give")
async def give_command(ctx, member: discord.Member, amount: int):
    await give_points(ctx, member, amount)

@bot.command(name="point")
async def point_command(ctx, member: discord.Member = None):
    await show_balance(ctx, member)

@bot.command(name="leaderboard")
async def leaderboard_command(ctx):
    await show_leaderboard(ctx)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ 오류: DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("💡 해결 방법:")
        print("   1. PowerShell에서: $env:DISCORD_TOKEN='your-bot-token'")
        print("   2. 또는 .env 파일 생성 후 DISCORD_TOKEN=your-bot-token 추가")
        exit(1)
    
    try:
        print("🚀 젠가 봇을 시작합니다...")
        bot.run(token)
    except discord.LoginFailure:
        print("❌ 오류: Discord 토큰이 유효하지 않습니다.")
        print("💡 토큰을 확인하고 다시 시도하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 봇 실행 중 예상치 못한 오류가 발생했습니다.")
