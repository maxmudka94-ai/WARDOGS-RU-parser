# twitch-parser-bot (Python) — Twitch-анонсы и перевод Discord-сообщений

Бот проверяет `TWITCH_CHANNELS` каждые `TWITCH_POLL_SECONDS` и пишет в `ANNOUNCE_CHANNEL_ID`, когда стрим переходит offline→live. `TWITCH_CHANNELS` — это логины стримеров без `@`. Также он умеет переводить сообщения вручную и автоматически через Gemini.

## Запуск
1. `cp .env.example .env` и заполни `DISCORD_TOKEN`, `TWITCH_CLIENT_ID/SECRET`, `TWITCH_CHANNELS`, `ANNOUNCE_CHANNEL_ID`.
2. `pip install -r requirements.txt`.
3. `python bot.py`.

## Перевод

1. Создай новый ключ Gemini в [Google AI Studio](https://aistudio.google.com/apikey) и укажи его в `GEMINI_API_KEY`. Ключи вида `AQ...` не являются обычными Gemini API keys и приводят к ошибке `401`.
2. Укажи модель, например `gemini-2.5-flash`.
3. `TRANSLATE_CHANNELS` — ID каналов через запятую для автоперевода.
4. Для ручного перевода используй контекстное меню сообщения: **ПКМ по сообщению → Apps → Перевести**.

Команды синхронизируются в `GUILD_ID`, поэтому появляются сразу. Если `GUILD_ID` не указан, используется глобальная синхронизация Discord, которая может занимать до часа.

Для автоперевода включи **Message Content Intent** для бота в Discord Developer Portal. Сообщения от ботов пропускаются, чтобы не создавать циклы.

## Twitch API
https://dev.twitch.tv/console/apps → Create app → Client ID + Client Secret. Без них работает GQL-фолбэк.

## Docker
```bash
docker build -t twitch-parser-bot .
docker run -d --env-file .env --name twitch-parser-bot twitch-parser-bot
```
