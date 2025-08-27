from .points import get_user_points, add_user_points, save_user_points, user_points

async def give_points(ctx, member, amount: int):
    if amount <= 0:
        await ctx.send("⚠️ 포인트는 1포인트 이상이어야 합니다.")
        return
    
    if ctx.author.id == member.id:
        await ctx.send("⚠️ 자신에게는 포인트를 줄 수 없습니다.")
        return
    
    guild_id = ctx.guild.id
    giver_id = ctx.author.id
    receiver_id = member.id
    
    giver_points = await get_user_points(guild_id, giver_id)
    if giver_points < amount:
        await ctx.send(f"⚠️ 보유 포인트가 부족합니다. 현재 포인트: **{giver_points}**")
        return
    
    await add_user_points(guild_id, giver_id, -amount)
    await add_user_points(guild_id, receiver_id, amount)
    
    await save_user_points()
    
    await ctx.send(f"🎁 **포인트 이전 완료!**\n{ctx.author.mention}님이 {member.mention}님에게 **{amount}포인트**를 주었습니다!\n\n💰 **현재 포인트:**\n{ctx.author.mention}: **{giver_points - amount}포인트**\n{member.mention}: **{await get_user_points(guild_id, receiver_id)}포인트**")

async def show_balance(ctx, member=None):
    guild_id = ctx.guild.id
    
    if member is None:
        member = ctx.author
    
    user_id = member.id
    points = await get_user_points(guild_id, user_id)
    
    if points >= 1000:
        status = "🏆 **부자**"
    elif points >= 500:
        status = "💰 **부유함**"
    elif points >= 200:
        status = "😊 **안정적**"
    elif points >= 100:
        status = "📊 **보통**"
    elif points >= 50:
        status = "⚠️ **주의**"
    else:
        status = "🚨 **위험**"
    
    await ctx.send(f"💰 **{member.display_name}님의 포인트 잔액**\n\n💎 **현재 포인트:** **{points}포인트**\n📊 **상태:** {status}\n\n💡 **포인트 관리:**\n• `!give @사용자 <포인트>` - 포인트 주기\n• `!point @사용자` - 다른 사용자 포인트 확인")

async def show_leaderboard(ctx):
    guild_id = ctx.guild.id
    
    if guild_id not in user_points or not user_points[guild_id]:
        await ctx.send("📊 **포인트 순위**\n\n아직 포인트 기록이 없습니다.\n게임을 시작하면 포인트 순위가 표시됩니다!")
        return
    
    guild_points = user_points[guild_id]
    sorted_users = sorted(guild_points.items(), key=lambda x: x[1], reverse=True)
    
    top_users = sorted_users[:10]
    
    leaderboard_msg = "🏆 **포인트 순위 (상위 10명)**\n\n"
    
    for i, (user_id, points) in enumerate(top_users, 1):
        try:
            user = await ctx.guild.fetch_member(user_id)
            username = user.display_name
            
            if i == 1:
                rank_emoji = "🥇"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"{i}."
            
            leaderboard_msg += f"{rank_emoji} **{username}** - **{points}포인트**\n"
            
        except:
            leaderboard_msg += f"{i}. **알 수 없는 사용자** - **{points}포인트**\n"
    
    total_users = len(guild_points)
    total_points = sum(guild_points.values())
    avg_points = total_points // total_users if total_users > 0 else 0
    
    leaderboard_msg += f"\n📊 **서버 통계:**\n"
    leaderboard_msg += f"👥 **총 사용자:** {total_users}명\n"
    leaderboard_msg += f"💰 **총 포인트:** {total_points}포인트\n"
    leaderboard_msg += f"📈 **평균 포인트:** {avg_points}포인트\n"
    leaderboard_msg += f"🏆 **1위:** {top_users[0][1] if top_users else 0}포인트"
    
    await ctx.send(leaderboard_msg)

async def points_command(ctx):
    guild_id = ctx.guild.id
    user_id = ctx.author.id
    
    points = await get_user_points(guild_id, user_id)
    await ctx.send(f"💰 {ctx.author.mention}님의 현재 포인트: **{points}포인트**")

