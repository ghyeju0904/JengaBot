import random
import asyncio
from .points import add_user_points, save_user_points

games = {}
active_timers = {}
starting_games = set()

async def auto_pick_timer(guild):
    guild_id = guild.id
    
    if guild_id not in games or not games[guild_id]["active"]:
        return
    
    game = games[guild_id]
    
    if game["paused"]:
        return
    
    try:
        await asyncio.sleep(30)
        
        if guild_id not in games or not games[guild_id]["active"] or games[guild_id]["paused"]:
            return
        
        current_player = game["players"][game["turn_index"]]
        await guild.system_channel.send(f"⏰ **30초 남았습니다!**\n{current_player.mention}님, `!pick` 명령어로 블록을 뽑아주세요!")
        
        await asyncio.sleep(20)
        
        if guild_id not in games or not games[guild_id]["active"] or games[guild_id]["paused"]:
            return
        
        await guild.system_channel.send(f"⏰ **10초 남았습니다!**\n{current_player.mention}님, `!pick` 명령어로 블록을 뽑아주세요!")
        
        await asyncio.sleep(10)
        
        if guild_id not in games or not games[guild_id]["active"] or games[guild_id]["paused"]:
            return
        
        await guild.system_channel.send(f"⏰ **시간 초과!**\n{current_player.mention}님을 위해 자동으로 블록을 선택합니다...")
        
        if random.random() < 0.1:
            game["turn_count"] += 1
            game["active"] = False
            
            if guild_id in active_timers:
                active_timers[guild_id].cancel()
                del active_timers[guild_id]
            
            loser_id = current_player.id
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
                    
                    await guild.system_channel.send(f"💥 {current_player.mention}님의 자동 선택으로 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!\n\n💰 **포인트 분배 결과:**\n패자 {current_player.mention}의 배팅 금액 **{loser_bet}포인트**를 승자들에게 분배:\n" + "\n".join(winner_messages))
                else:
                    await guild.system_channel.send(f"💥 {current_player.mention}님의 자동 선택으로 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!")
            else:
                await guild.system_channel.send(f"💥 {current_player.mention}님의 자동 선택으로 젠가가 무너졌습니다!\n📊 **{game['turn_count']}번째 턴**에서 게임 종료!")
            
            await save_user_points()
            
        else:
            next_index = (game["turn_index"] + 1) % len(game["players"])
            game["turn_index"] = next_index
            next_player = game["players"][next_index]
            
            if next_index == 0:
                game["turn_count"] += 1
                await guild.system_channel.send(f"✅ {current_player.mention}님의 자동 선택으로 안전하게 블록을 뽑았습니다!\n📊 **{game['turn_count']}턴 완료!**\n👉 다음 차례: {next_player.mention}")
            else:
                await guild.system_channel.send(f"✅ {current_player.mention}님의 자동 선택으로 안전하게 블록을 뽑았습니다!\n👉 다음 차례: {next_player.mention}")
            
            if guild_id in active_timers:
                active_timers[guild_id].cancel()
                del active_timers[guild_id]
            task = asyncio.create_task(auto_pick_timer(guild))
            active_timers[guild_id] = task
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"auto_pick_timer 오류 발생: {e}")
        if guild_id in active_timers:
            del active_timers[guild_id]
