FROM nodered/node-red:latest

ARG PROJECT_DIR

USER root

RUN apk update && apk add --no-cache \
    python3 \
    make \
    g++ \
    zeromq-dev

RUN mkdir -p /tmp/.ipc && chown -R node-red:node-red /tmp/.ipc

USER node-red
WORKDIR /usr/src/node-red

COPY ${PROJECT_DIR}/package.json /tmp/package.json
RUN PKGS=$(node -e "try { const d = require('/tmp/package.json').dependencies || {}; console.log(Object.keys(d).map(k => k + '@' + d[k]).join(' ')); } catch(e) {}"); \
    if [ -n "$PKGS" ]; then \
        echo "Instalando pacotes: $PKGS"; \
        npm install --unsafe-perm --no-update-notifier --no-fund --omit=dev $PKGS; \
    else \
        echo "Nenhuma dependencia encontrada. Subindo ambiente limpo."; \
    fi
