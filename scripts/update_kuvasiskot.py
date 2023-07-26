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

# if there's garbage in id, strip to where it ends
def leftfrom(string, char):
    index = string.find(char)
    if (index > 0):
        return string[:index]

    return string

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
                # avoid duplicates and those we are blocked from modifying (403 error)
                if subpage not in pages and isblockedimage(linked_page) == False:
                    pages.append(subpage)

    return pages

# check for list of images we are forbidden from changing (403 error)
def isblockedimage(page):
    pagename = str(page)
    if (pagename.find("Dubrovnik Lounge & Lobby") >= 0):
        return True
    if (pagename.find("Tuohipallo eli Rapapalli eli Meätshä.jpg") >= 0):
        return True
        
    # conversion from tiff is borked somehow -> avoid uploading for now
    if (pagename.find("Synnytyslaitoksen rakennus Tampereella.jpg") >= 0):
        return True

    return False

def getlinkedpages(pywikibot, commonssite):
    listpage = pywikibot.Page(commonssite, 'user:FinnaUploadBot/filelist')  # The page you're interested in

    pages = list()
    # Get all linked pages from the page
    for linked_page in listpage.linkedPages():
        # avoid duplicates and those we are blocked from modifying (403 error)
        if linked_page not in pages and isblockedimage(linked_page) == False: 
            pages.append(linked_page)

    return pages

# ------- main()

commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Files from the Antellin kokoelma")

#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)
pages = getlinkedpages(pywikibot, commonssite)

