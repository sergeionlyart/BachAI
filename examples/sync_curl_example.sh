#!/bin/bash

# Пример curl запроса для синхронного анализа одного автомобиля
# Generation Service - Synchronous Mode

# Настройки
BASE_URL="https://bach-ai-info3819.replit.app"
SHARED_KEY="dev-secret-key-for-testing-2024"

# Данные для анализа
LOT_ID="sync-demo-$(date +%s)"
ADDITIONAL_INFO="2020 Tesla Model 3, minor front damage, parking collision"
IMAGE_URL1="https://images.unsplash.com/photo-1549399811-9b0c893bd7c1?w=800"
IMAGE_URL2="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"

# JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "version": "1.0.0",
  "languages": ["en", "ru"],
  "lots": [
    {
      "lot_id": "$LOT_ID",
      "additional_info": "$ADDITIONAL_INFO",
      "images": [
        {"url": "$IMAGE_URL1"},
        {"url": "$IMAGE_URL2"}
      ]
    }
  ]
}
EOF
)

# Генерация HMAC подписи (для Linux/Mac с Python)
LOTS_JSON=$(echo "$JSON_PAYLOAD" | python3 -c "
import json
import sys
import hmac
import hashlib

data = json.load(sys.stdin)
lots_normalized = json.dumps(data['lots'], separators=(',', ':'), sort_keys=True)
signature = hmac.new(
    '$SHARED_KEY'.encode(),
    lots_normalized.encode(),
    hashlib.sha256
).hexdigest()
print('sha256=' + signature)
")

# Добавляем подпись в payload
FINAL_PAYLOAD=$(echo "$JSON_PAYLOAD" | python3 -c "
import json
import sys
data = json.load(sys.stdin)
data['signature'] = '$LOTS_JSON'
print(json.dumps(data, separators=(',', ':')))
")

echo "🚗 Отправка синхронного запроса..."
echo "📝 Lot ID: $LOT_ID"
echo "🔐 Signature: $LOTS_JSON"
echo ""

# Выполнение curl запроса
curl -X POST "$BASE_URL/api/v1/generate-descriptions" \
  -H "Content-Type: application/json" \
  -H "User-Agent: CurlExample/1.0" \
  -d "$FINAL_PAYLOAD" \
  --max-time 300 \
  --show-error \
  --silent \
  | python3 -m json.tool

echo ""
echo "✅ Запрос завершен"