# 🚀 Быстрый старт - Примеры запросов

## Curl команды для тестирования

### 1. Синхронный запрос (Python генерация подписи)

```bash
# Генерация подписи
python3 -c "
import hmac, hashlib, json
lots = [{'lot_id': 'test-123', 'additional_info': '2019 Tesla Model 3', 'images': [{'url': 'https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg'}]}]
key = 'dev-secret-key-for-testing-2024'
normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
signature = hmac.new(key.encode(), normalized.encode(), hashlib.sha256).hexdigest()
print(f'Подпись: {signature}')
"

# Синхронный запрос с полученной подписью
curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: QuickTest/1.0" \
  -d '{"signature":"YOUR_SIGNATURE_HERE","version":"1.0.0","languages":["en","ru"],"lots":[{"lot_id":"test-123","additional_info":"2019 Tesla Model 3","images":[{"url":"https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg"}]}]}' \
  --max-time 300
```

### 2. Пакетный запрос

```bash
# Создание пакетного задания
curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -d '{"signature":"BATCH_SIGNATURE","version":"1.0.0","languages":["en","ru"],"lots":[{"lot_id":"car-001","additional_info":"2020 BMW X3","images":[{"url":"https://example.com/bmw1.jpg"}]},{"lot_id":"car-002","additional_info":"2021 Audi A4","images":[{"url":"https://example.com/audi1.jpg"}]}]}' \
  --max-time 30
```

### 3. Проверка статуса

```bash
# Получение статуса задания
curl "https://bach-ai-info3819.replit.app/api/v1/batch-status/YOUR_JOB_ID"
```

### 4. Получение результатов

```bash
# Получение готовых результатов
curl "https://bach-ai-info3819.replit.app/api/v1/batch-results/YOUR_JOB_ID"
```

---

## Python - Полный рабочий пример

```python
#!/usr/bin/env python3
"""
Полный пример интеграции с Generation Service
"""
import requests
import hmac
import hashlib
import json
import time

# Конфигурация
BASE_URL = "https://bach-ai-info3819.replit.app"
SHARED_KEY = "dev-secret-key-for-testing-2024"  # Ваш реальный ключ

def generate_signature(lots_data):
    """Генерация HMAC подписи"""
    normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
    return hmac.new(
        SHARED_KEY.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()

def sync_example():
    """Пример синхронной обработки"""
    print("🚗 Синхронная обработка одного автомобиля...")
    
    lots = [{
        "lot_id": "sync-demo-001",
        "additional_info": "2019 Tesla Model 3, clean title",
        "images": [{
            "url": "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg"
        }]
    }]
    
    payload = {
        "signature": generate_signature(lots),
        "version": "1.0.0",
        "languages": ["en", "ru"],
        "lots": lots
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/generate-descriptions",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            descriptions = result['lots'][0]['descriptions']
            print(f"✅ Получено {len(descriptions)} описаний:")
            for desc in descriptions:
                print(f"  {desc['language']}: {desc['damages'][:100]}...")
            return result
        else:
            print(f"❌ Ошибка {response.status_code}: {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def async_example():
    """Пример асинхронной обработки с polling"""
    print("\n🔄 Асинхронная обработка нескольких автомобилей...")
    
    lots = [
        {
            "lot_id": "async-demo-001",
            "additional_info": "2020 BMW X5, fleet vehicle",
            "images": [{"url": "https://example.com/bmw-x5-1.jpg"}]
        },
        {
            "lot_id": "async-demo-002", 
            "additional_info": "2021 Mercedes C-Class, lease return",
            "images": [{"url": "https://example.com/mercedes-c-1.jpg"}]
        }
    ]
    
    payload = {
        "signature": generate_signature(lots),
        "version": "1.0.0",
        "languages": ["en", "ru", "de"],
        "lots": lots
    }
    
    try:
        # Создание задания
        response = requests.post(
            f"{BASE_URL}/api/v1/generate-descriptions",
            json=payload,
            timeout=30
        )
        
        if response.status_code != 201:
            print(f"❌ Ошибка создания задания: {response.text}")
            return None
            
        job_data = response.json()
        job_id = job_data['job_id']
        print(f"📋 Задание создано: {job_id}")
        
        # Polling статуса
        max_wait = 600  # 10 минут
        poll_interval = 10  # 10 секунд
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = requests.get(f"{BASE_URL}/api/v1/batch-status/{job_id}")
            
            if status_response.status_code != 200:
                print(f"❌ Ошибка проверки статуса: {status_response.text}")
                return None
                
            status = status_response.json()
            progress = status['progress']
            
            print(f"⏳ Статус: {status['status']} - {progress['completion_percentage']:.1f}% ({progress['processed_lots']}/{progress['total_lots']})")
            
            if status['status'] == 'completed':
                # Получение результатов
                results_response = requests.get(f"{BASE_URL}/api/v1/batch-results/{job_id}")
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    print(f"✅ Обработка завершена! Получено {len(results['results']['lots'])} автомобилей")
                    return results
                else:
                    print(f"❌ Ошибка получения результатов: {results_response.text}")
                    return None
                    
            elif status['status'] in ['failed', 'cancelled']:
                print(f"❌ Задание {status['status']}: {status.get('error_message', 'Unknown error')}")
                return None
                
            time.sleep(poll_interval)
        
        print(f"⏰ Превышено время ожидания ({max_wait} секунд)")
        return None
        
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def test_image_validation():
    """Тестирование валидации изображений"""
    print("\n🔍 Тестирование валидации изображений...")
    
    test_urls = [
        "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg",
        "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-8256033307301130576-1024x768.jpeg",
        "https://invalid-url.example.com/nonexistent.jpg"
    ]
    
    payload = {"urls": test_urls}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/test-image-validation",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Валидных изображений: {len(result['valid_urls'])}")
            print(f"❌ Недоступных изображений: {len(result['unreachable_urls'])}")
            print(f"📊 Порог пройден: {result['threshold_met']}")
            return result
        else:
            print(f"❌ Ошибка валидации: {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

if __name__ == "__main__":
    print("🔧 Generation Service - Примеры интеграции\n")
    
    # Тестирование валидации изображений
    test_image_validation()
    
    # Синхронный режим
    sync_result = sync_example()
    
    # Асинхронный режим (раскомментируйте для тестирования)
    # async_result = async_example()
    
    print("\n✨ Тестирование завершено!")
```

