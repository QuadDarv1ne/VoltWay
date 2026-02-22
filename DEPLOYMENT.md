# 🚀 VoltWay - Руководство по развертыванию

Полное руководство по развертыванию VoltWay в различных окружениях.

## 📋 Содержание

- [Локальная разработка](#локальная-разработка)
- [Docker развертывание](#docker-развертывание)
- [Production развертывание](#production-развертывание)
- [Мониторинг и логирование](#мониторинг-и-логирование)
- [Backup и восстановление](#backup-и-восстановление)
- [Troubleshooting](#troubleshooting)

---

## 🖥️ Локальная разработка

### Предварительные требования

```bash
# Python 3.8+
python --version

# PostgreSQL (опционально, можно использовать SQLite)
psql --version

# Redis (опционально, есть in-memory fallback)
redis-cli --version
```

### Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/QuadDarv1ne/VoltWay.git
cd VoltWay

# 2. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить окружение
cp .env.example .env
# Отредактировать .env с вашими настройками

# 5. Применить миграции
alembic upgrade head

# 6. Добавить тестовые данные
python add_sample_data.py

# 7. Создать admin API ключ
python manage_api_keys.py create --name "Dev Admin" --role admin

# 8. Запустить сервер
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Проверка

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

---

## 🐳 Docker развертывание

### Development

```bash
# 1. Запустить все сервисы
docker-compose -f docker-compose.dev.yml up -d

# 2. Применить миграции
docker-compose exec app alembic upgrade head

# 3. Добавить тестовые данные
docker-compose exec app python add_sample_data.py

# 4. Создать admin ключ
docker-compose exec app python manage_api_keys.py create \
  --name "Docker Admin" --role admin

# 5. Проверить логи
docker-compose logs -f app

# 6. Остановить
docker-compose down
```

### Production

```bash
# 1. Настроить production окружение
cp .env.example .env.production
# Отредактировать .env.production

# 2. Собрать production образ
docker-compose -f docker-compose.prod.yml build

# 3. Запустить
docker-compose -f docker-compose.prod.yml up -d

# 4. Применить миграции
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# 5. Создать admin ключ
docker-compose -f docker-compose.prod.yml exec app \
  python manage_api_keys.py create --name "Prod Admin" --role admin

# 6. Проверить health
curl https://your-domain.com/health/detailed
```

---

## 🌐 Production развертывание

### На VPS (Ubuntu 20.04+)

#### 1. Подготовка сервера

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установить Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
```

#### 2. Настройка приложения

```bash
# Клонировать репозиторий
git clone https://github.com/QuadDarv1ne/VoltWay.git
cd VoltWay

# Настроить окружение
cp .env.example .env.production
nano .env.production

# Важные настройки для production:
# DEBUG=false
# DATABASE_URL=postgresql://user:pass@db:5432/voltway
# REDIS_URL=redis://redis:6379
# SECRET_KEY=<generate-secure-key>
# ALLOWED_ORIGINS=https://your-domain.com
# SENTRY_DSN=<your-sentry-dsn>
```

#### 3. SSL сертификаты (Let's Encrypt)

```bash
# Установить certbot
sudo apt install certbot python3-certbot-nginx -y

# Получить сертификат
sudo certbot certonly --standalone -d your-domain.com

# Сертификаты будут в:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# Настроить автообновление
sudo certbot renew --dry-run
```

#### 4. Nginx конфигурация

```nginx
# /etc/nginx/sites-available/voltway
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Активировать конфигурацию
sudo ln -s /etc/nginx/sites-available/voltway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Запуск приложения

```bash
# Запустить с production конфигурацией
docker-compose -f docker-compose.prod.yml up -d

# Применить миграции
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Создать admin ключ
docker-compose -f docker-compose.prod.yml exec app \
  python manage_api_keys.py create \
  --name "Production Admin" \
  --role admin \
  --description "Main production admin key"

# Сохранить ключ в безопасном месте!
```

#### 6. Настройка systemd (автозапуск)

```bash
# Создать systemd service
sudo nano /etc/systemd/system/voltway.service
```

```ini
[Unit]
Description=VoltWay Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/VoltWay
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Активировать service
sudo systemctl enable voltway
sudo systemctl start voltway
sudo systemctl status voltway
```

---

## 📊 Мониторинг и логирование

### Prometheus + Grafana

```bash
# Запустить мониторинг стек
cd monitoring
docker-compose up -d

# Доступ:
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### Настройка Grafana

1. Добавить Prometheus data source:
   - URL: http://prometheus:9090
   - Access: Server

2. Импортировать дашборд:
   - Import → Upload JSON
   - Выбрать `monitoring/grafana/provisioning/dashboards/metrics.json`

### Логирование

```bash
# Просмотр логов
docker-compose logs -f app

# Фильтр по уровню
docker-compose logs app | grep ERROR

# Последние 100 строк
docker-compose logs --tail=100 app

# Экспорт логов
docker-compose logs app > app.log
```

### Sentry интеграция

```bash
# В .env.production
SENTRY_DSN=https://your-key@sentry.io/project-id

# Проверить интеграцию
curl -X POST https://your-domain.com/api/v1/test-error
# Ошибка должна появиться в Sentry
```

---

## 💾 Backup и восстановление

### Database Backup

```bash
# PostgreSQL backup
docker-compose exec db pg_dump -U voltway_user voltway > backup_$(date +%Y%m%d).sql

# Автоматический backup (cron)
0 2 * * * cd /home/user/VoltWay && docker-compose exec -T db pg_dump -U voltway_user voltway > /backups/voltway_$(date +\%Y\%m\%d).sql

# Очистка старых backup (хранить 30 дней)
find /backups -name "voltway_*.sql" -mtime +30 -delete
```

### Database Restore

```bash
# Восстановление из backup
docker-compose exec -T db psql -U voltway_user voltway < backup_20260222.sql
```

### API Keys Backup

```bash
# Экспорт API ключей
docker-compose exec app python manage_api_keys.py list > api_keys_backup.txt

# Важно: Храните backup в безопасном месте!
```

### Full System Backup

```bash
# Backup всего проекта
tar -czf voltway_full_backup_$(date +%Y%m%d).tar.gz \
  VoltWay/ \
  /backups/voltway_*.sql \
  /etc/nginx/sites-available/voltway \
  /etc/letsencrypt/live/your-domain.com/

# Загрузить на удаленное хранилище
# AWS S3
aws s3 cp voltway_full_backup_*.tar.gz s3://your-bucket/backups/

# rsync на другой сервер
rsync -avz voltway_full_backup_*.tar.gz user@backup-server:/backups/
```

---

## 🔧 Troubleshooting

### Проблема: Приложение не запускается

```bash
# Проверить логи
docker-compose logs app

# Проверить порты
sudo netstat -tulpn | grep 8000

# Проверить переменные окружения
docker-compose exec app env | grep DATABASE_URL
```

### Проблема: Database connection failed

```bash
# Проверить статус PostgreSQL
docker-compose ps db

# Проверить логи БД
docker-compose logs db

# Проверить подключение
docker-compose exec app python -c "from app.database import engine; print(engine.url)"

# Пересоздать БД
docker-compose down -v
docker-compose up -d db
sleep 10
docker-compose exec app alembic upgrade head
```

### Проблема: Redis unavailable

```bash
# Проверить Redis
docker-compose ps redis
docker-compose logs redis

# Проверить подключение
docker-compose exec redis redis-cli ping

# Приложение работает без Redis (in-memory cache)
# Но для production рекомендуется Redis
```

### Проблема: High memory usage

```bash
# Проверить использование памяти
docker stats

# Ограничить память для контейнера
# В docker-compose.yml:
services:
  app:
    mem_limit: 512m
    mem_reservation: 256m
```

### Проблема: Slow response times

```bash
# Проверить метрики
curl http://localhost:8000/metrics

# Проверить cache hit rate
curl -H "X-API-Key: admin-key" \
  http://localhost:8000/api/v1/admin/cache/stats

# Проверить circuit breakers
curl -H "X-API-Key: admin-key" \
  http://localhost:8000/api/v1/admin/circuit-breakers

# Проверить индексы БД
docker-compose exec db psql -U voltway_user voltway -c "\di"
```

---

## 🔐 Security Checklist

### Pre-deployment

- [ ] Изменен SECRET_KEY на случайный
- [ ] DEBUG=false в production
- [ ] Настроены ALLOWED_ORIGINS
- [ ] Установлен SSL сертификат
- [ ] Настроен firewall (UFW/iptables)
- [ ] Изменены пароли БД по умолчанию
- [ ] Создан admin API ключ
- [ ] Настроен Sentry для мониторинга ошибок

### Post-deployment

- [ ] Проверен HTTPS
- [ ] Проверены security headers
- [ ] Настроены backup
- [ ] Настроен мониторинг
- [ ] Проверена ротация логов
- [ ] Документированы процедуры восстановления
- [ ] Проведен security audit

---

## 📈 Performance Tuning

### Database

```sql
-- Анализ медленных запросов
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Обновить статистику
ANALYZE;

-- Пересоздать индексы
REINDEX DATABASE voltway;
```

### Application

```python
# В .env
# Увеличить connection pool
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Настроить worker'ы
WORKERS=4  # CPU cores * 2 + 1
```

### Nginx

```nginx
# Кэширование статики
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Gzip сжатие
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

---

## 📞 Поддержка

- **Documentation**: https://github.com/QuadDarv1ne/VoltWay
- **Issues**: https://github.com/QuadDarv1ne/VoltWay/issues
- **Email**: contact@voltway.dev

---

**Версия**: 1.0.0  
**Последнее обновление**: 2026-02-22
