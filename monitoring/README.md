# VoltWay Monitoring

Мониторинг приложения с использованием Prometheus и Grafana.

## Быстрый старт

### Запуск стека мониторинга

```bash
cd monitoring
docker-compose up -d
```

### Доступ к сервисам

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Логин: `admin`
  - Пароль: `voltway123`

## Метрики

Приложение экспортирует метрики Prometheus по адресу `/metrics`:

- `request_count_total` - общее количество запросов
- `request_duration` - длительность обработки запросов
- `errors_total` - количество ошибок
- `websocket_connections` - активные WebSocket соединения

## Настройка алертов

1. Откройте Grafana
2. Перейдите в Alerting → Notification channels
3. Добавьте канал (email, Slack, Telegram)
4. Создайте правила алертов в Alerting → Alert rules

## Dashboards

Предустановленный dashboard включает:
- Request Rate по эндпоинтам
- Request Duration (95th percentile)
- Error Rate по типам ошибок
- Active WebSocket connections

## Остановка

```bash
cd monitoring
docker-compose down
```

Для удаления данных:
```bash
docker-compose down -v
```
