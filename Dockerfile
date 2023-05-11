FROM alpine

# grab main dependencies
RUN wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && chmod +x /usr/local/bin/yt-dlp
RUN apk add --no-cache ffmpeg python3

# install dependencies using PIP
RUN apk add --no-cache py3-pip && \
    pip3 install websockets mutagen && \
    apk del --no-cache py3-pip

# bundle application
VOLUME /app/public/
COPY --chown=33:33 . /app/

# start server with proper context
EXPOSE 5555
WORKDIR /app/
USER 33:33
CMD /app/server.py
