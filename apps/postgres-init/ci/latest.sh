#!/usr/bin/env bash
version=$(curl -sXGET "https://pkgs.alpinelinux.org/package/v3.20/community/s390x/postgresql14-client" | grep -oP '(?<=<strong>).*?(?=</strong>)' 2>/dev/null)
version="${version%%_*}"
version="${version%%-*}"
printf "%s" "${version}"
