# Script updates kuvasiskot images with better resolution images from Finna
#
## Install
# mkdir pywikibot
# cd pywikibot
# python3 -m venv ./venv
# source venv/bin/activate
# pip install urllib

## Running
# python update_kuvasiskot.py

# Finna API documentation
# * https://api.finna.fi/
# * https://www.kiwi.fi/pages/viewpage.action?pageId=53839221

import json
import urllib
import requests

def get_finna_params():
    ret=[
        'id',
        'title',
        'subTitle',
        'shortTitle',
        'summary',
        'imageRights',
        'images',
        'imagesExtended',
        'onlineUrls',
        'openUrl',
        'nonPresenterAuthors',
        'onlineUrls',
        'subjects',
        'subjectsExtendet',
        'subjectPlaces',
        'subjectActors',
        'subjectDetails',
        'geoLocations',
        'buildings',
        'identifierString',
        'collections',
        'institutions',
        'classifications',
        'events',
        'languages',
        'originalLanguages',
        'year',
        'hierarchicalPlaceNames',
        'formats',
        'physicalDescriptions',
        'measurements'
    ]
    return ret

# urlencode Finna parameters
def finna_api_parameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)

def get_finna_record(id):
    finna_params=get_finna_params()

    url="https://api.finna.fi/v1/record?id=" +  urllib.parse.quote_plus(id)
    for param in finna_params:
        url+=finna_api_parameter('field[]', param)

    print(url)
    try:
        response = requests.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        exit(1)

data=get_finna_record("museovirasto.FE6E74B7E2A32E8AD2B27EF70E5EFE40")
pretty_json = json.dumps(data, indent=4)
print(pretty_json)
