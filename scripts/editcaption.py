import pywikibot
import json

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
      'bot' : True, # in case you're using a bot account 
   }
   request = site.simple_request(**payload)
   try:
      ret=request.submit()

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)


site = pywikibot.Site('commons', 'commons')
site.login()
file_page = pywikibot.FilePage(site, 'Aleksis Kiven katu 18 - Ajapaik-rephoto-2019-09-14 13-18-03.jpg')
media_identifier='M' + str(file_page.pageid)
print(media_identifier)

addCaption(site, media_identifier, 'fi', 'Aleksis Kiven katu 18, Helsinki, Finland')
