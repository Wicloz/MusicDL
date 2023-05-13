import $ from 'jquery';

const websocket = new WebSocket(
    (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.hostname + '/socket',
);

function setStage(active) {
    if (active === 'progress') {
        $('#progress-done').width('0%');
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
    });
    setStage('progress');
});

websocket.addEventListener('message', ({ data }) => {
    let event = JSON.parse(data);
    console.log(event);

    if (event['command'] == 'progress') {
        $('#progress-done').width(event['percentage'] + '%');
    }

    if (event['command'] == 'editor') {
        $('#edit-img').attr('src', event['thumbnail']);

        $('#edit-title').val(event['title']);
        $('#edit-album').val(event['album']);
        $('#edit-genre').val(event['genre']);

        setStage('edit');
    }

    if (event['command'] == 'finish') {
        let anchor = $('<a>');
        anchor.attr('href', event['href']);
        anchor.attr('download', event['download']);
        anchor.addClass('hidden');

        $('body').append(anchor);
        anchor[0].click();
        anchor.remove();
    }
});
