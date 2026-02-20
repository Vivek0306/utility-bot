# 🤖 Telegram Utility Bot

A persistent Telegram bot running on GCP, containerized with Docker, deployable anywhere.

---

## 📁 Project Structure
```
utility-bot/
├── bot.py               # Main bot code
├── Dockerfile           # Container recipe
├── docker-compose.yml   # Container runner
├── requirements.txt     # Python dependencies
├── .env                 # Secrets (never commit this)
├── .gitignore           # Excludes .env from git
└── update.sh            # One-command deploy script
```

---

## ⚙️ How It Works
```
You → Telegram → GCP VM → Docker Container → bot.py → reply back
```
- Bot polls Telegram every few seconds for new messages
- Only responds to your chat ID (security lock)
- Docker keeps it running 24/7, auto-restarts on crash

---

## 🚀 First Time Setup

### 1. Get a Bot Token
- Message `@BotFather` on Telegram
- Send `/newbot` → follow steps → copy token
- Get your chat ID from `@userinfobot`

### 2. GCP VM Setup
- Go to GCP Console → Compute Engine → Create Instance
- **Region:** `us-central1` | **Machine:** `e2-micro` | **OS:** Ubuntu 22.04 LTS
- Enable HTTP + HTTPS firewall → Create
- Click SSH to open terminal

### 3. Install Docker on VM
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
sudo apt install docker-compose-plugin -y
```

### 4. Clone Your Repo
```bash
git clone https://github.com/yourusername/utility-bot.git
cd utility-bot
```

### 5. Create `.env` on VM
```bash
nano .env
```
```
BOT_TOKEN=your_token_here
ALLOWED_CHAT_ID=your_chat_id_here
```

### 6. Build and Run
```bash
docker compose build
docker compose up -d
```

---

## 🔄 Updating the Bot

**On your laptop:**
```bash
git add .
git commit -m "what you changed"
git push
```

**On the VM:**
```bash
cd ~/utility-bot && ./update.sh
```

---

## 🐳 Useful Docker Commands
| Command | What it does |
|---|---|
| `docker compose up -d` | Start bot in background |
| `docker compose down` | Stop bot |
| `docker compose ps` | Check if running |
| `docker compose logs -f` | View live logs |
| `docker compose up -d --build` | Rebuild + restart |

---

## 💬 Bot Commands
| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/ping` | Check if bot is alive |
| `/help` | Show command list |

---

## 🔁 Moving to a New GCP VM
1. Create new VM
2. Install Docker (Step 3 above)
3. Clone repo (Step 4)
4. Recreate `.env` (Step 5)
5. `docker compose up -d`

Done in under 5 minutes. ✅

---

## 🛣️ Roadmap
- [ ] `/stats` — CPU, RAM, disk usage
- [ ] `/shell` — run remote commands
- [ ] `/ip` — get public IP
- [ ] `/remind` — set reminders
- [ ] Auto-deploy on `git push` (CI/CD)