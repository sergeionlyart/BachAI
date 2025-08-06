# Руководство по использованию веб-хуков

## Обзор

Веб-хуки позволяют получать автоматические уведомления о завершении обработки заданий без необходимости постоянно опрашивать API. Когда ваше задание завершается, система автоматически отправит HTTP POST запрос на указанный вами URL.

## Настройка веб-хука

### 1. Создание задания с веб-хуком

При отправке задания на обработку, добавьте параметр `webhook_url` в ваш запрос:

```bash
curl -X POST https://your-service.com/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "your_hmac_signature",
    "version": "1.0.0", 
    "languages": ["en", "ru"],
    "webhook_url": "https://your-domain.com/webhook-handler",
    "lots": [
      {
        "lot_id": "car_001",
        "images": [
          "https://example.com/car1_front.jpg",
          "https://example.com/car1_back.jpg"
        ]
      }
    ]
  }'
```

### 2. Требования к веб-хук endpoint'у

Ваш веб-хук endpoint должен:
- Принимать HTTP POST запросы
- Возвращать статус код 200-299 для успешной обработки
- Отвечать в течение 30 секунд
- Использовать HTTPS (рекомендуется)

## Формат уведомлений

### Структура webhook payload

Когда задание завершается, на ваш URL отправляется POST запрос с JSON payload:

```json
{
  "job_id": "365a09ce-5416-49b5-8471-d6aad042761c",
  "status": "completed",
  "timestamp": "2025-08-06T11:30:00Z",
  "total_lots": 10,
  "completed_lots": 10,
  "failed_lots": 0,
  "webhook_url": "https://your-domain.com/webhook-handler",
  "results_available": true
}
```

### Поля уведомления

| Поле | Тип | Описание |
|------|-----|----------|
| `job_id` | string | Уникальный ID задания |
| `status` | string | Статус: "completed", "failed", "partially_completed" |
| `timestamp` | string | Время завершения в ISO 8601 |
| `total_lots` | number | Общее количество лотов в задании |
| `completed_lots` | number | Количество успешно обработанных лотов |
| `failed_lots` | number | Количество лотов с ошибками |
| `webhook_url` | string | URL веб-хука (для подтверждения) |
| `results_available` | boolean | Доступны ли результаты для получения |

### HTTP заголовки

Каждый webhook запрос содержит следующие заголовки:

```
Content-Type: application/json
User-Agent: Generation-Service/1.0
X-Signature: hmac_signature_here
```

## Проверка подписи

### Важно для безопасности

Всегда проверяйте подпись `X-Signature` для защиты от поддельных запросов.

### Python пример

```python
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
SHARED_SECRET = "your-shared-secret-key"

@app.route('/webhook-handler', methods=['POST'])
def handle_webhook():
    # Получаем данные
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Signature')
    
    # Проверяем подпись
    expected_signature = hmac.new(
        SHARED_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({'error': 'Invalid signature'}), 403
    
    # Обрабатываем webhook
    data = request.get_json()
    job_id = data['job_id']
    status = data['status']
    
    print(f"Job {job_id} completed with status: {status}")
    
    # Получаем результаты если нужно
    if data.get('results_available'):
        fetch_results(job_id)
    
    return jsonify({'success': True}), 200

def fetch_results(job_id):
    # Код для получения результатов через polling API
    pass
```

### Node.js пример

```javascript
const express = require('express');
const crypto = require('crypto');
const app = express();

const SHARED_SECRET = 'your-shared-secret-key';

app.use(express.raw({type: 'application/json'}));

app.post('/webhook-handler', (req, res) => {
    const payload = req.body.toString();
    const signature = req.headers['x-signature'];
    
    // Проверяем подпись
    const expectedSignature = crypto
        .createHmac('sha256', SHARED_SECRET)
        .update(payload)
        .digest('hex');
    
    if (signature !== expectedSignature) {
        return res.status(403).json({error: 'Invalid signature'});
    }
    
    // Обрабатываем webhook
    const data = JSON.parse(payload);
    console.log(`Job ${data.job_id} completed:`, data);
    
    // Получаем результаты если нужно
    if (data.results_available) {
        fetchResults(data.job_id);
    }
    
    res.json({success: true});
});

function fetchResults(jobId) {
    // Код для получения результатов
}

app.listen(3000, () => {
    console.log('Webhook server running on port 3000');
});
```

## Получение результатов

После получения уведомления используйте polling API для получения результатов:

```bash
# Получение статуса задания
curl -X GET "https://your-service.com/api/v1/jobs/{job_id}/status"

# Получение результатов
curl -X GET "https://your-service.com/api/v1/jobs/{job_id}/results"
```

## Обработка ошибок и повторные попытки

### Система повторов

Если ваш endpoint недоступен, система автоматически повторит доставку:

- **Попытки**: До 5 попыток
- **Интервалы**: 1 мин, 2 мин, 4 мин, 8 мин, 16 мин
- **Timeout**: 30 секунд на запрос

### Коды ответа

