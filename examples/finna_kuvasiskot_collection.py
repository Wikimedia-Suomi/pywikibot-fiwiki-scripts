# Script loads Kuvasiskot collection from Finna and calcualtes dhash and phash for the images
#
## Install
# mkdir pywikibot
# cd pywikibot
# python3 -m venv ./venv
# source venv/bin/activate
# pip install pywikibot imagehash urllib

## Create user-config.py if it is needed
# echo "usernames['commons']['commons'] = 'ZacheBot'" > user-config.py

## Running
# python finna_kuvasiskot_collection.py

import urllib
import pywikibot
import json
import time
import imagehash
from PIL import Image


# urlencode Finna parameters
def finna_api_parameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)

# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

def calculate_phash(im):
    hash = imagehash.phash(im)
    hash_int=int(str(hash),16)
    return hash_int

# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

def calculate_dhash(im):
    hash = imagehash.dhash(im)
    hash_int=int(str(hash),16)
    return hash_int

# Finna search url filter ui parameters can be generated using web UI https://finna.fi 
# and then click "Finna API" link on bottom of the page.
 
def get_finna_by_filter(page):
    data = None
    url="https://api.finna.fi/v1/search?" 
    url+= finna_api_parameter('filter[]', '~format_ext_str_mv:"0/Image/"') 
    url+= finna_api_parameter('filter[]', 'free_online_boolean:"1"') 
    url+= finna_api_parameter('filter[]', '~hierarchy_parent_title:"Studio Kuvasiskojen kokoelma"')  
    url+= finna_api_parameter('filter[]', '~usage_rights_str_mv:"usage_B"') 
    url+= finna_api_parameter('type','AllFields')
    url+= finna_api_parameter('field[]', 'id')
    url+= finna_api_parameter('field[]', 'title')
    url+= finna_api_parameter('field[]', 'subTitle')
    url+= finna_api_parameter('field[]', 'summary')
    url+= finna_api_parameter('field[]', 'imageRights')
    url+= finna_api_parameter('field[]', 'images')
    url+= finna_api_parameter('field[]', 'imagesExtended')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'openUrl')
    url+= finna_api_parameter('field[]', 'nonPresenterAuthors')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('limit','100') 
    url+= finna_api_parameter('page',str(page)) 

    with urllib.request.urlopen(url) as file:
        try:
            data = json.loads(file.read().decode())
        except:
            data = None
    return data

images=[]
for page in range(1,101):
    data=get_finna_by_filter(page)
    if not data or not 'records' in data:
        break

    for record in data['records']:
        r={}
        r['id']=record['id']
        r['copyright']=record['imageRights']['copyright']
        r['thumbnail']="https://finna.fi" + record['imagesExtended'][0]['urls']['small']

        # Open the image1 with Pillow
        im = Image.open(urllib.request.urlopen(r['thumbnail']))
        r['phash_int']=calculate_phash(im)
        r['dhash_int']=calculate_dhash(im)
        images.append(r)
        print(r)
        time.sleep(0.01)

    print(".")
    time.sleep(1)    


print(images)
