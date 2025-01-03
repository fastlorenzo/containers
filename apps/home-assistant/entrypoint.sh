#!/usr/bin/env bash

mkdir -p /config/logs

if [[ "${HOME_ASSISTANT__HACS_INSTALL}" == "true" ]]; then
    curl -sfSL https://get.hacs.xyz | bash -
fi

exec \
    /usr/local/bin/hass \
        --config /config \
        --log-file /config/logs/home-assistant.log \
        "$@"