| Код | Результат | Действие системы |
|-----|-----------|------------------|
| 200-299 | Успех | Доставка завершена |
| 400-499 | Ошибка клиента | Повтор не выполняется |
| 500-599 | Ошибка сервера | Повтор через интервал |
| Timeout | Таймаут | Повтор через интервал |

### Пример обработки ошибок

```python
@app.route('/webhook-handler', methods=['POST'])
def handle_webhook():
    try:
        # Проверка подписи
        if not verify_signature(request):
            return jsonify({'error': 'Invalid signature'}), 403
        
        # Обработка данных
        data = request.get_json()
        process_webhook(data)
        
        return jsonify({'success': True}), 200
        
    except ValidationError as e:
        # Ошибка валидации - не повторять
        return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        # Серверная ошибка - система повторит
        app.logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Internal error'}), 500
```

## Тестирование

### Локальное тестирование с ngrok

Для тестирования на локальной машине используйте ngrok:

```bash
# Установка ngrok
npm install -g ngrok

# Запуск туннеля
ngrok http 3000

# Используйте предоставленный HTTPS URL как webhook_url
```

### Тестовые запросы

Создайте тестовое задание для проверки веб-хука:

```python
import requests
import hmac
import hashlib
import json

def create_test_job():
    data = {
        "version": "1.0.0",
        "languages": ["en"],
        "webhook_url": "https://your-ngrok-url.ngrok.io/webhook-handler",
        "lots": [{
            "lot_id": "test_001",
            "images": ["https://example.com/test.jpg"]
        }]
    }
    
    # Создание подписи
    payload = json.dumps(data['lots'])
    signature = hmac.new(
        b'your-shared-secret',
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    data['signature'] = signature
    
    response = requests.post(
        'https://your-service.com/api/v1/generate-descriptions',
        json=data
    )
    
    return response.json()
```

## Мониторинг веб-хуков

### API для мониторинга

Проверяйте статус доставки веб-хуков:

```bash
# Метрики доставки
curl "https://your-service.com/api/v1/webhook-metrics?hours=24"

# Статус системы
curl "https://your-service.com/api/v1/webhook-health"

# Неудачные доставки
curl "https://your-service.com/api/v1/webhook-failures"
```

### Рекомендации по мониторингу

1. **Логирование**: Записывайте все входящие веб-хуки
2. **Алерты**: Настройте уведомления при сбоях
3. **Метрики**: Отслеживайте время обработки
4. **Резервный план**: Используйте polling API как fallback

## Лучшие практики

### Безопасность

- ✅ Всегда проверяйте подпись `X-Signature`
- ✅ Используйте HTTPS для webhook endpoint'а
- ✅ Не логируйте секретные ключи
- ✅ Ограничьте доступ к webhook endpoint'у

### Надежность

- ✅ Возвращайте статус 200 быстро (в течение 5 секунд)
- ✅ Обрабатывайте веб-хук асинхронно если нужно время
- ✅ Идемпотентность: обрабатывайте дубликаты корректно
- ✅ Имейте fallback через polling API

### Производительность

- ✅ Используйте очереди для тяжелой обработки
- ✅ Кэширование для часто запрашиваемых данных
- ✅ Мониторинг времени ответа
- ✅ Graceful shutdown при обновлениях

## Устранение неполадок

### Веб-хук не приходит

1. Проверьте URL webhook'а на доступность
2. Убедитесь что endpoint возвращает 200
3. Проверьте логи на наличие ошибок
4. Используйте polling API как fallback

### Ошибки подписи

1. Проверьте правильность SHARED_KEY
2. Убедитесь в корректном вычислении HMAC-SHA256
3. Используйте raw body для подписи
4. Сравнивайте подписи через hmac.compare_digest()

### Таймауты

1. Уменьшите время обработки в endpoint'е
2. Используйте асинхронную обработку
3. Верните 200 сразу, обработку делайте в background
4. Проверьте сетевую связность

## Примеры интеграции

### Интеграция с базой данных

```python
import sqlite3
from datetime import datetime

def save_webhook_result(data):
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE jobs 
        SET status = ?, completed_at = ?, 
            completed_lots = ?, failed_lots = ?
        WHERE job_id = ?
    ''', (
        data['status'],
        datetime.utcnow(),
        data['completed_lots'],
        data['failed_lots'],
        data['job_id']
    ))
    
    conn.commit()
    conn.close()
```

### Интеграция с очередями

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def queue_result_processing(data):
    # Добавляем задачу в очередь для обработки
    redis_client.lpush('result_queue', json.dumps(data))
    
@app.route('/webhook-handler', methods=['POST'])
def handle_webhook():
    if verify_signature(request):
        data = request.get_json()
        
        # Быстро сохраняем и ставим в очередь
        queue_result_processing(data)
        
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Invalid signature'}), 403
```

## Поддержка

Если у вас возникли вопросы по настройке веб-хуков:

1. Проверьте логи вашего приложения
2. Используйте API мониторинга для диагностики
3. Обратитесь в техническую поддержку с деталями проблемы
4. Приложите примеры запросов и ответов

---

**Важно**: Всегда тестируйте веб-хуки в среде разработки перед внедрением в продакшн.