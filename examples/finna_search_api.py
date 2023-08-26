# Script updates kuvasiskot images with better resolution images from Finna
#
## Install
# mkdir pywikibot
# cd pywikibot
# python3 -m venv ./venv
# source venv/bin/activate
# pip install urllib

## Running
# python finna_search_api.py

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

def get_finna_search():
    finna_params=get_finna_params()

    url="https://api.finna.fi/v1/search?"

    # Return only images
    url+= finna_api_parameter('filter[]', '~format_ext_str_mv:"0/Image/"')

    # Return only results with free online image
    url+= finna_api_parameter('filter[]', 'free_online_boolean:"1"')

    # Collection
    url+= finna_api_parameter('filter[]', '~hierarchy_parent_title:"Studio Kuvasiskojen kokoelma"')

    # Return only results with right to use commercially and edit
    url+= finna_api_parameter('filter[]', '~usage_rights_str_mv:"usage_B"')

    # Search keys
    url+= finna_api_parameter('lookfor','"professorit"+"miesten+puvut"')      # Searchkey

    # Where search key matches
    url+= finna_api_parameter('type','Subjects')                              # Search only from subjects

    # Add parameters
    for param in finna_params:
        url+=finna_api_parameter('field[]', param)

    print(url)
    try:
        response = requests.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        exit(1)

data=get_finna_search()
pretty_json = json.dumps(data, indent=4)
print(pretty_json)
