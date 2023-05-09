FROM node:lts-alpine

# install OS dependencies
RUN apk add --no-cache ffmpeg python3

# set working folder
WORKDIR /app/

# install NPM dependencies
COPY package.json /app/
COPY package-lock.json /app/
RUN npm install --omit=dev
RUN npm audit fix

# bundle application
VOLUME /app/public/
COPY --chown=33:33 . /app/

# expose and start server
EXPOSE 3000
USER 33:33
CMD [ "node", "server.js" ]
