const express = require('express');
const app = express();
const http = require('http');
const server = http.createServer(app);
const { Server } = require('socket.io');
const io = new Server(server);
const youtubedl = require('youtube-dl-exec');
const crypto = require('crypto');
const { glob } = require('glob');
const { fstat } = require('fs');
const fs = require('fs');

app.get('/', (req, res) => {
  res.sendFile(__dirname + '/public/index.html');
});
app.get('/public/downloads/:file', (req, res) => {
  res.sendFile(__dirname + '/public/downloads/' + req.params['file']);
});

io.on('connection', (socket) => {
  let source = '';
  let random = crypto.randomBytes(16).toString('hex');

  function extract(json, ...keys) {
    for (const key of keys) {
      if (key in json) {
        return json[key];
      }
    }
    return '';
  }

  socket.on('query', async (query) => {
    source = query;

    await youtubedl(query, {
      'output': __dirname + '/public/downloads/' + random,
      'skipDownload': true,
      'writeThumbnail': true,
      'convertThumbnails': 'webp',
    });

    youtubedl(query, { 'dumpJson': true }).then((output) => {
      socket.emit('metadata', {
        'thumbnail': '/public/downloads/' + random + '.webp',

        'title': extract(output, 'track', 'title'),
        'artist': extract(output, 'artist', 'creator', 'uploader', 'uploader_id'),
        'genre': extract(output, 'genre'),
        'album': extract(output, 'album'),
      });
    });
  });

  socket.on('download', (metadata) => {
    youtubedl(source, {
      'output': __dirname + '/public/downloads/' + random,
      'format': 'bestaudio',
      'extractAudio': true,
      'audioFormat': 'mp3',
      'embedThumbnail': true,
      'embedMetadata': true,
    }).then((output) => {
      console.log(output);
      socket.emit('finish', {
        'href': '/public/downloads/' + random + '.mp3',
        'download': metadata['title'],
      });
    });
  });

  socket.on('disconnect', () => {
    glob(__dirname + '/public/downloads/' + random + '.*').then((files) => {
      for (const file of files) {
        fs.unlinkSync(file);
      }
    });
  });
});

server.listen(3000, () => {
  console.log('listening on *:3000');
});