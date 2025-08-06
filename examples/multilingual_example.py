#!/usr/bin/env python3
"""
Пример запроса с множественными языками
"""
import hmac
import hashlib
import json

# Данные лота
lots_data = [
    {
        "lot_id": "multilingual-demo",
        "additional_info": "2019 Tesla Model 3, good condition",
        "images": [
            {"url": "https://auto.dev/images/forsale/2025/08/02/11/20/2019_tesla_model_3-pic-5280294760125443694-1024x768.jpeg"}
        ]
    }
]

# МНОЖЕСТВЕННЫЕ ЯЗЫКИ (без ограничений!)
languages = [
    "en",    # английский (базовый)
    "ru",    # русский
    "de",    # немецкий  
    "fr",    # французский
    "es",    # испанский
    "it",    # итальянский
    "pt",    # португальский
    "zh",    # китайский
    "ja",    # японский
    "ko"     # корейский
]

shared_key = "dev-secret-key-for-testing-2024"

# Генерация подписи
normalized = json.dumps(lots_data, separators=(',', ':'), sort_keys=True)
signature = hmac.new(
    shared_key.encode(),
    normalized.encode(),
    hashlib.sha256
).hexdigest()

payload = {
    "signature": signature,
    "version": "1.0.0",
    "languages": languages,  # 10 языков!
    "lots": lots_data
}

print(f"🌍 Запрос на {len(languages)} языков:")
for i, lang in enumerate(languages, 1):
    print(f"  {i:2d}. {lang}")

print(f"\n⚠️  При >5 языках система выдаст предупреждение о возможных задержках")
print(f"⏱️  Лимит времени: 45 секунд на все переводы")
print(f"🔄 Если время истечет, остальные языки получат английский fallback")

print("\n✅ Curl команда:")
print(f"""curl -X POST "https://bach-ai-info3819.replit.app/api/v1/generate-descriptions" \\
  -H "Content-Type: application/json" \\
  -H "User-Agent: MultilingualDemo/1.0" \\
  -d '{json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}' \\
  --max-time 300""")