import os
import json

POINTS_FILE = "user_points.json"
user_points = {}

async def load_user_points():
    global user_points
    try:
        if os.path.exists(POINTS_FILE):
            with open(POINTS_FILE, 'r', encoding='utf-8') as f:
                user_points = json.load(f)
                print(f"포인트 데이터를 불러왔습니다. (서버 수: {len(user_points)})")
        else:
            user_points = {}
            print("새로운 포인트 파일을 생성합니다.")
    except Exception as e:
        print(f"포인트 파일 로드 중 오류 발생: {e}")
        user_points = {}
    return user_points

async def save_user_points():
    try:
        with open(POINTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_points, f, ensure_ascii=False, indent=2)
        print("포인트 데이터를 저장했습니다.")
    except Exception as e:
        print(f"포인트 파일 저장 중 오류 발생: {e}")

async def get_user_points(guild_id, user_id):
    if guild_id not in user_points:
        user_points[guild_id] = {}
    
    if user_id not in user_points[guild_id]:
        user_points[guild_id][user_id] = 100
        await save_user_points()
    
    return user_points[guild_id][user_id]

async def add_user_points(guild_id, user_id, points_to_add):
    if guild_id not in user_points:
        user_points[guild_id] = {}
    
    if user_id not in user_points[guild_id]:
        user_points[guild_id][user_id] = 100
    
    user_points[guild_id][user_id] += points_to_add
    
    if user_points[guild_id][user_id] < 0:
        user_points[guild_id][user_id] = 0
    
    await save_user_points()
    return user_points[guild_id][user_id]

