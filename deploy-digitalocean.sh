#!/bin/bash

# DigitalOcean Deployment Script for nuestrasrecetas.club
# Run this script on your DigitalOcean droplet

set -e

echo "🚀 Setting up nuestrasrecetas.club on DigitalOcean..."

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
echo "📂 Installing Git..."
apt-get install -y git curl

# Create deployment directory
echo "📁 Setting up deployment directory..."
mkdir -p /opt/nuestrasrecetas
cd /opt/nuestrasrecetas

# Clone repository (you'll need to set this up)
echo "📥 Cloning repository..."
echo "⚠️  You need to set up GitHub access for this server"
echo "   Run: ssh-keygen -t ed25519 -C 'your-email@example.com'"
echo "   Then add the public key to your GitHub repository as a deploy key"
read -p "Press enter when you've added the deploy key to GitHub..."

# Clone the repository
git clone git@github.com:yourusername/nuestrasrecetas.git .

# Create .env file
echo "🔐 Creating environment file..."
cat > .env << EOF
# Production Environment Variables
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
USE_SUPABASE=True

# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key

# Flask Configuration
FLASK_ENV=production
PORT=8000
EOF

echo "⚠️  IMPORTANT: Edit /opt/nuestrasrecetas/.env with your actual values!"

# Set up firewall
echo "🔥 Configuring firewall..."
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

# Set up SSL with Let's Encrypt
echo "🔒 Setting up SSL certificate..."
apt-get install -y certbot
certbot certonly --standalone -d nuestrasrecetas.club --agree-tos -m your-email@example.com -n

# Create SSL renewal cron job
echo "0 0,12 * * * root certbot renew --quiet" >> /etc/crontab

# Start the application
echo "🚀 Starting application..."
docker-compose up -d --profile with-nginx

echo "✅ Deployment complete!"
echo ""
echo "🌐 Your application should be available at: https://nuestrasrecetas.club"
echo ""
echo "📝 Next steps:"
echo "1. Edit /opt/nuestrasrecetas/.env with your actual Supabase credentials"
echo "2. Update GitHub repository secrets for auto-deployment"
echo "3. Point your domain DNS to this server's IP address"
echo ""
echo "🔧 To check logs: docker-compose logs -f"
echo "🔄 To restart: docker-compose restart"