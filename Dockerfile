FROM nodered/node-red:latest

USER root

RUN apk update && apk add --no-cache \
    python3 \
    make \
    g++ \
    zeromq-dev

USER node-red

RUN npm install node-red-contrib-zeromq