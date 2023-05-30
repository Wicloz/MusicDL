import asyncio
import websockets
import json
from secrets import choice
from pathlib import Path, PurePosixPath
from asyncio.subprocess import create_subprocess_exec, PIPE
from tempfile import TemporaryDirectory
from unidecode import unidecode
from os import listdir, getenv
from signal import signal, SIGTERM, SIGINT
import aiofiles
from pykakasi import kakasi
import re

from mutagen.easyid3 import EasyID3
EasyID3.RegisterTXXXKey('artists', 'ARTISTS')
EasyID3.RegisterTXXXKey('purl', 'purl')
EasyID3.RegisterTXXXKey('description', 'description')


class Downloader:
    def __init__(self, emitter):
        self.temp = Path(TemporaryDirectory(dir='public/downloads').name)
        self.web = PurePosixPath('/downloads/') / self.temp.name
        self.emit = emitter

    async def process(self, command, data):
        if command == 'download':
            await self._process_initial_download(**data)
        if command == 'edited':
            await self._process_edited_metadata(**data)
        if command == 'romanize':
            await self._romanize(**data)

    async def _romanize(self, text, number, script):
        if script == 'japanese':
            romanized = ' '.join(item['hepburn'] for item in kakasi().convert(text))
        else:
            romanized = unidecode(text)

        romanized = re.sub(r'[^ 0-9a-z]', '', re.sub(r'\s+', ' ', romanized.strip().lower()))
        await self.emit('romanized', {'text': romanized, 'number': number})

    @staticmethod
    def _extract(metadata, *keys):
        for key in keys:
            if key in metadata:
                return metadata[key]
        return ''

    async def _process_initial_download(self, url):
        await self.emit('progress', {'percentage': 0, 'message': 'Preparing'})

        process = await create_subprocess_exec(
            'yt-dlp', url,
            '--output', self.temp / 'ytdlp',
            '--progress',
            '--format', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--embed-thumbnail',
            '--write-thumbnail',
            '--write-info-json',
            stdout=PIPE,
        )

        percentage = 0
        digits = 0
        fraction = False

        while character := await process.stdout.read(1):
            pass

            if character in {b'0', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9'}:
                if not fraction:
                    percentage *= 10
                    percentage += int(character)
                else:
                    digits += 1
                    percentage += int(character) / (10 ** digits)

            elif character == b'.':
                fraction = True
            elif character == b'%':
                if percentage == 100:
                    break

                await self.emit('progress', {'percentage': percentage, 'message': 'Downloading'})
                percentage = 0
                digits = 0
                fraction = False
            else:
                percentage = 0
                digits = 0
                fraction = False

        await self.emit('progress', {'percentage': 100, 'message': 'Processing'})
        await process.wait()

        async with aiofiles.open(self.temp / 'ytdlp.info.json', 'rb') as fp:
            metadata = json.loads(await fp.read())

        thumbnail, = (item for item in listdir(self.temp)
                      if item != 'ytdlp.mp3' and item != 'ytdlp.info.json')

        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        mp3['date'] = self._extract(metadata, 'upload_date')
        mp3['description'] = self._extract(metadata, 'description')
        mp3['purl'] = self._extract(metadata, 'webpage_url')
        mp3.save()

        await self.emit('editor', {
            'title': self._extract(metadata, 'track', 'title'),
            'genre': self._extract(metadata, 'genre'),
            'album': self._extract(metadata, 'album'),
            'artist': self._extract(metadata, 'artist', 'creator', 'uploader', 'uploader_id'),
            'thumbnail': str(self.web / thumbnail),
            'uploader': self._extract(metadata, 'uploader'),
            'name': self._extract(metadata, 'title'),
        })

    async def _process_edited_metadata(self, title, album, genre, artists):
        artist_field = ' · '.join(artist['pretty'] for artist in artists)

        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        mp3['title'] = title
        mp3['album'] = album
        mp3['genre'] = genre
        mp3['artists'] = [artist['pretty'] for artist in artists]
        mp3['artist'] = artist_field
        mp3['artistsort'] = [artist['romanized'].lower() for artist in artists]
        mp3.save()

        await self.emit('finish', {
            'href': str(self.web / 'ytdlp.mp3'),
            'download': artist_field + ' - ' + title,
        })


async def handler(websocket):
    async def emitter(command, data):
        data['command'] = command
        await websocket.send(json.dumps(data))
        await asyncio.sleep(0)
    downloader = Downloader(emitter)

    while True:
        try:
            data = json.loads(await websocket.recv())
            command = data.pop('command')
            await downloader.process(command, data)
        except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
            break


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def signal_to_stop(_1, _2):
        stop.set_result(None)

    signal(SIGTERM, signal_to_stop)
    signal(SIGINT, signal_to_stop)

    port = int(getenv('PORT', '5555'))
    host = getenv('HOST', 'localhost')
    async with websockets.serve(handler, host, port):
        await stop


if __name__ == '__main__':
    asyncio.run(main())
