#!/bin/bash
# Простой скрипт для получения результатов задачи

# 1. Установите секретный ключ
export SHARED_KEY="dev-secret-key-for-testing-2024"

# 2. Укажите ID вашей задачи
JOB_ID="365a09ce-5416-49b5-8471-d6aad042761c"  # Замените на ваш ID

# 3. Генерируем подпись для пустого payload (GET запрос)
SIGNATURE=$(echo -n "" | openssl dgst -sha256 -hmac "$SHARED_KEY" -hex | cut -d' ' -f2)

echo "🔑 Подпись: $SIGNATURE"
echo ""

# 4. Получаем статус задачи
echo "📊 Статус задачи:"
curl -s -H "X-Signature: $SIGNATURE" \
  "https://bach-ai-info3819.replit.app/api/v1/batch-status/$JOB_ID" | python3 -m json.tool

echo ""
echo "📦 Полные результаты (первые 20 строк):"
curl -s -H "X-Signature: $SIGNATURE" \
  "https://bach-ai-info3819.replit.app/api/v1/jobs/$JOB_ID" | python3 -m json.tool | head -20