# This is example howto to create mediainfo for commons files using pywikibot simple_request 
# running
# python create_sdc_mediainfo.py

import pywikibot
import time
import json  

def createMediainfoClaim(site, media_identifier, property, value):
   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbcreateclaim',
      'format' : u'json',
      'entity' : media_identifier,
      'property' : property,
      'snaktype' : 'value',
      'value' : json.dumps(value),
      'token' : csrf_token,
      'bot' : True, # in case you're using a bot account (which you should)
   }
   print(payload)
   request = site.simple_request(**payload)
   try:
      ret=request.submit()
      claim=ret.get("claim")
      if claim:
         return claim.get("id")
      else:
         print("Claim created but there was an unknown problem")
         print(ret)
         exit(1)
      
   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)

def addCaption(site, media_identifier, lang, caption):
   captions={}
   captions[lang] = {u'language' : lang, 'value' : caption }
   data={ u'labels' : captions}
   wbEditEntity(site, media_identifier, data)

def wbEditEntity(site, media_identifier, data):
   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbeditentity',
      'format' : u'json',
      'id' : media_identifier,
      'data' :  json.dumps(data),
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

## MAIN

commons_site = pywikibot.Site("commons", "commons") # Connect to the Wikimedia Commons site
   
# Get filepage
pagename='File:Antonietta-Toini-1940s.jpg'
page = pywikibot.FilePage(commons_site, pagename)
media_identifier='M' + str(page.pageid)
      
# Add caption
caption='oopperalaulajatar Antonietta Toini oikealta nimeltään Toini Nikander 1940-luvulla'
addCaption(commons_site, media_identifier, 'fi', caption)
      
# Add first statement
property='P180' # P180 = Depicts
value={'entity-type':'item','id': "Q16658256" } # Antoinia Toini
createMediainfoClaim(commons_site, media_identifier, property, value)
      
# Test that mediainfo works 
item = page.data_item()
data=item.get()
