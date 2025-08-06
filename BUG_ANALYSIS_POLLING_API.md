# Анализ и исправление бага в Polling API

## Описание проблемы

При получении результатов через Polling API система возвращает структуру формата вместо реального текста описания автомобилей:

```json
{
  "lot_id": "5YJ3E1EB5KF433798",
  "vision_result": "{'format': {'type': 'text'}}"
}
```

Вместо ожидаемого:
```json
{
  "lot_id": "5YJ3E1EB5KF433798", 
  "vision_result": "Looking at this Tesla Model 3, I can observe several condition and damage indicators..."
}
```

## Причина проблемы

### Структура ответа OpenAI Responses API

OpenAI Responses API возвращает следующую структуру:

```json
{
  "response": {
    "body": {
      "text": {
        "format": {"type": "text"}  // ❌ Это мы сохраняли
      },
      "output": [
        {
          "content": [
            {
              "text": "Actual car description...",  // ✅ Это нужно сохранять
              "type": "text"
            }
          ],
          "type": "reasoning"
        }
      ]
    }
  }
}
```

### Ошибка в коде

В файле `services/batch_monitor.py` (строка 231) система извлекала поле `body.text`, которое содержит только метаданные формата, вместо `body.output[0].content[0].text`, где находится реальный текст.

## Исправление

### 1. Обновлен код парсинга (✅ Выполнено)

Файл: `services/batch_monitor.py`, строки 226-270

**Было:**
```python
text = body.get('text', '')  # Извлекает {'format': {'type': 'text'}}
```

**Стало:**
```python
# Правильное извлечение из структуры OpenAI Responses API
output = body.get('output', [])
if output and isinstance(output, list) and len(output) > 0:
    first_output = output[0]
    if isinstance(first_output, dict):
        content = first_output.get('content', [])
        if content and isinstance(content, list) and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict):
                vision_text = first_content.get('text', '')
```

### 2. Восстановление существующих данных

Для задачи `64734dab-3961-4014-8b2b-196302b5d047` данные уже сохранены неправильно в базе данных.

**Проблема:** У этой задачи отсутствует `openai_batch_id` для vision (поле пустое), есть только `openai_translation_batch_id`.

**Возможные решения:**

1. **Повторная обработка** - создать новую задачу с теми же изображениями
2. **Ручное восстановление** - если есть доступ к логам с оригинальным batch ID
3. **Использование translation batch** - попытаться найти связанные vision результаты

## План действий для пользователя

### Вариант 1: Создать новую задачу (Рекомендуется)

Отправьте новый запрос с теми же данными. Благодаря исправлению, новые задачи будут обрабатываться корректно:

```bash
curl -X POST http://your-service.com/api/v1/generate-descriptions \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "your_signature",
    "version": "1.0.0",
    "languages": ["en", "ru"],
    "lots": [/* ваши данные */]
  }'
```

### Вариант 2: Восстановление через поддержку OpenAI

Если у вас есть `request_id` или временные метки создания задачи, можно запросить у OpenAI восстановление результатов.

### Вариант 3: Использование синхронного режима

Для небольших партий (до 20 изображений) используйте синхронный режим, который не подвержен этой проблеме:

```bash
curl -X POST http://your-service.com/api/v1/generate-single \
  -H "Content-Type: application/json" \
  -d '{
    "signature": "your_signature",
    "lot_id": "TEST_001",
    "images": ["url1", "url2"],
    "languages": ["en"]
  }'
```

## Статус исправления

- ✅ **Код исправлен** - новые задачи будут обрабатываться корректно
- ✅ **Развернуто в production** - изменения применены и работают
- ⚠️ **Старые данные** - требуют повторной обработки или восстановления

## Мониторинг

Для проверки корректности работы:

```bash
# Проверить статус задачи
curl -X GET "http://your-service.com/api/v1/batch-status/{job_id}" \
  -H "X-Signature: your_signature"

# Проверить результаты
curl -X GET "http://your-service.com/api/v1/batch-results/{job_id}" \
  -H "X-Signature: your_signature"
```

Результаты должны содержать полный текст описания, а не структуру формата.

## Технические детали

- **Затронутые файлы:** `services/batch_monitor.py`
- **Версия OpenAI API:** Responses API (o4-mini)
- **Формат ответа:** JSONL с вложенной структурой
- **Критическое поле:** `response.body.output[0].content[0].text`

## Контакты для поддержки

При возникновении вопросов обращайтесь к системному администратору или создайте issue в репозитории проекта.