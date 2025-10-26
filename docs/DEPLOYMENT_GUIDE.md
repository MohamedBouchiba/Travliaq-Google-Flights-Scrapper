# 🚀 Guide de Déploiement - Production EC2 Ubuntu

Guide complet pour déployer l'API Travliaq Google Flights Scraper sur AWS EC2 Ubuntu.

---

## 📋 Prérequis

### Instance EC2
- **Type**: t3.medium minimum (2 vCPU, 4 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20 GB minimum
- **Security Group**: 
  - Port 22 (SSH)
  - Port 80 (HTTP)
  - Port 443 (HTTPS - optionnel)

### Localement
- Accès SSH à l'instance
- Git installé sur EC2

---

## 🔧 Étape 1 : Connexion et Préparation du Serveur

### 1.1 Se connecter à l'instance
```bash
ssh -i votre-cle.pem ubuntu@votre-ip-publique
```

### 1.2 Mettre à jour le système
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Installer les dépendances système
```bash
# Python et pip
sudo apt install -y python3 python3-pip python3-venv

# Chrome et dépendances
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
sudo apt update
sudo apt install -y google-chrome-stable

# ChromeDriver
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
CHROMEDRIVER_VERSION=$(cat LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip LATEST_RELEASE

# Git
sudo apt install -y git

# Nginx (optionnel mais recommandé)
sudo apt install -y nginx

# Outils de monitoring
sudo apt install -y htop curl
```

---

## 📦 Étape 2 : Installation de l'Application

### 2.1 Cloner le repository
```bash
cd /home/ubuntu
git clone https://github.com/votre-username/Travliaq-Google-Flights-Scrapper.git
cd Travliaq-Google-Flights-Scrapper
```

### 2.2 Créer l'environnement virtuel
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3 Installer les dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configurer l'environnement
```bash
# Copier le fichier de config production
cp .env.production .env

# Éditer avec vos valeurs
nano .env
```

**Configuration recommandée** :
```bash
ENVIRONMENT=production
DEBUG=false
HEADLESS=true
LOG_LEVEL=WARNING
SENTRY_DSN=votre-dsn-sentry
DATABASE_URL=sqlite:///data/flights.db
```

### 2.5 Créer les répertoires nécessaires
```bash
mkdir -p data logs screenshots
chmod 755 data logs
```

### 2.6 Tester l'installation
```bash
# Test rapide
python -c "from src.scrapers.calendar_scraper import CalendarScraper; print('✅ Import OK')"

# Test de l'API (en foreground)
python scripts/run_api.py
# Ctrl+C pour arrêter
```

---

## 🔄 Étape 3 : Configuration Systemd (Auto-start)

### 3.1 Créer le service systemd
```bash
sudo nano /etc/systemd/system/travliaq-api.service
```

**Contenu** :
```ini
[Unit]
Description=Travliaq Google Flights Scraper API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Travliaq-Google-Flights-Scrapper
Environment="PATH=/home/ubuntu/Travliaq-Google-Flights-Scrapper/.venv/bin"
ExecStart=/home/ubuntu/Travliaq-Google-Flights-Scrapper/.venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/Travliaq-Google-Flights-Scrapper/logs/api.log
StandardError=append:/home/ubuntu/Travliaq-Google-Flights-Scrapper/logs/api_error.log

[Install]
WantedBy=multi-user.target
```

### 3.2 Activer et démarrer le service
```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer au démarrage
sudo systemctl enable travliaq-api

# Démarrer le service
sudo systemctl start travliaq-api

# Vérifier le statut
sudo systemctl status travliaq-api
```

### 3.3 Commandes utiles
```bash
# Voir les logs en temps réel
sudo journalctl -u travliaq-api -f

# Redémarrer le service
sudo systemctl restart travliaq-api

# Arrêter le service
sudo systemctl stop travliaq-api

# Vérifier le statut
sudo systemctl status travliaq-api
```

---

## 🌐 Étape 4 : Configuration Nginx (Reverse Proxy)

### 4.1 Créer la configuration Nginx
```bash
sudo nano /etc/nginx/sites-available/travliaq
```

**Contenu** :
```nginx
server {
    listen 80;
    server_name votre-ip-ou-domaine.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts pour le scraping
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }
}
```

### 4.2 Activer la configuration
```bash
# Créer le lien symbolique
sudo ln -s /etc/nginx/sites-available/travliaq /etc/nginx/sites-enabled/

# Tester la configuration
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx

# Activer au démarrage
sudo systemctl enable nginx
```

---

## 🔐 Étape 5 : Sécurité et Monitoring

### 5.1 Firewall (UFW)
```bash
# Activer UFW
sudo ufw enable

# Autoriser SSH, HTTP
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp

# Vérifier
sudo ufw status
```

### 5.2 Health Check automatique
```bash
# Créer le script de monitoring
nano /home/ubuntu/health_check.sh
```

**Contenu** :
```bash
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health)

if [ $response -eq 200 ]; then
    echo "$(date): ✅ API healthy"
else
    echo "$(date): ❌ API unhealthy (HTTP $response)"
    # Redémarrer le service
    sudo systemctl restart travliaq-api
fi
```
```bash
# Rendre exécutable
chmod +x /home/ubuntu/health_check.sh

# Ajouter au crontab (toutes les 5 minutes)
crontab -e
```

**Ajouter** :
```
*/5 * * * * /home/ubuntu/health_check.sh >> /home/ubuntu/logs/health_check.log 2>&1
```

### 5.3 Backup automatique de la DB
```bash
# Créer le script de backup
nano /home/ubuntu/backup_db.sh
```

**Contenu** :
```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DB_FILE="/home/ubuntu/Travliaq-Google-Flights-Scrapper/data/flights.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_FILE $BACKUP_DIR/flights_$DATE.db
gzip $BACKUP_DIR/flights_$DATE.db

# Garder seulement les 7 derniers
ls -t $BACKUP_DIR/flights_*.db.gz | tail -n +8 | xargs -r rm

echo "$(date): ✅ Backup created"
```
```bash
# Rendre exécutable
chmod +x /home/ubuntu/backup_db.sh

# Ajouter au crontab (tous les jours à 2h du matin)
crontab -e
```

**Ajouter** :
```
0 2 * * * /home/ubuntu/backup_db.sh >> /home/ubuntu/logs/backup.log 2>&1
```

---

## 🧪 Étape 6 : Tests Post-Déploiement

### 6.1 Test du health check
```bash
curl http://localhost:8000/api/v1/health
```

**Réponse attendue** :
```json
{
  "status": "healthy",
  "version": "v1",
  "database": "ok"
}
```

### 6.2 Test de scraping
```bash
curl "http://localhost:8000/api/v1/calendar-prices?origin=BRU&destination=CDG&start_date=2025-11-01&end_date=2025-11-30&force_refresh=true"
```

### 6.3 Vérifier les logs
```bash
# Logs de l'application
tail -f /home/ubuntu/Travliaq-Google-Flights-Scrapper/logs/scraper.log

# Logs systemd
sudo journalctl -u travliaq-api -f

# Logs Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔄 Étape 7 : Mises à Jour

### Script de mise à jour
```bash
# Créer update.sh
nano /home/ubuntu/update.sh
```

**Contenu** :
```bash
#!/bin/bash
set -e

echo "🔄 Mise à jour de Travliaq..."

cd /home/ubuntu/Travliaq-Google-Flights-Scrapper

# Pull les dernières modifications
git pull

# Activer le venv
source .venv/bin/activate

# Mettre à jour les dépendances
pip install -r requirements.txt --upgrade

# Redémarrer le service
sudo systemctl restart travliaq-api

echo "✅ Mise à jour terminée"

# Vérifier le statut
sleep 3
sudo systemctl status travliaq-api
```
```bash
chmod +x /home/ubuntu/update.sh

# Pour mettre à jour :
/home/ubuntu/update.sh
```

---

## 📊 Monitoring avec Sentry

### Configuration

1. Créer un compte sur [sentry.io](https://sentry.io)
2. Créer un nouveau projet Python
3. Copier le DSN
4. Mettre à jour `.env` :
```bash
SENTRY_DSN=https://votre-dsn@sentry.io/projet-id
SENTRY_ENVIRONMENT=production
```

5. Redémarrer :
```bash
sudo systemctl restart travliaq-api
```

---

## 🐛 Dépannage

### L'API ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u travliaq-api -n 50

# Vérifier les erreurs Python
cat /home/ubuntu/Travliaq-Google-Flights-Scrapper/logs/api_error.log

# Tester manuellement
cd /home/ubuntu/Travliaq-Google-Flights-Scrapper
source .venv/bin/activate
python scripts/run_api.py
```

### Chrome/ChromeDriver ne fonctionne pas
```bash
# Vérifier Chrome
google-chrome --version

# Vérifier ChromeDriver
chromedriver --version

# Les versions doivent correspondre
```

### Out of Memory
```bash
# Vérifier la mémoire
free -h

# Ajouter du swap si nécessaire
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Base de données corrompue
```bash
# Restaurer depuis un backup
cd /home/ubuntu/Travliaq-Google-Flights-Scrapper
cp data/flights.db data/flights.db.backup
gunzip -c /home/ubuntu/backups/flights_YYYYMMDD_HHMMSS.db.gz > data/flights.db
sudo systemctl restart travliaq-api
```

---

## 📈 Optimisations Recommandées

### 1. Utiliser un proxy rotatif

Pour éviter les rate limits de Google :
- [Bright Data](https://brightdata.com)
- [Oxylabs](https://oxylabs.io)
- [ScraperAPI](https://www.scraperapi.com)

### 2. Ajouter HTTPS avec Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com
```

### 3. Monitoring avancé

- [Prometheus](https://prometheus.io) + [Grafana](https://grafana.com)
- [Datadog](https://www.datadoghq.com)
- [New Relic](https://newrelic.com)

---

## ✅ Checklist Finale

- [ ] Service systemd actif
- [ ] Nginx configuré
- [ ] Firewall activé
- [ ] Health check automatique en place
- [ ] Backups automatiques configurés
- [ ] Sentry configuré
- [ ] Tests de scraping OK
- [ ] Logs accessibles
- [ ] Script de mise à jour créé
- [ ] Documentation à jour

---

## 🆘 Support

En cas de problème :
1. Vérifier les logs (`journalctl -u travliaq-api -f`)
2. Consulter Sentry pour les erreurs
3. Vérifier le health check
4. Redémarrer le service

**Contact** : votre-email@example.com