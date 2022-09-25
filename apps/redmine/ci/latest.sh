#!/usr/bin/env bash
version=$(curl -sX GET "https://raw.githubusercontent.com/bitnami/containers/main/bitnami/redmine/5/debian-11/tags-info.yaml" | yq '.rolling-tags[2]')
version="${version#*v}"
version="${version#*release-}"
printf "%s" "${version}"
