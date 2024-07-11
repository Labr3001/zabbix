#!/bin/bash

##########################################################################
# Zabbix-Telegram envio de alerta por Telegram com graficos dos eventos
# Date: 25/10/2017
# Original script by Diego Maia - diegosmaia@yahoo.com.br Telegram - @diegosmaia
# Updated by [Your Name]
##########################################################################

MAIN_DIRECTORY="/usr/lib/zabbix/alertscripts"
DEBUG_FILE="/dev/null"

#############################################
# Argument to pass to the script and its manipulation
#############################################

USER=$1
SUBJECT=$2
TEXT=$3

# Check if there is only 2 argument (no test message, only subject)
if [ -z "$TEXT" ]; then
    TEXT=""
fi

# Get status and severity from subject
STATUS=$(echo $SUBJECT | awk '{print $1;}')
SEVERITY=$(echo $SUBJECT | awk '{print $2;}')
SUBJECT=${SUBJECT#"$STATUS "}
SUBJECT=${SUBJECT#"$SEVERITY "}
SUBJECT="${SUBJECT//,/ }"

# Get graphid from text
GRAPHID=$(echo $TEXT | grep -o -E "(Item Graphic: \[[0-9]{1,7}\])")
TEXT=${TEXT%"$GRAPHID"}
MESSAGE="chat_id=${USER}&text=${TEXT}"
GRAPHID=$(echo $GRAPHID | grep -o -E "[0-9]{1,7}")

# Save text to send in file
ZABBIXMSG="/tmp/telegram-zabbix-message-$(date "+%Y.%m.%d-%H.%M.%S").tmp"
echo "$MESSAGE" > $ZABBIXMSG

#############################################
# Zabbix address
#############################################
ZBX_URL="http://103.121.88.225/zabbix"

##############################################
# Zabbix credentials to login
##############################################

USERNAME="admin"
PASSWORD="sv74b@U3$#vPNa%X"

#############################################
# Telegram Bot data
#############################################

BOT_TOKEN='5832192848:AAEI6-qXA_uQxwIle2wdJhDBYcNB1osfetE'

#############################################
# Zabbix GUI name
#############################################

#############################################
# To enable/disable graph sending and message content
#############################################

SEND_GRAPH=1
SEND_MESSAGE=1

# If the GRAPHID variable is not compliant, do not send the graph
case $GRAPHID in
    ''|*[!0-9]*) SEND_GRAPH=0 ;;
esac

# Graph settings
WIDTH=800
PERIOD=10800
CURL="/usr/bin/curl"
COOKIE="/tmp/telegram_cookie-$(date "+%Y.%m.%d-%H.%M.%S")"
PNG_PATH="/tmp/telegram_graph-$(date "+%Y.%m.%d-%H.%M.%S").png"

###########################################
# Check if at least 2 parameters are passed to script
###########################################

if [ "$#" -lt 2 ]; then
    exit 1
fi

# Convert STATUS and SEVERITY from text to ICON
case $STATUS in
    "PROBLEM") ICON="%E2%9A%A0";; # Warning sign
    "OK") ICON="%E2%9C%85";; # Check mark
    *) ICON="";;
esac

case $SEVERITY in
    "Not classified") ICON_SEV="%E2%9C%89";; # Envelope
    "Information") ICON_SEV="%F0%9F%98%8C";; # Relieved face
    "Warning") ICON_SEV="%F0%9F%98%9E";; # Disappointed face
    "Average") ICON_SEV="%F0%9F%98%A8";; # Fearful face
    "High") ICON_SEV="%F0%9F%98%A9";; # Weary face
    "Disaster") ICON_SEV="%F0%9F%98%B1";; # Face screaming in fear
    *) ICON_SEV="";;
esac

############################################
# Send messages with SUBJECT and TEXT
############################################

${CURL} -k -s -S --max-time 5 -c ${COOKIE} -b ${COOKIE} -d "name=${USERNAME}&password=${PASSWORD}&autologin=1&enter=Sign%20in" ${ZBX_URL}/index.php >> $DEBUG_FILE

# If SEND_GRAPH=1 send the graph
if [ "$SEND_GRAPH" -eq '1' ]; then
    ${CURL} -k -s -S --max-time 5 -c ${COOKIE} -b ${COOKIE} -d "itemids%5B0%5D=${GRAPHID}&period=${PERIOD}&width=${WIDTH}" ${ZBX_URL}/chart.php -o "${PNG_PATH}";
fi

# Send the image to Telegram
if [ "$SEND_MESSAGE" -eq 1 ]; then
    ${CURL} -k -s -S --max-time 5 -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto" -F chat_id="${USER}" -F photo="@${PNG_PATH}" -F caption="${TEXT} - ${ZABBIX_GUI_NAME}" >> $DEBUG_FILE
fi

# Clean up files used in the script execution
rm -f ${COOKIE}
rm -f ${PNG_PATH}
rm -f ${ZABBIXMSG}

exit 0
