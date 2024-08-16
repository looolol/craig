#!/bin/bash

export DISCORD_TOKEN=""

export DISCORD_CHANNEL_ID=""

export RSS_FEED=""
export POLLING_INTERVAL="900"

export RATE_LIMIT_STATUS="429"

export ID_FILE="processed_ids.json"
export LOG_FILE="craig.log"

python3 app/craig.py