---

## JavaScript/Node.js пример

```javascript
const axios = require('axios');
const crypto = require('crypto');

// Конфигурация
const BASE_URL = 'https://bach-ai-info3819.replit.app';
const SHARED_KEY = 'dev-secret-key-for-testing-2024';

function generateSignature(lotsData) {
    const normalized = JSON.stringify(lotsData, Object.keys(lotsData).sort());
    return crypto.createHmac('sha256', SHARED_KEY).update(normalized).digest('hex');
}

async function syncExample() {
    console.log('🚗 Синхронная обработка...');
    
    const lots = [{
        lot_id: 'js-sync-001',
        additional_info: '2019 Tesla Model 3',
        images: [{
            url: 'https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg'
        }]
    }];
    
    const payload = {
        signature: generateSignature(lots),
        version: '1.0.0',
        languages: ['en', 'ru'],
        lots
    };
    
    try {
        const response = await axios.post(
            `${BASE_URL}/api/v1/generate-descriptions`,
            payload,
            { timeout: 300000 }
        );
        
        console.log(`✅ Получено ${response.data.lots[0].descriptions.length} описаний`);
        return response.data;
        
    } catch (error) {
        console.error('❌ Ошибка:', error.response?.data || error.message);
        return null;
    }
}

// Запуск
syncExample();
```

---

## Быстрые команды для разработчиков

### Проверка работоспособности службы

```bash
curl -s "https://bach-ai-info3819.replit.app/health" | jq
```

### Генерация подписи в командной строке

```bash
# Linux/Mac с Python
python3 -c "
import hmac, hashlib, json, sys
lots = [{'lot_id': sys.argv[1], 'additional_info': sys.argv[2], 'images': [{'url': sys.argv[3]}]}]
key = 'dev-secret-key-for-testing-2024'
normalized = json.dumps(lots, separators=(',', ':'), sort_keys=True)
signature = hmac.new(key.encode(), normalized.encode(), hashlib.sha256).hexdigest()
print(signature)
" "car-123" "Test car" "https://example.com/car.jpg"
```

### Быстрое тестирование

```bash
# 1-минутный тест
./examples/quick_test.sh "car-123" "https://example.com/test.jpg" "en,ru"
```

---

## Готовые шаблоны интеграции

### PHP cURL

```php
<?php
function generateSignature($lotsData, $sharedKey) {
    $normalized = json_encode($lotsData, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    return hash_hmac('sha256', $normalized, $sharedKey);
}

$lots = [
    [
        'lot_id' => 'php-demo-001',
        'additional_info' => '2020 Honda Civic',
        'images' => [['url' => 'https://example.com/honda.jpg']]
    ]
];

$payload = [
    'signature' => generateSignature($lots, 'your-shared-key'),
    'version' => '1.0.0',
    'languages' => ['en', 'es'],
    'lots' => $lots
];

$ch = curl_init('https://bach-ai-info3819.replit.app/api/v1/generate-descriptions');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 300);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200) {
    $result = json_decode($response, true);
    echo "Успешно: " . count($result['lots'][0]['descriptions']) . " описаний\n";
} else {
    echo "Ошибка $httpCode: $response\n";
}
?>
```

Все примеры готовы к копированию и использованию в продакшн-системах.