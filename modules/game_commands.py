import random
import asyncio
import time
from discord.ext import commands
from .game_logic import games, active_timers, starting_games, auto_pick_timer
from .points import get_user_points, add_user_points, save_user_points

async def start_game(ctx, *members):
    guild_id = ctx.guild.id
    
    if guild_id in games:
        await ctx.send("⚠️ 이미 진행 중인 게임이 있습니다. `!stop` 명령어로 종료 후 다시 시작하세요.")
        return
    
    if guild_id in starting_games:
        await ctx.send("⚠️ 게임 시작이 이미 진행 중입니다. 잠시만 기다려주세요.")
        return
    
    players = [ctx.author] + list(members)
    
    if len(players) < 2:
        await ctx.send("⚠️ 최소 2명 이상의 참가자가 필요합니다.")
        return
    
    players = list(dict.fromkeys(players))
    starting_games.add(guild_id)
    
    try:
        random.shuffle(players)
        
        await ctx.send(f"💰 **배팅 단계 시작!**\n각 참가자가 `!bet <포인트>` 명령어로 배팅해주세요!")
        
        games[guild_id] = {
            "players": players,
            "turn_index": 0,
            "active": False,
            "paused": False,
            "last_turn_time": time.time(),
            "turn_count": 0,
            "bets": {},
            "total_pot": 0
        }
        
        for player in players:
            current_points = await get_user_points(guild_id, player.id)
            await ctx.send(f"💰 {player.mention}님, 현재 포인트: **{current_points}**\n`!bet <포인트>` 명령어로 배팅해주세요!")
        
        await ctx.send(f"🎯 **모든 참가자가 배팅을 완료하면 게임이 자동으로 시작됩니다!**")
        
    finally:
        starting_games.discard(guild_id)

async def place_bet(ctx, amount: int):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    if games[guild_id]["active"]:
        await ctx.send("⚠️ 게임이 이미 진행 중입니다. 배팅은 게임 시작 전에만 가능합니다.")
        return
    
    if amount <= 0:
        await ctx.send("⚠️ 배팅 금액은 1포인트 이상이어야 합니다.")
        return
    
    game = games[guild_id]
    player_id = ctx.author.id
    
    if not any(p.id == player_id for p in game["players"]):
        await ctx.send("⚠️ 게임에 참가하지 않은 플레이어는 배팅할 수 없습니다.")
        return
    
    if player_id in game.get("bets", {}):
        await ctx.send("⚠️ 이미 배팅을 완료했습니다.")
        return
    
    current_points = await get_user_points(guild_id, player_id)
    if current_points < amount:
        await ctx.send(f"⚠️ 보유 포인트가 부족합니다. 현재 포인트: **{current_points}**")
        return
    
    if "bets" not in game:
        game["bets"] = {}
    if "total_pot" not in game:
        game["total_pot"] = 0
    
    game["bets"][player_id] = amount
    game["total_pot"] += amount
    
    await add_user_points(guild_id, player_id, -amount)
    
    await ctx.send(f"💰 {ctx.author.mention}님이 **{amount}포인트**를 배팅했습니다!\n현재 총 배팅 금액: **{game['total_pot']}포인트**")
    
    if len(game["bets"]) == len(game["players"]):
        await ctx.send(f"🎯 **모든 참가자 배팅 완료!**\n총 배팅 금액: **{game['total_pot']}포인트**\n게임을 시작합니다!")
        
        game["active"] = True
        
        guild = ctx.guild
        if guild_id in active_timers:
            active_timers[guild_id].cancel()
            del active_timers[guild_id]
        task = asyncio.create_task(auto_pick_timer(guild))
        active_timers[guild_id] = task
        
        order = " → ".join([p.mention for p in game["players"]])
        first = game["players"][0].mention
        await ctx.send(f"🧩 **젠가 게임 시작!**\n💰 총 배팅 금액: **{game['total_pot']}포인트**\n👉 순서: {order}\n첫 번째 차례: {first}\n\n`!pick` 명령어로 블록을 뽑으세요!")

