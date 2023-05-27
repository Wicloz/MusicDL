rsync --recursive --delete ./built/ ./public/
uvicorn --host "$HOST" --port "$PORT" server:app
