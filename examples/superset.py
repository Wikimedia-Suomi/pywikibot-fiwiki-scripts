# Script logins to https://superset.wmcloud.org 
# and runs a SQL query

# Requirements
# 1.) Open https://superset.wmcloud.org/login/ with browser and do Oauth login 

# 2.) Running the script
# - python3 -m venv venv
# - source venv/bin/activate
# - pip install pywikibot
# - echo "usernames['meta']['meta'] = 'YORUUSERNAME'" >> user-config.py
# - python superset.py

import pywikibot
from pywikibot.comms import http

# Mediawiki login to meta.wikimedia.org

print("Meta login")
site = pywikibot.Site('meta')
site.login()
print(site.user())
print("")

# Superset login using OAUTH
# - Requires manual first time login and approval first
# - https://superset.wmcloud.org/login/

superset_url='https://superset.wmcloud.org'
url=f'{superset_url}/login/mediawiki?next='
print(f'Superset: {url}')
last_response = http.fetch(url)
print(last_response)

# Checking that user is logged in

headers={}
url = f'{superset_url}/api/v1/me/'
print(f'Superset: {url}')
last_response = http.fetch(url, headers=headers)
print(last_response)
print(last_response.json())
print("")

# Just sample superset API query to list databases

url=f'{superset_url}/api/v1/database/2/schemas/?q=(force:!f)'
print(f'Superset: {url}')
last_response = http.fetch(url, headers=headers)
print(last_response)
print(last_response.json())
print("")

# Load CSRF token

url=f'{superset_url}/api/v1/security/csrf_token/'
print(f'Superset: {url}')
last_response = http.fetch(url, headers=headers)
print(last_response)
print(last_response.json())
print("")
token=last_response.json()['result']

headers = {
    "X-CSRFToken": token,
    "Content-Type": "application/json",
    "referer": "https://superset.wmcloud.org/sqllab/"
}
# SQL Query

# Define the SQL query payload
# - Database id mapping:
# - https://noc.wikimedia.org/conf/highlight.php?file=db-production.php

sql_query_payload = {
    "database_id":2,
    "schema":"fiwiki_p",
    "sql":"SELECT page_id, page_namespace, page_title FROM page LIMIT 2;",
    "queryLimit":1000,
    "json":True,
    "runAsync":False,
}

# Actual query

url=f'{superset_url}/api/v1/sqllab/execute/'
print(f'Superset: {url} {sql_query_payload} {headers}')
last_response = http.fetch(uri=url, json=sql_query_payload, method='POST', headers=headers)
print(last_response)
json=last_response.json()
    
for row in json['data']:
    print(row)
