var websocket = new WebSocket((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.hostname + '/socket');

queryElem = document.getElementById('query-div');
progressElem = document.getElementById('progress-div');
editElem = document.getElementById('edit-div');

document.getElementById('query-form').addEventListener('submit', function (e) {
    e.preventDefault();
    input = document.getElementById('query-url');

    if (input.value) {
        websocket.send(JSON.stringify({
            command: 'download',
            url: input.value,
        }));

        queryElem.classList.add("disabled");
        progressElem.classList.remove("disabled");
    }
});

document.getElementById('edit-form').addEventListener('submit', function (e) {
    e.preventDefault();

    websocket.send(JSON.stringify({
        command: 'edited',
        title: document.getElementById('edit-title').value,
        album: document.getElementById('edit-album').value,
        genre: document.getElementById('edit-genre').value,
    }));

    editElem.classList.add("disabled");
    progressElem.classList.remove("disabled");
});

websocket.addEventListener('message', ({ data }) => {
    let event = JSON.parse(data);
    console.log(event);

    if (event['command'] == 'progress') {
        document.getElementById('progress-done').style.width = event['percentage'] + '%';
    }

    if (event['command'] == 'editor') {
        document.getElementById('edit-img').src = event['thumbnail'];
        document.getElementById('edit-title').value = event['title'];
        document.getElementById('edit-album').value = event['album'];
        document.getElementById('edit-genre').value = event['genre'];

        progressElem.classList.add("disabled");
        editElem.classList.remove("disabled");
    }

    if (event['command'] == 'finish') {
        var anchorTag = document.createElement('a');

        anchorTag.href = event['href'];
        anchorTag.download = event['download'];

        document.body.appendChild(anchorTag);
        anchorTag.click();
        document.body.removeChild(anchorTag);
    }
});
