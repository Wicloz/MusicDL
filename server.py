import asyncio
import websockets
import json
from secrets import choice
from pathlib import Path, PurePosixPath
from subprocess import Popen, PIPE, run
from tempfile import TemporaryDirectory
from unidecode import unidecode
from os import listdir, getenv
from signal import signal, SIGTERM, SIGINT

from mutagen.easyid3 import EasyID3
EasyID3.RegisterTXXXKey('artists', 'ARTISTS')


class Downloader:
    def __init__(self):
        self.temp = Path(TemporaryDirectory(dir='public/downloads').name)
        self.web = PurePosixPath('/downloads/') / self.temp.name

    def process(self, command, data):
        if command == 'download':
            return self._process_initial_download(**data)
        if command == 'edited':
            return self._process_edited_metadata(**data)
        if command == 'romanize':
            return self._romanize(**data)

    def _romanize(self, text, number):
        yield 'romanized', {
            'text': unidecode(text).strip(),
            'number': number,
        }

    def _process_initial_download(self, url):
        yield 'progress', {'percentage': 0, 'message': 'Preparing'}

        metadata = json.loads(run([
            'yt-dlp', url, '--dump-json',
        ], stdout=PIPE).stdout)

        process = Popen([
            'yt-dlp', url,
            '--output', self.temp / 'ytdlp',
            '--progress',
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

        while character := process.stdout.read(1):
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

                yield 'progress', {'percentage': percentage, 'message': 'Downloading'}
                percentage = 0
                digits = 0
                fraction = False
            else:
                percentage = 0
                digits = 0
                fraction = False

        yield 'progress', {'percentage': 100, 'message': 'Processing'}
        process.wait()

        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        thumbnail, = (item for item in listdir(self.temp) if item != 'ytdlp.mp3')
        yield 'editor', {
            'thumbnail': str(self.web / thumbnail),
            'title': mp3.get('title', ''),
            'genre': mp3.get('genre', ''),
            'album': mp3.get('album', ''),
            'artist': mp3.get('artist', ''),
            'uploader': metadata['uploader'],
            'name': metadata['title'],
        }

    def _process_edited_metadata(self, title, album, genre, artists):
        artist_field = ' & '.join(artist['pretty'] for artist in artists)

        mp3 = EasyID3(self.temp / 'ytdlp.mp3')
        mp3['title'] = title
        mp3['album'] = album
        mp3['genre'] = genre
        mp3['artists'] = [artist['pretty'] for artist in artists]
        mp3['artist'] = artist_field
        mp3['artistsort'] = [artist['romanized'].lower() for artist in artists]
        mp3.save()

        yield 'finish', {
            'href': str(self.web / 'ytdlp.mp3'),
            'download': artist_field + ' - ' + title,
        }


async def handler(websocket):
    downloader = Downloader()

    while True:
        try:
            message = await websocket.recv()
        except websockets.ConnectionClosedOK:
            break

        data = json.loads(message)
        command = data.pop('command')
        for command, data in downloader.process(command, data):
            data['command'] = command

            try:
                await websocket.send(json.dumps(data))
                await asyncio.sleep(0)
            except websockets.ConnectionClosedOK:
                break


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def signal_to_stop(_1, _2):
        stop.set_result(None)

    signal(SIGTERM, signal_to_stop)
    signal(SIGINT, signal_to_stop)

    port = int(getenv('PORT', '5555'))
    bind = getenv('BIND', 'localhost')
    async with websockets.serve(handler, bind, port):
        await stop


if __name__ == '__main__':
    asyncio.run(main())
