# Как получить результаты выполненной задачи

## Если вы получили ответ:
```json
{
  "job_id": "365a09ce-5416-49b5-8471-d6aad042761c",
  "status": "completed"
}
```

## Получите полные результаты:

### Способ 1: С аутентификацией (полные данные)
```bash
export SHARED_KEY="dev-secret-key-for-testing-2024"

curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "https://bach-ai-info3819.replit.app/api/v1/jobs/365a09ce-5416-49b5-8471-d6aad042761c"
```

### Способ 2: Без аутентификации (только статус)
```bash
curl "https://bach-ai-info3819.replit.app/api/v1/jobs/365a09ce-5416-49b5-8471-d6aad042761c/status"
```

## Ответ содержит:
- **results**: массив всех обработанных лотов с описаниями
- **processed_lots**: количество успешно обработанных лотов
- **failed_lots**: количество неудачных лотов

## Python пример:
```python
import requests

job_id = "365a09ce-5416-49b5-8471-d6aad042761c"

# Получить результаты
headers = {"X-Signature": "31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426"}
response = requests.get(f"https://bach-ai-info3819.replit.app/api/v1/jobs/{job_id}", headers=headers)

results = response.json()
for lot in results["results"]:
    print(f"Лот {lot['lot_id']}: {lot['vision_result']}")
```

**Замените job_id на ваш актуальный ID задачи**