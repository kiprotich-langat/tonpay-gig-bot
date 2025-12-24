# TONPay Gig Bot

A Telegram-based freelance marketplace powered by TON blockchain. Post gigs, apply for tasks, and complete deals securely with blockchain-backed escrow—all inside Telegram.

[![TON](https://img.shields.io/badge/TON-Blockchain-0088CC)](https://ton.org)
[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

##  Overview

TONPay Gig Bot bridges clients and freelancers through Telegram with secure, blockchain-backed payments. The platform integrates gig creation, proposals, smart contract escrow, dispute resolution, ratings, and transaction history into a seamless bot experience.

### Key Highlights

- ** Smart Contract Escrow** - Payments locked on-chain until work is verified
- ** Instant Settlements** - TON blockchain ensures fast, low-cost transactions  
- ** Native Telegram** - No external websites or apps needed
- ** Dispute Protection** - Built-in mediation system with admin oversight
- ** Reputation System** - Ratings and feedback build trust over time

---

##  Features

### For Clients
- Post gigs with title, description, and TON budget
- Deposit funds to blockchain escrow automatically
- Review proposals from qualified freelancers
- Release payment upon work completion
- Rate and review freelancers

### For Freelancers  
- Browse available gigs with budget details
- Submit proposals with experience and timeline
- Receive instant TON payment on approval
- Build reputation through client ratings
- Track earnings and completed jobs

### Technical Capabilities
- **Blockchain**: Real TON mainnet/testnet smart contracts
- **Database**: SQLite for fast local storage
- **Bot Framework**: Aiogram 3.x with FSM state management
- **Async Design**: Non-blocking operations for scalability
- **Logging**: Comprehensive monitoring and error tracking

---

##  Quick Start

### Prerequisites

> **Note**: Tested on WSL. Building TON toolchain may be challenging for newer developers.

- Python 3.12+ (avoid 3.14, older versions untested)
- Telegram account
- Bot token from [@BotFather](https://t.me/BotFather)
- TON wallet (testnet recommended for development)

### Installation

**Option 1: Automated Setup**

```bash
git clone https://github.com/kiprotich-langat/tonpay-gig-bot.git
cd tonpay-gig-bot
chmod +x quick_start.sh
./quick_start.sh
```

**Option 2: Manual Installation**

```bash
# Clone repository
git clone https://github.com/kiprotich-langat/tonpay-gig-bot.git
cd tonpay-gig-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run bot
python3 bot_production.py
```

### Configuration

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_WALLET_MNEMONIC=word1 word2 word3 ... word24
USE_TESTNET=True
DATABASE_PATH=tonpay.db
```

> **Security Warning**: Never commit your `.env` file or share your mnemonic. Use testnet for development.

---

##  Using the Bot

### Client Workflow

1. **Create a Gig**
   ```
   /postgig → Enter title → Description → Price in TON
   ```

2. **Fund Escrow**
   - Bot deploys smart contract automatically
   - Send TON to generated escrow address
   - Contract locks funds on-chain

3. **Review Applications**
   ```
   /mygigs → View Applications → Accept/Reject
   ```

4. **Complete & Pay**
   ```
   Mark Complete → Funds released to freelancer instantly
   ```

### Freelancer Workflow

1. **Browse Gigs**
   ```
   /browsegigs → View available opportunities
   ```

2. **Submit Proposal**
   - Click "Apply for Gig"
   - Write proposal with experience and timeline
   - Wait for client review

3. **Get Accepted & Work**
   - Receive notification on acceptance
   - Complete work as specified

4. **Receive Payment**
   - Client marks complete
   - TON released from escrow automatically
   - Rate your experience

### Command Reference

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and see welcome message |
| `/postgig` | Create a new gig (clients) |
| `/browsegigs` | Browse available gigs (freelancers) |
| `/mygigs` | View your posted gigs and applications |
| `/myapplications` | Check status of your proposals |
| `/myjobs` | View active freelance jobs |
| `/profile` | See your stats and ratings |
| `/wallet` | Manage TON wallet connection |
| `/setwallet <address>` | Link your TON wallet |
| `/help` | Display help information |
| `/debug` | Check gig statuses (troubleshooting) |

---

##  Project Structure

```
tonpay-gig-bot/
│
├── bot_production.py          # Main bot logic & handlers
├── database.py                # SQLite operations & schema
├── ton_wallet_manager.py      # TON blockchain integration
├── escrow.fc                  # Smart contract source (FunC)
├── escrow.boc                 # Compiled contract bytecode
├── requirements.txt           # Python dependencies
├── quick_start.sh             # Automated setup script
├── .env                       # Configuration (create this)
│
├── tonpay.db                  # SQLite database (auto-generated)
└── venv/                      # Virtual environment
```

---

##  TON Blockchain Integration

### Smart Contract Architecture

The escrow system uses a FunC smart contract that:
- **Locks funds** when gig is created
- **Holds securely** until work completion
- **Releases payment** on client approval
- **Handles disputes** with admin intervention

### Operations Supported

| Operation | Code | Description |
|-----------|------|-------------|
| Initialize | `op::1` | Fund the escrow contract |
| Release | `op::2` | Pay freelancer (client/admin) |
| Refund | `op::3` | Return funds to client |
| Resolve | `op::4` | Admin dispute resolution |

### Network Configuration

**Switch between testnet and mainnet:**

In `bot_production.py` and `ton_wallet_manager.py`:

```python
# Testnet (safe for development)
ton_manager = TONWalletManager(use_testnet=True)

# Mainnet (real TON transactions)
ton_manager = TONWalletManager(use_testnet=False)
```

>  **Important**: Always test on testnet first. Mainnet transactions use real TON and cannot be reversed.

---

##  Database Schema

### Tables Overview

**users**
- Stores user profiles, wallet addresses, and ratings
- Fields: `user_id`, `username`, `wallet_address`, `rating`, `created_at`

**gigs**
- Tracks all posted gigs with status and pricing
- Fields: `id`, `client_id`, `freelancer_id`, `title`, `description`, `price`, `status`, `escrow_address`, `created_at`
- Status: `open`, `in_progress`, `completed`, `cancelled`, `disputed`

**applications**
- Manages freelancer proposals
- Fields: `id`, `gig_id`, `freelancer_id`, `proposal`, `status`, `created_at`
- Status: `pending`, `accepted`, `rejected`

**ratings**
- Stores mutual ratings and reviews
- Fields: `id`, `gig_id`, `from_user`, `to_user`, `rating`, `comment`, `created_at`

**disputes**
- Tracks conflict resolution
- Fields: `id`, `gig_id`, `raised_by`, `reason`, `status`, `resolution`, `created_at`

**transactions**
- Logs all blockchain transactions
- Fields: `id`, `gig_id`, `from_user`, `to_user`, `amount`, `tx_hash`, `created_at`

---

##  Security & Best Practices

### Built-in Protections
-  Smart contract escrow prevents payment disputes
-  No private keys stored in database or logs
-  All TON transactions recorded on-chain
-  Wallet address validation before deployment
-  Permission checks on all critical operations
-  Comprehensive error handling and logging

### User Safety Guidelines
- Never share your wallet mnemonic
- Verify wallet addresses before funding
- Use testnet for learning/testing
- Report suspicious activity to admins
- Check ratings before accepting work

---

##  Monitoring & Maintenance

### View Logs
```bash
tail -f bot.log
```

### Check Database
```bash
sqlite3 tonpay.db "SELECT * FROM users LIMIT 5;"
sqlite3 tonpay.db "SELECT * FROM gigs WHERE status='in_progress';"
```

### Health Check
```python
python3 -c "from database import Database; db = Database(); print(' DB OK')"
python3 ton_wallet_manager.py  # Tests TON connection
```

---

##  Deployment

### Deploying to Production

#### Option 1: VPS Deployment (Recommended)

**1. Prepare Your Server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12+
sudo apt install python3.12 python3.12-venv python3-pip git -y
```

**2. Clone and Setup**
```bash
# Clone repository
git clone https://github.com/kiprotich-langat/tonpay-gig-bot.git
cd tonpay-gig-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**3. Configure Environment**
```bash
# Create .env file
nano .env
```

Add your production configuration:
```env
BOT_TOKEN=your_production_bot_token
ADMIN_WALLET_MNEMONIC=your 24 word mnemonic here
USE_TESTNET=False
DATABASE_PATH=/home/user/tonpay-gig-bot/tonpay.db
LOG_LEVEL=INFO
```

**4. Run with systemd (Auto-restart)**

Create service file:
```bash
sudo nano /etc/systemd/system/tonpay-bot.service
```

Add configuration:
```ini
[Unit]
Description=TONPay Gig Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/tonpay-gig-bot
Environment="PATH=/home/your_username/tonpay-gig-bot/venv/bin"
ExecStart=/home/your_username/tonpay-gig-bot/venv/bin/python bot_production.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tonpay-bot
sudo systemctl start tonpay-bot
sudo systemctl status tonpay-bot
```

**5. Monitor Logs**
```bash
sudo journalctl -u tonpay-bot -f
```

#### Option 2: Screen/tmux (Simple)

```bash
# Install screen
sudo apt install screen -y

# Start in screen session
screen -S tonpay
cd tonpay-gig-bot
source venv/bin/activate
python3 bot_production.py

# Detach: Ctrl+A then D
# Reattach: screen -r tonpay
```

#### Option 3: Docker Deployment

**Create Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot_production.py"]
```

**Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  tonpay-bot:
    build: .
    container_name: tonpay-gig-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./tonpay.db:/app/tonpay.db
      - ./logs:/app/logs
```

**Deploy:**
```bash
docker-compose up -d
docker-compose logs -f
```

### Pre-Deployment Checklist

Before going live on mainnet:

- [ ]  Tested thoroughly on testnet
- [ ]  Admin wallet funded with sufficient TON (minimum 2-3 TON)
- [ ]  Backup `.env` file and mnemonic securely
- [ ]  Set `USE_TESTNET=False` in production
- [ ]  Configure proper logging and monitoring
- [ ]  Setup automated backups for `tonpay.db`
- [ ]  Verify bot commands work correctly
- [ ]  Test escrow deployment end-to-end
- [ ]  Enable systemd auto-restart
- [ ]  Setup alerts for bot downtime

### Security for Production

**1. Secure Your Server**
```bash
# Setup firewall
sudo ufw allow 22
sudo ufw enable

# Create dedicated user
sudo adduser tonpay
sudo su - tonpay
```

**2. Protect Sensitive Files**
```bash
chmod 600 .env
chmod 600 tonpay.db
```

**3. Regular Backups**
```bash
# Automated daily backup
crontab -e
```

Add:
```cron
0 2 * * * cp /home/user/tonpay-gig-bot/tonpay.db /home/user/backups/tonpay-$(date +\%Y\%m\%d).db
```

**4. Monitor Bot Health**

Use a monitoring service:
- **UptimeRobot** - Free uptime monitoring
- **Better Stack** - Log aggregation
- **Prometheus + Grafana** - Advanced metrics

### Updating the Bot

```bash
# Stop bot
sudo systemctl stop tonpay-bot

# Backup database
cp tonpay.db tonpay.db.backup

# Pull updates
git pull origin main

# Reinstall dependencies if needed
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart bot
sudo systemctl start tonpay-bot
sudo systemctl status tonpay-bot
```

### Cost Estimates

**Monthly VPS (e.g., DigitalOcean, Hetzner, Linode):**
- Basic: $5-10/month (1GB RAM, sufficient for 100-500 users)
- Standard: $15-20/month (2GB RAM, 1000+ users)

**TON Mainnet Costs:**
- Contract deployment: ~0.05-0.1 TON per gig
- Transaction fees: ~0.01-0.02 TON per operation
- Recommended admin wallet: 2-5 TON buffer

**Example for 50 gigs/month:**
- Deployment: 5 TON
- Operations: 1 TON
- **Total: ~6 TON/month** (~$30-40 depending on TON price)

### Recommended VPS Providers

| Provider | Starting Price | Region | Good For |
|----------|---------------|--------|----------|
| [Hetzner](https://hetzner.com) | €4.51/mo | EU | Best value |
| [DigitalOcean](https://digitalocean.com) | $6/mo | Global | Easy setup |
| [Linode](https://linode.com) | $5/mo | Global | Reliable |
| [Vultr](https://vultr.com) | $6/mo | Global | Fast deployment |

---

##  Testing

### Verify Installation
```bash
# Test database initialization
python3 -c "from database import Database; Database().init_db()"

# Test TON wallet manager
python3 ton_wallet_manager.py

# Run bot in development
python3 bot_production.py
```

### Manual Testing Checklist
- [ ] Bot responds to `/start`
- [ ] Gig posting flow completes
- [ ] Applications submit successfully
- [ ] Escrow contract deploys on-chain
- [ ] Payment releases to freelancer wallet
- [ ] Ratings update user profiles
- [ ] Notifications sent correctly

---

##  Troubleshooting

### Common Issues

**"Admin wallet not initialized"**
- Ensure `.env` has valid `ADMIN_WALLET_MNEMONIC`
- Must be exactly 24 words separated by spaces

**"Failed to connect to TON"**
- Check internet connection
- Verify `pytoniq` installation: `pip install pytoniq pytoniq-core`
- Try testnet first before mainnet

**"Contract deployment failed"**
- Ensure admin wallet has sufficient TON balance
- Testnet: Get free TON from [@testgiver_ton_bot](https://t.me/testgiver_ton_bot)
- Mainnet: Fund wallet before deploying

**Database errors**
- Delete `tonpay.db` and restart bot to reset
- Check file permissions: `chmod 644 tonpay.db`

---

##  Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
git clone https://github.com/kiprotich-langat/tonpay-gig-bot.git
cd tonpay-gig-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

##  Contact & Support

- **Telegram**: [@bytes_kip](https://t.me/bytes_kip)
- **Email**: kiprotichlangat@proton.me
- **GitHub**: [kiprotich-langat](https://github.com/kiprotich-langat)

---

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

##  Acknowledgments

Built with:
- [Aiogram](https://github.com/aiogram/aiogram) - Telegram Bot Framework
- [TON](https://ton.org) - The Open Network Blockchain
- [pytoniq](https://github.com/yungwine/pytoniq) - TON Python Library
- SQLite - Embedded Database



---



If you find this project useful, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=kiprotich-langat/tonpay-gig-bot&type=Date)](https://star-history.com/#kiprotich-langat/tonpay-gig-bot&Date)

---

**Made with love for the TON Community**
