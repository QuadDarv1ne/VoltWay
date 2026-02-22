# 🚀 VoltWay - Шпаргалка разработчика

## Быстрый старт

```bash
# Установка
pip install -r requirements.txt

# Настройка
cp .env.example .env

# Миграции
alembic upgrade head

# Запуск
uvicorn app.main:app --reload
```

## Docker

```bash
# Запуск
docker-compose up -d

# Логи
docker-compose logs -f app

# Остановка
docker-compose down

# Пересборка
docker-compose build --no-cache
```

## API Эндпоинты

### Основные
```bash
GET  /                          # Главная страница
GET  /docs                      # Swagger UI
GET  /health                    # Health check
GET  /health/detailed           # Детальный health check
```

### Станции
```bash
GET  /api/v1/stations           # Список станций
GET  /api/v1/stations/{id}      # Конкретная станция
POST /api/v1/stations/update_cache  # Обновить кэш
```

### Admin (требует X-API-Key с ролью admin)
```bash
# Circuit Breakers
GET  /api/v1/admin/circuit-breakers        # Статус circuit breakers
POST /api/v1/admin/circuit-breakers/{name}/reset  # Сброс breaker

# Cache Management
GET  /api/v1/admin/cache/stats             # Статистика кэша
POST /api/v1/admin/cache/clear             # Очистить кэш
POST /api/v1/admin/cache/clear-stations    # Очистить кэш станций

# API Key Management
POST   /api/v1/admin/api-keys              # Создать API ключ
GET    /api/v1/admin/api-keys              # Список ключей
GET    /api/v1/admin/api-keys/stats        # Статистика ключей
DELETE /api/v1/admin/api-keys/{id}         # Деактивировать ключ
```

## Тестирование

```bash
# Все тесты
pytest -v

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_circuit_breaker.py -v

# Конкретный тест
pytest tests/test_circuit_breaker.py::test_circuit_breaker_opens_after_failures -v
```

## Миграции БД

```bash
# Применить все
alembic upgrade head

# Откатить одну
alembic downgrade -1

# Создать новую
alembic revision -m "description"

# История
alembic history

# Текущая версия
alembic current
```

## Логирование

```python
# Обычное
import logging
logger = logging.getLogger(__name__)
logger.info("Message")

# Структурированное
from app.utils.structured_logging import get_structured_logger
logger = get_structured_logger(__name__)
logger.info("Message", user_id=123, action="login")
```

## Repository Pattern

```python
from app.repositories.station import station_repository
from app.core.dependencies import get_db

async def my_function(db: AsyncSession = Depends(get_db)):
    # Получить по ID
    station = await station_repository.get(db, station_id)
    
    # Получить список
    stations = await station_repository.get_multi(db, skip=0, limit=10)
    
    # По локации
    stations = await station_repository.get_by_location(
        db, latitude=55.7558, longitude=37.6173, radius_km=10.0
    )
    
    # С фильтрами
    stations = await station_repository.get_by_filters(
        db, connector_type="CCS", min_power_kw=50.0
    )
```

## Circuit Breaker

```python
from app.services.circuit_breaker import open_charge_map_breaker

# Использование
try:
    result = await open_charge_map_breaker.call(my_function, arg1, arg2)
except CircuitBreakerOpenError:
    # Circuit открыт, сервис недоступен
    pass

# Статистика
stats = open_charge_map_breaker.get_stats()

# Ручной сброс
open_charge_map_breaker.reset()
```

## Retry Decorator

```python
from app.utils.retry import async_retry

@async_retry(max_attempts=3, delay=1.0, backoff=2.0)
async def my_function():
    # Ваш код
    pass

# Для sync функций
from app.utils.retry import sync_retry

@sync_retry(max_attempts=3, delay=1.0)
def my_sync_function():
    pass
```

## Валидация

```python
from app.utils.validators import (
    validate_coordinates,
    validate_radius,
    validate_connector_type,
    validate_power,
)

# Координаты
validate_coordinates(55.7558, 37.6173)  # OK
validate_coordinates(100, 200)  # HTTPException

# Радиус
validate_radius(10.0)  # OK
validate_radius(-5.0)  # HTTPException

# Тип разъема
connector = validate_connector_type("CCS")  # OK, возвращает sanitized

# Мощность
validate_power(50.0)  # OK
validate_power(-10.0)  # HTTPException
```

## Кэширование

```python
from app.utils.cache.manager import cache

# Получить
value = cache.get("key")

# Установить (TTL 10 минут)
cache.set("key", value, expire=600)

# Удалить
cache.delete("key")

# Очистить всё
cache.clear()

# Очистить станции
cache.clear_station_cache()

# Статистика
stats = cache.stats()
```

## Переменные окружения

```bash
# Приложение
APP_NAME=VoltWay
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# База данных
DATABASE_URL=sqlite:///./voltway.db
# или
DATABASE_URL=postgresql://user:pass@localhost:5432/voltway

# Redis
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true

# API ключи
OPEN_CHARGE_MAP_API_KEY=your_key
API_NINJAS_KEY=your_key

# Безопасность
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Производительность
ENABLE_COMPRESSION=true
COMPRESSION_MINIMUM_SIZE=500

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD_SECONDS=60

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Мониторинг
SENTRY_DSN=your_sentry_dsn
```

