#!/usr/bin/env python3

from os import getenv
from datetime import datetime, timedelta
import sys, requests, jwt

installation_id = getenv('INSTALLATION_ID', '55555555')
app_id = getenv('APP_ID', '555555')
private_key = getenv('PRIVATE_KEY')
if private_key == None:
  sys.exit("ERROR: PRIVATE_KEY env var was not found")

## generate encoded jwt token
payload = {
  "iat": int(datetime.now().timestamp()),
  "exp": int((datetime.now() + timedelta(minutes=10)).timestamp()),
  "iss": app_id
}
jwt_token = jwt.encode(payload, private_key, algorithm='RS256')
####

## get installation access token
access_token_url = 'https://api.github.com/app/installations/' + installation_id + '/access_tokens'
access_token_headers = {'Accept': 'application/vnd.github.v3+json', 'Authorization': 'Bearer ' + jwt_token.decode()}
r = requests.post(access_token_url, headers=access_token_headers)
####

print(r.json()['token'])
