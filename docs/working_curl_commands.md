# Рабочие команды curl

## ✅ Правильная команда (одной строкой):
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" "http://localhost:5000/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c"
```

## ❌ Проблема с переносом строки:
Когда команда разбивается на несколько строк без символа `\`, curl интерпретирует это неправильно.

## 🔧 Альтернативные варианты:

### С переносом строки (правильно):
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "http://localhost:5000/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c"
```

### Простая версия без аутентификации:
```bash
curl "http://localhost:5000/api/v1/jobs/365a09ce-5416-49b5-8471-d6aad042761c/status"
```

### С форматированием JSON:
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "http://localhost:5000/api/v1/batch-status/365a09ce-5416-49b5-8471-d6aad042761c" | jq
```

## 🎯 Тестирование других Job ID:
```bash
# Замените YOUR_JOB_ID на ваш ID задачи
curl -H "X-Signature: GENERATED_SIGNATURE" \
  "http://localhost:5000/api/v1/batch-status/YOUR_JOB_ID"
```

## 🛠️ Генерация новой подписи:
```bash
python3 tools/signature_helper.py "/api/v1/batch-status/YOUR_JOB_ID"
```