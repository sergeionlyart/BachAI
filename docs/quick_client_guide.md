# Быстрая инструкция: Как получить результаты задачи

## 1. Установите секретный ключ
```bash
export SHARED_KEY="dev-secret-key-for-testing-2024"
```

## 2. Сгенерируйте подпись
```bash
echo -n "" | openssl dgst -sha256 -hmac "$SHARED_KEY" -hex | cut -d' ' -f2
```
Результат: `31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426`

## 3. Получите статус задачи
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "https://bach-ai-info3819.replit.app/api/v1/batch-status/YOUR_JOB_ID"
```

## 4. Получите полные результаты
```bash
curl -H "X-Signature: 31372e0cc162d8177cd01417440ae6ed9e8c74894765825b64d335070b80c426" \
  "https://bach-ai-info3819.replit.app/api/v1/jobs/YOUR_JOB_ID"
```

## Альтернатива: Без подписи (только статус)
```bash
curl "https://bach-ai-info3819.replit.app/api/v1/jobs/YOUR_JOB_ID/status"
```

**Замените YOUR_JOB_ID на ваш ID задачи**