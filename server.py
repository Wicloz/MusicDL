import socketio
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
EasyID3.RegisterTXXXKey('purl', 'purl')
EasyID3.RegisterTXXXKey('description', 'description')


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

    @staticmethod
    def _extract(metadata, *keys):
        for key in keys:
            if key in metadata:
                return metadata[key]
        return ''

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
        mp3['date'] = self._extract(metadata, 'upload_date')
        mp3['description'] = self._extract(metadata, 'description')
        mp3['purl'] = self._extract(metadata, 'webpage_url')
        mp3.save()

        thumbnail, = (item for item in listdir(self.temp) if item != 'ytdlp.mp3')
        yield 'editor', {
            'title': self._extract(metadata, 'track', 'title'),
            'genre': self._extract(metadata, 'genre'),
            'album': self._extract(metadata, 'album'),
            'artist': self._extract(metadata, 'artist', 'creator', 'uploader', 'uploader_id'),
            'thumbnail': str(self.web / thumbnail),
            'uploader': self._extract(metadata, 'uploader'),
            'name': self._extract(metadata, 'title'),
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


sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)
connections = {}


@sio.event
def connect(sid, _1, _2):
    connections[sid] = Downloader()


@sio.event
def disconnect(sid):
    del connections[sid]


@sio.on('*')
def process(command, sid, data):
    for command, data in connections[sid].process(command, data):
        sio.emit(command, data, sid)
