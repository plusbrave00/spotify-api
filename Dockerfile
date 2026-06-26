# YuviMods ADB Remote Controller Bot
# Dockerfile for Railway.app deployment

FROM python:3.10-slim

# Install Android ADB tools
RUN apt-get update && \
    apt-get install -y android-tools-adb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY bot.py .

# Start ADB server and run bot
CMD adb start-server && python bot.py
