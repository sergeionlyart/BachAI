# 🚀 Краткая инструкция для клиента

## Получение результатов задачи за 3 шага

### Шаг 1: Установите секретный ключ
```bash
export SHARED_KEY="dev-secret-key-for-testing-2024"
```

### Шаг 2: Получите статус (замените YOUR_JOB_ID на ваш ID)
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "https://bach-ai-info3819.replit.app/api/v1/batch-status/YOUR_JOB_ID"
```

### Шаг 3: Получите полные результаты
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "https://bach-ai-info3819.replit.app/api/v1/jobs/YOUR_JOB_ID"
```

---

## Альтернатива: Простой способ БЕЗ подписи

Для простого статуса без аутентификации:
```bash
curl "https://bach-ai-info3819.replit.app/api/v1/jobs/YOUR_JOB_ID/status"
```

---

## Python пример
```python
import requests

# С подписью
headers = {"X-Signature": "31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426"}
response = requests.get(
    "https://bach-ai-info3819.replit.app/api/v1/batch-status/YOUR_JOB_ID",
    headers=headers
)
print(response.json())

# Без подписи (только статус)
response = requests.get("https://bach-ai-info3819.replit.app/api/v1/jobs/YOUR_JOB_ID/status")
print(response.json())
```

**Примечание:** Подпись `31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426` уже рассчитана для GET запросов с ключом `dev-secret-key-for-testing-2024`