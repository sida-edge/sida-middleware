FROM nodered/node-red:latest

USER root

RUN apk update && apk add --no-cache \
    python3 \
    make \
    g++ \
    zeromq-dev

RUN mkdir -p /tmp/.ipc && chown -R node-red:node-red /tmp/.ipc

USER node-red

RUN npm install node-red-contrib-zeromq