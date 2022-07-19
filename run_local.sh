#!/usr/bin/env bash
SERVER_PORT=${1-5000}
export SERVER_PORT=${SERVER_PORT}
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_USER=dhos-sms-api
export DATABASE_PASSWORD=dhos-sms-api
export DATABASE_NAME=dhos-sms-api
export FLASK_APP=dhos_sms_api/autoapp.py
export ENVIRONMENT=DEVELOPMENT
export ALLOW_DROP_DATA=true
export LOG_LEVEL=${LOG_LEVEL:-DEBUG}
export LOG_FORMAT=${LOG_FORMAT:-COLOUR}
export TWILIO_CALL_BACK_URL=http://dummy-callback-url
export COUNTRY_CODE=GB
export TWILIO_ACCOUNT_SID=something
export TWILIO_AUTH_TOKEN=something
export TWILIO_DISABLED=true


if [ -z "$*" ]
then
  flask db upgrade
  python3 -m dhos_sms_api
else
  python3 -m flask $*
fi