#rowcount = 1
#rowlimit = 100

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

    print(" -- [ " + page.title() + " ] --")

    # Find ids used in Finna
    finna_ids=get_finna_ids(page)
    
    # Skip if there is no known ids
    if not finna_ids:
        print("Skipping " + page.title() + " (no known finna ID)")
        continue

    for finnaid in finna_ids:

        if (finnaid.find("?") > 0 or finnaid.find("&") > 0 or finnaid.find("<") > 0 or finnaid.find("#") > 0):
            print("WARN: finna id in " + page.title() + " has unexpected characters, bug or garbage in url? ")
            
            # strip pointless parts if any
            finnaid = leftfrom(finnaid, "<")
            finnaid = leftfrom(finnaid, "?")
            finnaid = leftfrom(finnaid, "&")
            finnaid = leftfrom(finnaid, "#")
    
        finna_record = get_finna_record(finnaid)

        if (finna_record['status'] != 'OK'):
            print("Skipping (status not OK): " + finnaid + " status: " + finna_record['status'])
            continue

        if (finna_record['resultCount'] != 1):
            print("Skipping (result not 1): " + finnaid + " count: " + str(finna_record['resultCount']))
            continue

        if "records" not in finna_record:
            print("WARN: 'records' not found in finna record, skipping: " + finnaid)
            continue
        if (len(finna_record['records']) == 0):
            print("WARN: empty array of 'records' for finna record, skipping: " + finnaid)
            continue
        if "collections" not in finna_record['records'][0]:
            print("WARN: 'collections' not found in finna record, skipping: " + finnaid)
            continue

        # collections: expecting ['Historian kuvakokoelma', 'Studio Kuvasiskojen kokoelma']
        # skip coins in "Antellin kokoelma" as hashes will be too similar
        finna_collections = finna_record['records'][0]['collections']
        if ("Antellin kokoelma" in finna_collections):
            print("Skipping collection (can't match by hash due similarities): " + finnaid)
            continue

        if "imagesExtended" not in finna_record['records'][0]:
            print("WARN: 'imagesExtended' not found in finna record, skipping: " + finnaid)
            continue

        imagesExtended = finna_record['records'][0]['imagesExtended'][0]

        # Test copyright (old field: rights, but request has imageRights?)
        # imageRights = finna_record['records'][0]['imageRights']
        if imagesExtended['rights']['copyright'] != "CC BY 4.0":
            print("Incorrect copyright: " + imagesExtended['rights']['copyright'])
            continue

        finna_image_url = ""
        need_index = False
        match_found = False
        # 'images' can have array of multiple images, need to select correct one
        # -> loop through them (they should have just different &index= in them)
        # and compare with the image in commons
        imageList = finna_record['records'][0]['images']
        if (len(imageList) == 0):
            print("no images for item")

        if (len(imageList) == 1):
            # get image from commons for comparison
            commons_thumbnail_url = file_page.get_file_url(url_width=500)
            commons_thumb = downloadimage(commons_thumbnail_url)
        
            finna_thumbnail_url = "https://finna.fi" + imagesExtended['urls']['small']
            finna_thumb = downloadimage(finna_thumbnail_url)
            
            # Test if image is same using similarity hashing
            if (is_same_image(finna_thumb, commons_thumb) == True):
                match_found = True
                finna_image_url = "https://finna.fi" + imagesExtended['urls']['large']
                #finna_image = downloadimage(finna_image_url)

                # get full image for further comparison
                commons_image_url = file_page.get_file_url()
                commons_image = downloadimage(commons_image_url)

        if (len(imageList) > 1):
            # multiple images in finna related to same item -> 
            # need to pick the one that is closest match
            print("Multiple images for same item: " + str(len(imageList)))

            # get image from commons for comparison:
            # try to use same size
            commons_image_url = file_page.get_file_url()
            commons_image = downloadimage(commons_image_url)
            
            f_imgindex = 0
            for img in imageList:
                finna_image_url = "https://finna.fi" + img
                finna_image = downloadimage(finna_image_url)

                # Test if image is same using similarity hashing
                if (is_same_image(finna_image, commons_image) == True):
                    match_found = True
                    need_index = True
                    print("Matching image index: " + str(f_imgindex))
                    break
                else:
                    f_imgindex = f_imgindex + 1

        if (match_found == False):
            print("No matching image found, skipping: " + finnaid)
            continue

        print("Matching image found: " + finnaid)
        finna_record_url = "https://finna.fi/Record/" + finnaid

        # note! 'original' might point to different image than used above! different server in some cases
        hires = imagesExtended['highResolution']

        # there is at least one case where this is not available?
        if "original" not in hires:
            print("WARN: 'original' not found in hires image, skipping: " + finnaid)
            continue
        hires = imagesExtended['highResolution']['original'][0]

        if "data" not in hires:
            print("WARN: 'data' not found in hires image, skipping: " + finnaid)
            continue
        if "width" not in hires['data'] or "height" not in hires['data']:
            print("WARN: 'width' or 'height' not found in hires-data for image, skipping: " + finnaid)
            continue

        # verify finna image really is in better resolution than what is in commons
        # before uploading
        finnawidth = hires['data']['width']['value']
        finnaheight = hires['data']['height']['value']
        
        if file_info.width >= int(finnawidth) or file_info.height >= int(finnaheight):
            print("Skipping " + page.title() + ", resolution already equal or higher than finna: " + finnawidth + "x" + finnaheight)
            continue

        # Select which file to upload.
        # Note! 'url' might point to different server than any other url in same data!
        # -> it might be somehow different image then as well (see 'original' above)
        local_file=False
        if hires["format"] == "tif" and file_info.mime == 'image/tiff':
            if (need_index == False):
                finna_image_url = hires['url']
        elif hires["format"] == "tif" and file_info.mime == 'image/jpeg':
            print("converting image from tiff to jpeg") # log it
            if (need_index == False):
                finna_image_url = hires['url']
            local_image = downloadimage(finna_image_url)
            image_file_name = convert_tiff_to_jpg(local_image)
            local_file=True    
        elif hires["format"] == "jpg" and file_info.mime == 'image/jpeg':
            if (need_index == False):
                finna_image_url = hires['url']
        elif file_info.mime == 'image/jpeg':
            if (need_index == False):
                finna_image_url = "https://finna.fi" +  imagesExtended['urls']['large']
        else:
            print("Exit: Unhandled mime-type")
            print(f"File format Commons (MIME type): {file_info.mime}")
            print(f"File format Finna (MIME type): {hires['format']}")
            continue

        # can't upload if identical to the one in commons:
        # compare hash of converted image if necessary,
        # need to compare full image for both (not thumbnails)
        if (local_file == False):
            # get full image before trying to upload:
            # code above might have switched to another
            # from multiple different images
            local_image = downloadimage(finna_image_url)
            if (isidentical(local_image, commons_image) == True):
                print("Images are identical files, skipping: " + finnaid)
                continue
        else:
            converted_image = Image.open(image_file_name)
            if (isidentical(converted_image, commons_image) == True):
                print("Images are identical files, skipping: " + finnaid)
                continue

        comment = "Overwriting image with better resolution version of the image from " + finna_record_url +" ; Licence in Finna " + imagesExtended['rights']['copyright']
        print(comment)

        # Ignore warnigs = True because we update files
        if (local_file == False):
            print("uploading from url: " + finna_image_url)
            file_page.upload(finna_image_url, comment=comment,ignore_warnings=True)
        if (local_file == True):
            print("uploading converted local file ")
            file_page.upload(image_file_name, comment=comment,ignore_warnings=True)
            os.unlink(image_file_name)

        # don't try too many at once
        #if (rowcount >= rowlimit):
        #    print("Limit reached")
        #    exit(1)
        #    break
        #rowcount += 1

