rsync --recursive --delete ./built/ ./public/
gunicorn server:app
