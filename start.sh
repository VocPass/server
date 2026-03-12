#!/bin/bash

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

APP_ENV="${APP_ENV:-development}"
APP_PORT="${APP_PORT:-8000}"

if [ "$APP_ENV" = "production" ]; then
    echo "🚀 Run main(Port: $APP_PORT)..."
    fastapi run --port "$APP_PORT"
else
    echo "🛠️  Run dev (Port: $APP_PORT)..."
    fastapi dev --port "$APP_PORT" --host "0.0.0.0"
fi