import asyncio
import websockets
import json
from secrets import choice
from pathlib import Path, PurePosixPath
from subprocess import Popen, PIPE
from mutagen.easyid3 import EasyID3
from tempfile import TemporaryDirectory


class Connection:
    def __init__(self, websocket):
        self.socket = websocket
        self.temp = Path(TemporaryDirectory(dir='public/downloads').name)
        self.web = PurePosixPath('/downloads/') / self.temp.name

    async def message(self, content):
        parsed = json.loads(content)
        if parsed['command'] == 'download':
            await self.process_initial_download(parsed['url'])
        if parsed['command'] == 'edited':
            await self.process_edited_metadata(parsed['title'], parsed['album'], parsed['genre'])

    async def send(self, command, data):
        data['command'] = command
        await self.socket.send(json.dumps(data))

    async def process_initial_download(self, url):
        process = Popen([
            'yt-dlp', url,
            '--newline',
            '--output', self.temp / 'ytdlp',
            '--format', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--embed-thumbnail',
            '--embed-metadata',
            '--write-thumbnail',
        ], stdout=PIPE)

        percentage = 0
        digits = 0
        fraction = False

        for line in process.stdout:
            if not line:
                break

            for character in line.decode('UTF8'):
                if character in {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}:
                    percentage += int(character) * \
                        (0.1 if fraction else 10) ** digits
                    digits += 1
                elif character == '.':
                    fraction = True
                    digits = 1
                elif character == '%':
                    await self.send('progress', {'percentage': percentage})
                    percentage = 0
                    digits = 0
                    fraction = False
                else:
                    percentage = 0
                    digits = 0
                    fraction = False

        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        await self.send('editor', {
            'thumbnail': str(self.web / 'ytdlp.webp'),
            'title': mp3.get('title', ''),
            'genre': mp3.get('genre', ''),
            'album': mp3.get('album', ''),
        })

    async def process_edited_metadata(self, title, album, genre):
        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        mp3['title'] = title
        mp3['album'] = album
        mp3['genre'] = genre
        mp3.save()
        await self.send('progress', {'percentage': 100})

        await self.send('finish', {
            'href': str(self.web / 'ytdlp.mp3'),
            'download': title,
        })


async def handler(websocket):
    connection = Connection(websocket)
    while True:
        await connection.message(await websocket.recv())


async def main():
    async with websockets.serve(handler, '', 5555):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
