# Script updates kuvasiskot images with better resolution images from Finna
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
# python update_kuvasiskot.py

import pywikibot
import re
import urllib
import requests
import hashlib
import imagehash
import io
import os
import tempfile
from PIL import Image

# Find (old) finna id's from file page urls

def get_finna_ids(page):
    finna_ids=[]

    for url in page.extlinks():
        if "finna.fi" in url:
            id = None

            # Parse id from url
            patterns = [
                           r"finna\.fi/Record/([^?]+)",
                           r"finna\.fi/Cover/Show\?id=([^&]+)",
                           r"finna\.fi/thumbnail\.php\?id=([^&]+)",
                           r"finna\.fi/Cover/Download\?id=([^&]+)",
                       ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    id = match.group(1)
                    if id not in finna_ids:
                        finna_ids.append(id)
                    break

    return finna_ids

# urlencode Finna parameters
def finna_api_parameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)


# Get finna API record with most of the information
# Finna API documentation
# * https://api.finna.fi
# * https://www.kiwi.fi/pages/viewpage.action?pageId=53839221 

def get_finna_record(id):

    url="https://api.finna.fi/v1/record?id=" +  urllib.parse.quote_plus(id)
    url+= finna_api_parameter('field[]', 'id')
    url+= finna_api_parameter('field[]', 'title')
    url+= finna_api_parameter('field[]', 'subTitle')
    url+= finna_api_parameter('field[]', 'summary')
    url+= finna_api_parameter('field[]', 'imageRights')
    url+= finna_api_parameter('field[]', 'images')
    url+= finna_api_parameter('field[]', 'imagesExtended')
    url+= finna_api_parameter('field[]', 'openUrl')
    url+= finna_api_parameter('field[]', 'nonPresenterAuthors')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'subjects')
    url+= finna_api_parameter('field[]', 'geoLocations')
    url+= finna_api_parameter('field[]', 'buildings')
    url+= finna_api_parameter('field[]', 'identifierString')
    url+= finna_api_parameter('field[]', 'collections')
    url+= finna_api_parameter('field[]', 'institutions')
    url+= finna_api_parameter('field[]', 'classifications')
    url+= finna_api_parameter('field[]', 'events')
    url+= finna_api_parameter('field[]', 'languages')
    url+= finna_api_parameter('field[]', 'originalLanguages')
    url+= finna_api_parameter('field[]', 'year')
    url+= finna_api_parameter('field[]', 'formats')

    try:
        response = requests.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        exit(1)

# convert string to base 16 integer for calculating difference
def converthashtoint(h, base=16):
    return int(str(h), base)

# Compares if the image is same using similarity hashing
# method is to convert images to 64bit integers and then
# calculate hamming distance. 
#
# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
#
def is_same_image(img1, img2):

    phash1 = imagehash.phash(img1)
    dhash1 = imagehash.dhash(img1)
    phash1_int = converthashtoint(phash1)
    dhash1_int = converthashtoint(dhash1)

    phash2 = imagehash.phash(img2)
    dhash2 = imagehash.dhash(img2)
    phash2_int = converthashtoint(phash2)
    dhash2_int = converthashtoint(dhash2)

    # Hamming distance difference
    phash_diff = bin(phash1_int ^ phash2_int).count('1')
    dhash_diff = bin(dhash1_int ^ dhash2_int).count('1') 

    # print hamming distance
    if (phash_diff == 0 and dhash_diff == 0):
        print("Both hashes are equal")
    else:
        print("Phash diff: " + str(phash_diff) + ", image1: " + str(phash1) + ", image2: " + str(phash2))
        print("Dhash diff: " + str(dhash_diff) + ", image1: " + str(dhash1) + ", image2: " + str(dhash2))

    # max distance for same is that least one is 0 and second is max 3

    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    else:
        return False

def isidentical(img1, img2):
    shaimg1 = hashlib.sha1()
    shaimg1.update(img1.tobytes())
    digest1 = shaimg1.digest()

    shaimg2 = hashlib.sha1()
    shaimg2.update(img2.tobytes())
    digest2 = shaimg2.digest()

    print("digest1: " + shaimg1.hexdigest() + " digest2: " + shaimg2.hexdigest())
    
    if (digest1 == digest2):
        return True
    return False

def convert_tiff_to_jpg(tiff_image):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fp:
        tiff_image.convert('RGB').save(fp, "JPEG", quality=95)
    return fp.name    

# note: commons at least once has thrown error due to client policy?
# "Client Error: Forbidden. Please comply with the User-Agent policy"
# keep an eye out for problems..
def downloadimage(url):
    headers={'User-Agent': 'pywikibot'}
    # Image.open(urllib.request.urlopen(url, headers=headers))

    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
                            
    return Image.open(io.BytesIO(response.content))

