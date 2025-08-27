# Discord Jenga Bot

Discord에서 젠가 게임을 즐길 수 있는 봇입니다.

## 설치 방법

### 1. Python 설치
- Python 3.8 이상이 필요합니다.

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. Discord 봇 토큰 설정
- Discord Developer Portal에서 봇을 생성하고 토큰을 받으세요.
- 환경 변수로 토큰을 설정하세요:

**Windows (PowerShell):**
```powershell
$env:DISCORD_TOKEN="your-bot-token"
```

**Windows (Command Prompt):**
```cmd
set DISCORD_TOKEN=your-bot-token
```

**Linux/macOS:**
```bash
export DISCORD_TOKEN="your-bot-token"
```

### 4. 봇 실행
```bash
python bot.py
```

## 게임 방법

### 명령어
- `!start` - 젠가 게임 시작
- `!pick` - 블록 뽑기
- `!status` - 게임 상태 확인
- `!stop` - 게임 종료
- `!help_command` - 도움말

## 환경 변수

- `DISCORD_TOKEN`: Discord 봇 토큰

## 기술 스택

- Python 3.8+
- discord.py 2.4.0

## 문제 해결

### ModuleNotFoundError: No module named 'discord'
- 가상환경을 활성화하고 `pip install discord.py`를 실행하세요.

### PrivilegedIntentsRequired 오류
- Discord Developer Portal에서 "MESSAGE CONTENT INTENT"를 활성화하세요.
