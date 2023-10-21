# build container, requires node
FROM node:lts-alpine AS builder
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
RUN apk add --no-cache python3 py3-pip yt-dlp rsync

# install PIP requirements
COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

# copy static files from build container
VOLUME /app/public/
COPY --from=builder /app/public/ /app/built/
RUN mkdir /app/built/downloads/

# install remaining files
COPY server.py /app/
COPY entrypoint.sh /app/

# prepare cache folder
ENV XDG_CACHE_HOME=/app/cache/
RUN install -o 1000 -g 1000 -d /app/cache/

# prepare working directory and user
WORKDIR /app/
RUN install -o 1000 -g 1000 -d /app/public/
USER 1000:1000

# start websocket server
EXPOSE 5555
ENV HOST='0.0.0.0' PORT='5555'
ENTRYPOINT /app/entrypoint.sh