## Makefile команды

```bash
make help          # Показать помощь
make install       # Установить зависимости
make dev-run       # Запустить dev сервер
make test          # Запустить тесты
make build         # Собрать Docker образы
make deploy        # Развернуть production
make clean         # Очистить артефакты
make logs          # Показать логи
make db-migrate    # Применить миграции
make db-reset      # Сбросить БД
make format        # Форматировать код
make lint          # Проверить код
make quality       # Все проверки качества
```

## API Key Management

```bash
# Создать admin ключ
python manage_api_keys.py create --name "Admin" --role admin

# Создать user ключ с кастомным rate limit
python manage_api_keys.py create \
  --name "Mobile App" \
  --role user \
  --rate-limit 1000 \
  --rate-period 60 \
  --expires-in-days 365

# Список всех ключей
python manage_api_keys.py list

# Информация о ключе
python manage_api_keys.py info --id 1

# Деактивировать ключ
python manage_api_keys.py deactivate --id 1
```

## Полезные curl команды

```bash
# Health check
curl http://localhost:8000/health

# Детальный health check
curl http://localhost:8000/health/detailed

# Список станций
curl "http://localhost:8000/api/v1/stations?skip=0&limit=10"

# Поиск по локации
curl "http://localhost:8000/api/v1/stations?latitude=55.7558&longitude=37.6173&radius_km=10"

# Circuit breakers (с API ключом admin)
curl -H "X-API-Key: your-admin-key" \
  http://localhost:8000/api/v1/admin/circuit-breakers

# Статистика кэша
curl -H "X-API-Key: your-admin-key" \
  http://localhost:8000/api/v1/admin/cache/stats

# Очистить кэш станций
curl -X POST -H "X-API-Key: your-admin-key" \
  http://localhost:8000/api/v1/admin/cache/clear-stations

# Создать API ключ
curl -X POST -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"New App","role":"user","rate_limit_requests":100}' \
  http://localhost:8000/api/v1/admin/api-keys

# Список API ключей
curl -H "X-API-Key: your-admin-key" \
  http://localhost:8000/api/v1/admin/api-keys

# Статистика API ключей
curl -H "X-API-Key: your-admin-key" \
  http://localhost:8000/api/v1/admin/api-keys/stats
```

## Отладка

```bash
# Проверить импорты
python -c "from app.main import app; print('OK')"

# Проверить конфиг
python -c "from app.core.config import settings; print(settings.database_url)"

# Проверить БД
alembic current

# Проверить Redis
redis-cli ping

# Проверить Docker
docker-compose ps
docker-compose logs app | tail -50
```

## Структура проекта

```
VoltWay/
├── app/
│   ├── api/              # API эндпоинты
│   │   ├── admin.py      # Admin API
│   │   ├── health.py     # Health checks
│   │   └── stations.py   # Станции
│   ├── core/             # Конфигурация
│   │   ├── config.py     # Настройки
│   │   └── dependencies.py  # DI
│   ├── models/           # SQLAlchemy модели
│   ├── repositories/     # Data access layer
│   │   ├── base.py       # Базовый репозиторий
│   │   └── station.py    # Репозиторий станций
│   ├── schemas/          # Pydantic схемы
│   ├── services/         # Бизнес-логика
│   │   ├── circuit_breaker.py  # Circuit breaker
│   │   ├── external_api.py     # Внешние API
│   │   └── batch_processor.py  # Batch processing
│   ├── utils/            # Утилиты
│   │   ├── retry.py      # Retry декораторы
│   │   ├── validators.py # Валидаторы
│   │   └── structured_logging.py  # Логирование
│   └── middleware/       # Middleware
├── tests/                # Тесты
├── migrations/           # Alembic миграции
└── docs/                 # Документация
```

## Горячие клавиши (если используете VS Code)

```
Ctrl+Shift+P  # Command palette
Ctrl+`        # Терминал
Ctrl+B        # Sidebar
F5            # Debug
Ctrl+Shift+F  # Поиск по проекту
```

## Troubleshooting

### Проблема: Порт занят
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Проблема: Миграции не применяются
```bash
alembic stamp head
alembic upgrade head
```

### Проблема: Redis недоступен
```bash
# Проверить
redis-cli ping

# Запустить
redis-server

# Docker
docker-compose up -d redis
```

### Проблема: Тесты падают
```bash
# Очистить кэш
pytest --cache-clear

# Пересоздать БД
rm test_voltway.db
pytest
```

---

**Полезные ссылки:**
- [README.md](README.md) - Основная документация
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Детали улучшений
- [ADVANCED_IMPROVEMENTS.md](ADVANCED_IMPROVEMENTS.md) - Продвинутые фичи
- [API Docs](http://localhost:8000/docs) - Swagger UI