# get pages immediately under cat
# and upto depth of 1 in subcats
def getcatpages(pywikibot, commonssite, maincat, recurse=False):
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(commonssite.categorymembers(cat))

    # no recursion by default, just get into depth of 1
    if (recurse == True):
        subcats = list(cat.subcategories())
        for subcat in subcats:
            subpages = commonssite.categorymembers(subcat)
            for subpage in subpages:
                pages.append(subpage)

    return pages

# ------- main()

commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Files from the Antellin kokoelma")

#cat = pywikibot.Category(commonssite, "Category:Kuvasiskot")
#pages = site.categorymembers(cat)

rowcount = 1
rowlimit = 10

for page in pages:
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    file_page = pywikibot.FilePage(page)
    if file_page.isRedirectPage():
        continue
        
    file_info = file_page.latest_file_info

    # Check only low resolution images
    if file_info.width > 2000 or file_info.height > 2000:
        print("Skipping " + page.title() + ", width or height over 2000")
        continue

    print(page.title())

    # Find ids used in Finna
    finna_ids=get_finna_ids(page)
    
    # Skip if there is no known ids
    if not finna_ids:
        print("Skipping " + page.title() + " (no known finna ID)")
        continue

    for finna_id in finna_ids:
        finna_record = get_finna_record(finna_id)

        if (finna_record['status'] != 'OK'):
            print("Skipping (status not OK): " + finnaid + " status: " + finna_record['status'])
            continue

        if (finna_record['resultCount'] != 1):
            print("Skipping (result not 1): " + finnaid + " count: " + str(finna_record['resultCount']))
            continue

        # collections: expecting ['Historian kuvakokoelma', 'Studio Kuvasiskojen kokoelma']
        # skip coins in "Antellin kokoelma" as hashes will be too similar
        finna_collections = finna_record['records'][0]['collections']
        if ("Antellin kokoelma" in finna_collections):
            print("Skipping collection (can't match by hash due similarities): " + finna_id)
            continue

        imagesExtended=finna_record['records'][0]['imagesExtended'][0]

        # Test copyright
        if imagesExtended['rights']['copyright'] != "CC BY 4.0":
            print("Incorrect copyright: " + imagesExtended['rights']['copyright'])
            continue

        # Confirm that images are same using imagehash

        finna_thumbnail_url="https://finna.fi" + imagesExtended['urls']['small']
        commons_thumbnail_url=file_page.get_file_url(url_width=500)

        # check here that download works, 
        # also try to reuse without downloading multiple times
        finna_thumb = downloadimage(finna_thumbnail_url)
        commons_thumb = downloadimage(commons_thumbnail_url)

        # Test if image is same using similarity hashing
        # default hashlength is 16, try comparison with increased length as well?
        if not is_same_image(finna_thumb, commons_thumb):
            print("Not same image, skipping: " + finna_id)
            continue

        hires = imagesExtended['highResolution']['original'][0]

        # verify finna image really is in better resolution than what is in commons
        # before uploading
        finnawidth = hires['data']['width']['value']
        finnaheight = hires['data']['height']['value']
        
        if file_info.width > int(finnawidth) or file_info.height > int(finnaheight):
            print("Skipping " + page.title() + ", resolution already higher than finna: " + finnawidth + "x" + finnaheight)
            continue

        # Select which file to upload.
        local_file=False
        if hires["format"] == "tif" and file_info.mime == 'image/tiff':
            image_file_name = hires['url']
        elif hires["format"] == "tif" and file_info.mime == 'image/jpeg':
            print("converting image from tiff to jpeg") # log it
            local_image = downloadimage(hires['url'])
            image_file_name = convert_tiff_to_jpg(local_image)
            local_file=True    
        elif hires["format"] == "jpg" and file_info.mime == 'image/jpeg':
            image_file_name = hires['url']
        elif file_info.mime == 'image/jpeg':
            image_file_name = "https://finna.fi" +  imagesExtended['urls']['large']
        else:
            print("Exit: Unhandled mime-type")
            print(f"File format Commons (MIME type): {file_info.mime}")
            print(f"File format Finna (MIME type): {hires['format']}")
            continue

        # can't upload if identical to the one in commons:
        # compare hash of converted image if necessary,
        # otherwise get full image for both (not thumbnails)
        #if (local_file == False):
            #finna_image = downloadimage(image_file_name)
        #commons_image = downloadimage(commons_thumbnail_url)
        #if (isidentical(image_file_name, commons_image) == True):
            #print("Images are identical files, skipping: " + finna_id)
            #continue

        finna_record_url = "https://finna.fi/Record/" + finna_id
        comment = "Overwriting image with better resolution version of the image from " + finna_record_url +" ; Licence in Finna " + imagesExtended['rights']['copyright']
        print(comment)

        # Ignore warnigs = True because we update files
        file_page.upload(image_file_name, comment=comment,ignore_warnings=True)
        if local_file:
            os.unlink(image_file_name)

        # don't try too many at once
        if (rowcount >= rowlimit):
            print("Limit reached")
            exit(1)
            break
        rowcount += 1

