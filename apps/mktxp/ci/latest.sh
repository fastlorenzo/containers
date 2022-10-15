#!/usr/bin/env bash
# No version information from https://github.com/akpw/mktxp
version=$(curl -sXGET https://pypi.org/project/mktxp/ | grep '<h1 class="package-header__name">' -A1 | tail -n1 | awk '{print $2}')
printf "%s" "${version}"
