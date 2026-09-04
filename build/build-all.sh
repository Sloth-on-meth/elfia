#!/bin/sh
# Rebuild every generated page and calendar file from build/programme.json.
# Re-snapshot the API first if the programme has changed:
#
#   curl -s -X POST -H 'Origin: https://elfia.nl' --data 'lang=en' \
#        https://bo-elfia.lusolab.com/api/programme > build/programme.json
#
set -e
cd "$(dirname "$0")/.."
python3 build/make-lineup.py  . build/programme.json build/lineup-labels.json
python3 build/make-food.py    . build/programme.json
python3 build/make-vendors.py . build/programme.json
python3 build/make-ics.py     . build/programme.json build/lineup-labels.json
echo "done."
