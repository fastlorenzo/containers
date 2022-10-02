#!/bin/sh

# Fix user id
PUID=${PUID:-911}
PGID=${PGID:-911}

# Default settings
NC_EXIT=${NC_EXIT:=true}
NC_OPTIONS="--non-interactive"
CHOWN_FILES=${CHOWN_FILEs:=false}

# Append -h to NC_OPTIONS if NC_HIDDEN is true
if [ "$NC_HIDDEN" = "true" ]; then
    NC_OPTIONS="$NC_OPTIONS -h"
fi

# Append --silent to NC_OPTIONS if NC_SILENT is true
if [ "$NC_SILENT" = "true" ]; then
    NC_OPTIONS="$NC_OPTIONS --silent"
fi

# Append --trust if NC_TRUST is true
if [ "$NC_TRUST" = "true" ]; then
    NC_OPTIONS="$NC_OPTIONS --trust"
fi

groupmod -o -g "$PGID" ncsync
usermod -o -u "$PUID" ncsync

echo '
-------------------------------------
GID/UID
-------------------------------------'
echo "
User uid:    $(id -u ncsync)
User gid:    $(id -g ncsync)
-------------------------------------
"

[ -d /settings ] || mkdir -p /settings
chown -R ncsync:ncsync /settings

# check exclude file exists
if [ -e "/settings/exclude" ]; then
	NC_OPTIONS="$NC_OPTIONS --exclude /settings/exclude"
else
	echo "INFO: exclude file not found!"
fi

# check unsyncedfolders file exists
if [ -e "/settings/unsyncfolders" ]; then
	NC_OPTIONS="$NC_OPTIONS --unsyncedfolders /settings/unsyncfolders"
else
	echo "INFO: unsync file not found!"
fi

# Check if NC_USER is set, if not, exit
if [ -z "$NC_USER" ]; then
    echo "ERROR: NC_USER is not set!"
    exit 1
else
    NC_OPTIONS="$NC_OPTIONS --user $NC_USER"
fi
# Check if NC_PASS is set, if not, exit
if [ -z "$NC_PASS" ]; then
    echo "ERROR: NC_PASS is not set!"
    exit 1
else
    NC_OPTIONS="$NC_OPTIONS --password $NC_PASS"
fi
# Check if NC_PATH is set, if not, exit
if [ -z "$NC_PATH" ]; then
    echo "ERROR: NC_PATH is not set!"
    exit 1
else
    NC_OPTIONS="$NC_OPTIONS --path $NC_PATH"
fi

# Check if NC_URL is set, if not, exit
if [ -z "$NC_URL" ]; then
    echo "ERROR: NC_URL is not set!"
    exit 1
fi

# Check if NC_SOURCE_DIR is set, if not, exit
if [ -z "$NC_SOURCE_DIR" ]; then
    echo "ERROR: NC_SOURCE_DIR is not set!"
    exit 1
fi

while true
do
	su-exec ncsync nextcloudcmd $NC_OPTIONS $NC_SOURCE_DIR $NC_URL

	# chown the files to the USER_UID if CHOWN_FILES is true
    if [ "$CHOWN_FILES" = "true" ]; then
        echo "INFO: chowning files in $NC_SOURCE_DIR to $PUID:$PGID"
        chown -R ncsync:ncsync $NC_SOURCE_DIR
    fi

	# Exit 0 if NC_EXIT is true
    if [ "$NC_EXIT" = "true" ]; then
        echo "INFO: NC_EXIT is true, exiting..."
        exit 0
    fi

    echo "INFO: NC_EXIT is false, sleeping for $NC_INTERVAL seconds..."
    sleep $NC_INTERVAL
done

exit 1
