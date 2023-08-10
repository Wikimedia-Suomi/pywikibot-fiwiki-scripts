# Script finds Wikimedia Commons files which doesn't have any statements and adds mime type statement
# This is workaround for bug <CREATE BUG TICKET TO PHABRICATOR> where pywikibot fails when PHP
# backend returns MediaInfo data with wrong type for files with no statements.

## Install
# mkdir pywikibot
# cd pywikibot
# python3 -m venv ./venv
# source venv/bin/activate
# pip install pywikibot

## Create user-config.py if it is needed
# echo "usernames['commons']['commons'] = 'ZacheBot'" > user-config.py

## Running
# python create_missing_mediainfo.py

import pywikibot
import json

# Create SDC MediaInfo statement using pywikibot simple_request
def createMediainfoClaim(site, media_identifier, property, value):

   csrf_token = site.tokens['csrf']
   # payload documentation
   # https://www.wikidata.org/w/api.php?action=help&modules=wbcreateclaim
   payload = {
      'action' : 'wbcreateclaim',
      'format' : u'json',
      'entity' : media_identifier,
      'property' : property,
      'snaktype' : 'value',
      'value' : f'"{value}"',
      'token' : csrf_token,
      'bot' : True, # in case you're using a bot account (which you should)
   }

   request = site.simple_request(**payload)
   try:
      ret=request.submit()

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)

# Reads image mime type from API
def get_mime_type(file_title):
    mime_type=False

    request = site.simple_request(
        action='query',
        titles=file_title,
        prop='imageinfo', 
        iiprop='mime'
    )
    # Execute the request
    result = request.submit()
      
    # Extract the MIME type from the result
    pages = result['query']['pages']
    for page_id, page_data in pages.items():
        mime_type = page_data['imageinfo'][0]['mime']
    return mime_type
    
def add_P1163_mime_type(site, page):
     media_identifier='M' + str(page.pageid)
     property='P1163'  # P1163 = Mime type
     mime_type = get_mime_type(page.title())
   
     pywikibot.output(f"Adding {property} (MIME type) = '{mime_type}' to ':c:{page.title()}' ({media_identifier})")
     createMediainfoClaim(site, media_identifier, property, mime_type)

site = pywikibot.Site('commons', 'commons')  # The site we're working on
page = pywikibot.Page(site, 'user:FinnaUploadBot/filelist')  # The page you're interested in

# Get all linked pages from the page
for page in page.linkedPages():
    
    # Create new mediainfo with one statement if there is no mediainfo at all
    if not 'mediainfo' in page.latest_revision.slots:
        add_P1163_mime_type(site, page)
        continue
     
    # Bugfix: API returns empty content['statements'] as a list. It should be
    # dictionary. We fix this by adding a first statement
      
    data=page.latest_revision.slots['mediainfo']['*']
    content=json.loads(data)
    if isinstance(content['statements'], list):
        add_P1163_mime_type(site, page)
        continue

