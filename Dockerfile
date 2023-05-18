# build container, requires node
FROM node:alpine AS builder
WORKDIR /app/

# install NPM packages
COPY package.json /app/
COPY package-lock.json /app/
RUN npm install && npm audit fix

# copy and build source files
COPY ./source/ /app/source/
COPY .parcelrc /app/
RUN npm run build

# production container, no requirements
FROM alpine

# install additional packages
RUN apk add --no-cache python3 yt-dlp rsync

# install PIP requirements
COPY requirements.txt /app/
RUN apk add --no-cache py3-pip && pip3 install -r /app/requirements.txt && apk del --no-cache py3-pip

# copy static files from build container
VOLUME /app/public/
COPY --from=builder /app/public/ /app/built/
RUN mkdir /app/built/downloads/

# install remaining files
COPY server.py /app/
COPY entrypoint.sh /app/

# prepare working directory and user
WORKDIR /app/
ENV UID=33 GID=33
RUN install -o $UID -g $GID -d /app/public/
USER $UID:$GID

# start websocket server
EXPOSE 5555
ENV BIND='' PORT='5555'
ENTRYPOINT /app/entrypoint.sh