async def pick_block(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    game = games[guild_id]
    
    if not game["active"]:
        await ctx.send("⚠️ 게임이 아직 시작되지 않았습니다. 모든 참가자가 배팅을 완료해주세요.")
        return
    
    if game["paused"]:
        await ctx.send("⚠️ 게임이 일시정지되었습니다. `!resume` 명령어로 재개해주세요.")
        return
    
    current_player = game["players"][game["turn_index"]]
    if ctx.author.id != current_player.id:
        await ctx.send(f"⚠️ 아직 {current_player.mention}님의 차례입니다.")
        return
    
    game["last_turn_time"] = time.time()
    
    if random.random() < 0.1:
        game["turn_count"] += 1
        game["active"] = False
        
        if guild_id in active_timers:
            active_timers[guild_id].cancel()
            del active_timers[guild_id]
        
        loser_id = ctx.author.id
        loser_bet = game.get("bets", {}).get(loser_id, 0)
        
        if loser_bet > 0:
            winners = [p for p in game["players"] if p.id != loser_id]
            if winners:
                points_per_winner = loser_bet // len(winners)
                remainder = loser_bet % len(winners)
                
                winner_messages = []
                for i, winner in enumerate(winners):
                    points_to_give = points_per_winner + (1 if i < remainder else 0)
                    await add_user_points(guild_id, winner.id, points_to_give)
                    winner_messages.append(f"{winner.mention}: +{points_to_give}포인트")
                
                await ctx.send(f"💥 {ctx.author.mention} 이(가) 블록을 뽑다가 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!\n\n💰 **포인트 분배 결과:**\n패자 {ctx.author.mention}의 배팅 금액 **{loser_bet}포인트**를 승자들에게 분배:\n" + "\n".join(winner_messages))
            else:
                await ctx.send(f"💥 {ctx.author.mention} 이(가) 블록을 뽑다가 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!")
        else:
            await ctx.send(f"💥 {ctx.author.mention} 이(가) 블록을 뽑다가 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!")
        
        await save_user_points()
        
    else:
        next_index = (game["turn_index"] + 1) % len(game["players"])
        game["turn_index"] = next_index
        next_player = game["players"][next_index]
        
        if next_index == 0:
            game["turn_count"] += 1
            await ctx.send(f"✅ {ctx.author.mention} 이(가) 안전하게 블록을 뽑았습니다!\n📊 **{game['turn_count']}턴 완료!**\n👉 다음 차례: {next_player.mention}")
        else:
            await ctx.send(f"✅ {ctx.author.mention} 이(가) 안전하게 블록을 뽑았습니다!\n👉 다음 차례: {next_player.mention}")
        
        if guild_id in active_timers:
            active_timers[guild_id].cancel()
            del active_timers[guild_id]
        task = asyncio.create_task(auto_pick_timer(ctx.guild))
        active_timers[guild_id] = task

async def pause_game(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    game = games[guild_id]
    
    if not game["active"]:
        await ctx.send("⚠️ 게임이 아직 시작되지 않았습니다.")
        return
    
    if game["paused"]:
        await ctx.send("⚠️ 게임이 이미 일시정지되었습니다.")
        return
    
    game["paused"] = True
    
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    await ctx.send(f"⏸️ **게임이 일시정지되었습니다.**\n`!resume` 명령어로 게임을 재개할 수 있습니다.")

async def resume_game(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    game = games[guild_id]
    
    if not game["active"]:
        await ctx.send("⚠️ 게임이 아직 시작되지 않았습니다.")
        return
    
    if not game["paused"]:
        await ctx.send("⚠️ 게임이 일시정지되지 않았습니다.")
        return
    
    game["paused"] = False
    game["last_turn_time"] = time.time()
    
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    task = asyncio.create_task(auto_pick_timer(ctx.guild))
    active_timers[guild_id] = task
    
    current_player = game["players"][game["turn_index"]]
    await ctx.send(f"▶️ **게임이 재개되었습니다!**\n👉 현재 차례: {current_player.mention}\n⏰ 60초 타이머가 시작되었습니다!")

async def stop_game(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    del games[guild_id]
    
    if guild_id in active_timers:
        active_timers[guild_id].cancel()
        del active_timers[guild_id]
    
    starting_games.discard(guild_id)
    
    await ctx.send("🛑 **게임이 강제 종료되었습니다.**\n새로운 게임을 시작하려면 `!start` 명령어를 사용하세요.")

async def show_status(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in games:
        await ctx.send("⚠️ 현재 진행 중인 게임이 없습니다.")
        return
    
    game = games[guild_id]
    
    if not game["active"]:
        players = game["players"]
        bets = game.get("bets", {})
        total_pot = game.get("total_pot", 0)
        
        status_msg = f"💰 **배팅 단계 진행 중**\n\n"
        status_msg += f"👥 **참가자 목록:**\n"
        for i, player in enumerate(players):
            bet_amount = bets.get(player.id, "미배팅")
            if bet_amount != "미배팅":
                bet_amount = f"{bet_amount}포인트"
            status_msg += f"{i+1}. {player.mention} - {bet_amount}\n"
        
        status_msg += f"\n💰 **총 배팅 금액:** {total_pot}포인트\n"
        status_msg += f"🎯 **배팅 완료:** {len(bets)}/{len(players)}명"
        
        await ctx.send(status_msg)
        return
    
    players = game["players"]
    current_turn = game["turn_index"]
    current_player = players[current_turn]
    turn_count = game["turn_count"]
    bets = game.get("bets", {})
    total_pot = game.get("total_pot", 0)
    
    status_msg = f"🧩 **젠가 게임 진행 중**\n\n"
    status_msg += f"👥 **참가자 순서:**\n"
    for i, player in enumerate(players):
        if i == current_turn:
            status_msg += f"➡️ {i+1}. {player.mention} **(현재 차례)**\n"
        else:
            status_msg += f"   {i+1}. {player.mention}\n"
    
    status_msg += f"\n📊 **턴:** {turn_count}턴\n"
    status_msg += f"💰 **총 배팅 금액:** {total_pot}포인트\n"
    status_msg += f"⏰ **타이머:** 60초 카운트다운 진행 중"
    
    if game["paused"]:
        status_msg += "\n⏸️ **상태:** 일시정지됨"
    
    await ctx.send(status_msg)

