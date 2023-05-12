rsync --recursive --delete ./built/ ./public/
mkdir ./public/downloads/
python3 -u server.py
