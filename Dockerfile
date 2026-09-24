FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py config.py translator.py twitch_api.py ./
COPY cogs ./cogs
COPY .env.example ./
CMD ["python", "bot.py"]
