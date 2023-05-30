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
        artists: _.range(numberOfArtists).map((index) => {
            let lastName = $('#edit-artist-last-' + index).val();
            return {
                pretty: $('#edit-artist-first-' + index).val() + (lastName ? ' ' + lastName : ''),
                romanized: $('#edit-artist-romaji-' + index).val(),
            };
        }),
    });
});

websocket.addEventListener('message', ({ data }) => {
    let event = JSON.parse(data);
    console.log(event);

    if (event['command'] == 'progress') {
        $('#progress-message').text(event['message']);
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
        $('#edit-artist-first-0').val(event['artist']);

        romanizeArtist(0);
        setStage('edit');
    }

    if (event['command'] == 'romanized') {
        $('#edit-artist-romaji-' + event['number']).val(event['text']);
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

function romanizeArtist(number) {
    let lastName = $('#edit-artist-last-' + number).val();
    message('romanize', {
        text: (lastName ? lastName + ' ' : '') + $('#edit-artist-first-' + number).val(),
        number: number,
        script: $('#edit-artist-script-' + number).val(),
    });
}

let numberOfArtists = 0;
function registerArtistOns(number) {
    let lastNameElement = $('#edit-artist-last-' + number);
    let firstNameElement = $('#edit-artist-first-' + number);

    $('#edit-artist-proper-' + number).on('change', (event) => {
        if (event.target.checked) {
            firstNameElement.attr('placeholder', 'First Name');
            lastNameElement.removeClass('disabled');
        } else {
            firstNameElement.attr('placeholder', 'Nickname');
            lastNameElement.addClass('disabled');
            lastNameElement.val('');
            romanizeArtist(number);
        }
    });

    $('#edit-artist-new-' + number).on('click', (event) => {
        event.preventDefault();

        let process2 = (text) => {
            let parts = text.split('-');
            parts.pop();
            parts.push(numberOfArtists);
            return parts.join('-');
        };

        let process1 = (element) => {
            if (element.attr('id')) {
                element.attr('id', process2(element.attr('id')));
            }
            if (element.attr('for')) {
                element.attr('for', process2(element.attr('for')));
            }
            if (element.val()) {
                element.val('');
            }
        };

        let copy = $('#edit-artist-' + number).clone();
        process1(copy);
        copy.children().each((index, element) => {
            process1($(element));
        });

        $('#edit-form').append(copy);
        registerArtistOns(numberOfArtists);
    });

    firstNameElement.on('change', (event) => {
        event.target.value = _.trim(event.target.value);
        romanizeArtist(number);
    });
    lastNameElement.on('change', (event) => {
        event.target.value = _.trim(event.target.value);
        romanizeArtist(number);
    });

    $('#edit-artist-script-' + number).on('change', (event) => {
        romanizeArtist(number);
    });
    $('#edit-artist-romaji-' + number).on('change', (event) => {
        event.target.value = _.trim(event.target.value);
    });

    numberOfArtists += 1;
}

registerArtistOns(0);
$('#edit-title, #edit-album, #edit-genre').on('change', (event) => {
    event.target.value = _.trim(event.target.value);
});
