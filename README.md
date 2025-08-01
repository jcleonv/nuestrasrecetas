# 🍽️ Family Recipe Planner

A beautiful, production-ready web application for planning your family's weekly meals and managing recipes. Built with Flask, featuring a modern glassmorphism UI design, and ready for deployment with Docker.

## ✨ Features

- 🎨 **Beautiful Modern UI** - Glassmorphism design with smooth animations
- 📱 **Fully Responsive** - Works perfectly on desktop, tablet, and mobile
- 🥘 **Recipe Management** - Add, edit, search, and organize your recipes
- 📅 **Weekly Meal Planning** - Drag-and-drop interface for planning meals
- 🛒 **Smart Grocery Lists** - Automatically generate and aggregate shopping lists
- 🔄 **Import/Export** - Backup and share your recipes in JSON format
- 🐳 **Docker Ready** - One-command deployment with Docker Compose
- 🗄️ **Supabase Integration** - Cloud database support for production
- 👥 **Multi-user Support** - Ready for family accounts (optional)

## 🚀 Quick Start (Recommended)

The fastest way to get your family recipe planner running:

### Prerequisites
- Docker and Docker Compose installed
- A domain name (optional, for HTTPS)

### 1-Command Deployment
```bash
git clone <your-repo-url>
cd recipes
./deploy.sh
```

That's it! Your recipe planner will be available at `http://localhost:8000`

## 💰 Cost-Effective Hosting Options

### Option 1: DigitalOcean Droplet ($4/month)
- 1GB RAM, 25GB SSD
- Perfect for family use
- Includes domain and SSL setup

### Option 2: Railway ($5/month)
- Automatic deployments from Git
- Built-in PostgreSQL database
- Custom domain included

### Option 3: Fly.io (Free tier available)
- 256MB RAM free tier
- Automatic scaling
- Global edge deployment

### Option 4: Self-hosted (Free)
- Home server or Raspberry Pi
- Use DuckDNS for free domain
- Cloudflare for free SSL

## 🛠️ Detailed Setup

### Environment Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   # For cloud database (recommended for production)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   
   # For local SQLite (good for testing)
   DATABASE_URL=sqlite:///data/recipes.sqlite
   
   # Security
   SECRET_KEY=your-super-secure-secret-key
   ```

### Supabase Setup (Free Cloud Database)

1. **Create a Supabase account** at https://supabase.com
2. **Create a new project** (free tier includes 500MB database)
3. **Get your credentials** from Settings > API
4. **Add them to your `.env` file**

The app will automatically create the necessary tables.

### Docker Deployment

#### Basic Deployment (SQLite)
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

#### Production Deployment (with Nginx)
```bash
# Start with reverse proxy
docker-compose --profile with-nginx up -d

# Includes rate limiting and SSL termination
```

### Manual Installation

If you prefer not to use Docker:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python database.py

# 4. Run application
python app.py  # Development
# OR
gunicorn --bind 0.0.0.0:8000 app:app  # Production
```

## 🌐 Domain and SSL Setup

### Free Domain Options
- **DuckDNS** - Free dynamic DNS
- **Freenom** - Free domain names (.tk, .ml, .ga)
- **Cloudflare** - Free SSL certificates and CDN

### SSL Certificate (Free with Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring and Backup

### Health Monitoring
The app includes a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
```

### Backup Your Data
```bash
# Create backup
./deploy.sh backup

# Backup is saved to backups/YYYYMMDD_HHMMSS/
```

### Automated Backups
Add to your crontab for daily backups:
```bash
0 2 * * * cd /path/to/your/app && ./deploy.sh backup
```

## 🔧 Management Commands

```bash
# View application logs
./deploy.sh logs

# Stop the application
./deploy.sh stop

# Restart the application
./deploy.sh restart

# Create backup
./deploy.sh backup

# Update application
git pull
docker-compose build --no-cache
docker-compose up -d
```

## 🏗️ Architecture

- **Frontend**: Modern HTML5 + TailwindCSS + Vanilla JS
- **Backend**: Flask (Python) with SQLAlchemy ORM
- **Database**: SQLite (local) or PostgreSQL (Supabase)
- **Deployment**: Docker + Docker Compose
- **Reverse Proxy**: Nginx with rate limiting
- **Security**: HTTPS, security headers, CORS protection

## 🔒 Security Features

- HTTPS/SSL termination
- Rate limiting (10 req/sec for API, 30 req/sec for static files)
- Security headers (XSS, CSRF, clickjacking protection)
- Input validation and sanitization
- Non-root Docker container
- Environment variable configuration

## 📱 Mobile Support

- Responsive design for all screen sizes
- Touch-friendly interface
- iOS/Android web app capabilities
- Optimized for mobile drag-and-drop

## 🎯 Production Checklist

- [ ] Set strong `SECRET_KEY` in production
- [ ] Configure Supabase or PostgreSQL database
- [ ] Set up domain name and SSL certificate
- [ ] Configure automated backups
- [ ] Set up monitoring (health checks)
- [ ] Configure email notifications (optional)
- [ ] Set up user authentication (if multi-user)

## 💡 Tips for Families

1. **Start Simple**: Begin with SQLite, upgrade to Supabase when needed
2. **Backup Regularly**: Use the built-in backup command weekly
3. **Organize Recipes**: Use categories and tags effectively
4. **Mobile First**: The interface works great on phones and tablets
5. **Share Access**: Multiple family members can access the same deployment

## 🤝 Contributing

This is designed to be a self-contained family application, but contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues or questions:
- Check the health endpoint: `/health`
- Review the logs: `./deploy.sh logs`
- Ensure all environment variables are set correctly
- Verify Docker and Docker Compose are running

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Enjoy planning your family meals! 🍽️**