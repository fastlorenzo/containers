#!/bin/sh

# Fix user id
PUID=${PUID:-911}
PGID=${PGID:-911}

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
	EXCLUDE="--exclude /settings/exclude"
else
	echo "INFO: exclude file not found!"
fi
# check unsyncedfolders file exists
if [ -e "/settings/unsyncfolders" ]; then
	UNSYNCEDFOLDERS="--unsyncedfolders /settings/unsyncfolders"
else
	echo "INFO: unsync file not found!"
fi

while true
do
	su-exec ncsync nextcloudcmd $( [ "$NC_HIDDEN" == true ] && echo "-h" ) $( [ "$NC_SILENT" == true ] && echo "--silent" ) $( [ "$NC_TRUST_CERT" == true ] && echo "--trust" ) $( [ "$EXCLUDE" ] && echo $EXCLUDE ) $( [ "$UNSYNCEDFOLDERS" ] && echo $UNSYNCEDFOLDERS ) --non-interactive -u $NC_USER -p $NC_PASS $NC_SOURCE_DIR $NC_URL

	#chown the files to the USER_UID:
	echo "chown -R ncsync:ncsync $NC_SOURCE_DIR";
	chown -R ncsync:ncsync $NC_SOURCE_DIR

	#check if exit!
	if [ "$NC_EXIT" = true ] ; then

		if [  ! "$NC_SILENT" == true ] ; then
			echo "NC_EXIT is true so exiting... bye!"
		fi

		exit;
	fi
	sleep $NC_INTERVAL
done

exit 1
