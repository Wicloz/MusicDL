FROM alpine

# install additional packages
RUN apk add --no-cache ffmpeg yt-dlp

# install PIP requirements
RUN apk add --no-cache py3-pip && pip3 install -r requirements.txt && apk del --no-cache py3-pip

# bundle application
VOLUME /app/public/
COPY --chown=33:33 . /app/

# start server with proper context
EXPOSE 5555
WORKDIR /app/
USER 33:33
CMD /app/server.py
