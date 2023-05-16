import asyncio
import websockets
import json
from secrets import choice
from pathlib import Path, PurePosixPath
from subprocess import Popen, PIPE, run
from tempfile import TemporaryDirectory
from unidecode import unidecode
from os import listdir, getenv

from mutagen.easyid3 import EasyID3
EasyID3.RegisterTXXXKey('artists', 'ARTISTS')


class Connection:
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
        metadata = json.loads(run([
            'yt-dlp', url, '--dump-json',
        ], stdout=PIPE).stdout)

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
                    if not fraction:
                        percentage *= 10
                        percentage += int(character)
                    else:
                        digits += 1
                        percentage += int(character) / (10 ** digits)

                elif character == '.':
                    fraction = True
                elif character == '%':
                    yield 'progress', {'percentage': percentage}
                    percentage = 0
                    digits = 0
                    fraction = False
                else:
                    percentage = 0
                    digits = 0
                    fraction = False

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
    connection = Connection()

    while True:
        try:
            message = await websocket.recv()
        except websockets.ConnectionClosedOK:
            break

        data = json.loads(message)
        command = data.pop('command')
        for command, data in connection.process(command, data):
            data['command'] = command
            await websocket.send(json.dumps(data))
            await asyncio.sleep(0)


async def main():
    port = int(getenv('PORT', '5555'))
        await asyncio.Future()
    bind = getenv('BIND', 'localhost')
    async with websockets.serve(handler, bind, port):


if __name__ == '__main__':
    asyncio.run(main())
