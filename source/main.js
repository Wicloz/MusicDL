import $ from 'jquery';
import _ from 'lodash';

const websocket = new WebSocket(
    (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.hostname + '/socket',
);

function setStage(active) {
    if (active === 'progress') {
        $('#progress-done').width('0%');
        $('#progress-done').text('0%');
    }

    for (const element of ['query', 'progress', 'edit']) {
        if (element === active) {
            $('#' + element + '-div').removeClass('disabled');
        } else {
            $('#' + element + '-div').addClass('disabled');
        }
    }
}

function message(command, data) {
    data['command'] = command;
    console.log(data);
    websocket.send(JSON.stringify(data));
}

$('#query-form').on('submit', (event) => {
    event.preventDefault();

    let url = $('#query-url').val();
    if (url) {
        message('download', { url: url });
        setStage('progress');
    }
});

$('#edit-form').on('submit', (event) => {
    event.preventDefault();

    message('edited', {
        title: $('#edit-title').val(),
        album: $('#edit-album').val(),
        genre: $('#edit-genre').val(),
        artists: $('#edit-artist').val(),
    });
});

websocket.addEventListener('message', ({ data }) => {
    let event = JSON.parse(data);
    console.log(event);

    if (event['command'] == 'progress') {
        $('#progress-done').width(event['percentage'] + '%');
        $('#progress-done').text(event['percentage'] + '%');
    }

    if (event['command'] == 'editor') {
        $('#video-cover-art').attr('src', event['thumbnail']);
        $('#video-name').text(event['name']);
        $('#video-uploader').text(event['uploader']);

        $('#edit-title').val(event['title']);
        $('#edit-album').val(event['album']);
        $('#edit-genre').val(event['genre']);
        $('#edit-artist').val(event['artist']);

        setStage('edit');
    }

    if (event['command'] == 'finish') {
        let anchor = $('<a>');
        anchor.attr('href', event['href']);
        anchor.attr('download', event['download'] + '.mp3');
        anchor.addClass('disabled');

        $('body').append(anchor);
        anchor[0].click();
        anchor.remove();
    }
});
