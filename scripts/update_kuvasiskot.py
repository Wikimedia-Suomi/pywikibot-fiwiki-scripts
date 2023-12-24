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

# note: finna API query id and finna metapage id need different quoting:
# https://www.finna.fi/Record/sls.%25C3%2596TA+335_%25C3%2596TA+335+foto+81
# https://api.finna.fi/v1/record?id=sls.%25C3%2596TA%2B335_%25C3%2596TA%2B335%2Bfoto%2B81&lng=fi&prettyPrint=1

def get_finna_record(finnaid, quoteid=True):
    if (finnaid.startswith("fmp.") == True and finnaid.find("%2F") > 0):
        quoteid = False

    if (finnaid.find("/") > 0):
        quoteid = True
    
    if (quoteid == True):
        quotedfinnaid = urllib.parse.quote_plus(finnaid)
    else:
        quotedfinnaid = finnaid

    if (finnaid.find("+") > 0):
        quotedfinnaid = finnaid.replace("+", "%2B")

    #print("DEBUG: using quoted id ", quotedfinnaid, " for id ", finnaid)

    url="https://api.finna.fi/v1/record?id=" +  quotedfinnaid
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
        return None

# Check if license from Finna is something
# that is also supported in Commons.
def isSupportedFinnaLicense(copyrightlicense):
    if (copyrightlicense == "CC BY 4.0" 
        or copyrightlicense == "CC BY-SA 4.0"
        or copyrightlicense == "PDM" 
        or copyrightlicense == "CC0"):
        return True
    return False

# simple checks if received record could be usable
def isFinnaRecordOk(finnarecord, finnaid):
    if (finnarecord == None):
        print("WARN: failed to retrieve finna record for: " + finnaid)
        return False

    if (finnarecord['status'] != 'OK'):
        print("WARN: status not OK: " + finnaid + " status: " + finnarecord['status'])
        return False

    if (finnarecord['resultCount'] != 1):
        print("WARN: resultCount not 1: " + finnaid + " count: " + str(finnarecord['resultCount']))
        return False

    if "records" not in finnarecord:
        print("WARN: 'records' not found in finna record: " + finnaid)
        return False

    if (len(finnarecord['records']) == 0):
        print("WARN: empty array of 'records' for finna record: " + finnaid)
        return False

    return True

# helper to check in case of malformed json
def getImagesExtended(finnarecord):
    if "imagesExtended" not in finnarecord['records'][0]:
        return None

    # some records are broken?
    imagesExtended = finnarecord['records'][0]['imagesExtended']
    if (len(imagesExtended) == 0):
        return None

    # at least one entry exists
    return imagesExtended[0]

# try to determine if image is copyrighted:
# note the comments, this can get complicated..
def determineCopyrightStatus(finnarecord):
    if (finnarecord == None):
        # can't determine -> safer to assume it is
        # Q50423863
        return True
    
    imagesExtended = getImagesExtended(finnarecord)
    if (imagesExtended == None):
        # can't determine -> safer to assume it is
        # Q50423863
        return True

    copyrightlicense = imagesExtended['rights']['copyright']
    if (copyrightlicense == "PDM"):
        # not copyrighted: copyright has been waived by releasing into PD
        return False
    
    # otherwise.. it's complicated, we need to know when it was taken,
    # if it is artwork or not, is the photographer alive and if not for long..
    # -> safer to just assume it is
    # Q50423863
    return True

# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
#
def getimagehash(img, hashlen=8):
    phash = imagehash.phash(img, hash_size=hashlen)
    dhash = imagehash.dhash(img, hash_size=hashlen)
    return tuple((hashlen, str(phash), str(dhash)))

# convert string to base 16 integer for calculating difference
#def converthashtoint(h, base=16):
#    return int(h, base)

# distance of hashes (count of bits that are different)
def gethashdiff(hint1, hint2):
    return bin(hint1 ^ hint2).count('1')

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
def is_same_image(img1, img2, hashlen=8):

    phash1 = imagehash.phash(img1, hash_size=hashlen)
    dhash1 = imagehash.dhash(img1, hash_size=hashlen)
    phash1_int = converthashtoint(phash1)
    dhash1_int = converthashtoint(dhash1)

    phash2 = imagehash.phash(img2, hash_size=hashlen)
    dhash2 = imagehash.dhash(img2, hash_size=hashlen)
    phash2_int = converthashtoint(phash2)
    dhash2_int = converthashtoint(dhash2)

    if (phash1_int == 0 or dhash1_int == 0 or phash2_int == 0 or dhash2_int == 0):
        print("WARN: zero hash detected, file was not read correctly?")
        return False

    # Hamming distance difference
    phash_diff = gethashdiff(phash1_int, phash2_int)
    dhash_diff = gethashdiff(dhash1_int, dhash2_int)

    # print hamming distance
    if (phash_diff == 0 and dhash_diff == 0):
        print("Both images have equal hashes, phash: " + str(phash1) + ", dhash: " + str(dhash1))
    else:
        print("Phash diff: " + str(phash_diff) + ", image1: " + str(phash1) + ", image2: " + str(phash2))
        print("Dhash diff: " + str(dhash_diff) + ", image1: " + str(dhash1) + ", image2: " + str(dhash2))

    # max distance for same is that least one is 0 and second is max 3
    
    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    elif (phash_diff + dhash_diff) <= 8:
        return True
    else:
        return False

# if image is identical (not just similar) after conversion (avoid reupload)
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
    # if image is CMYK/grayscale ("L") might work or not,
    # might have to abort/use different method with ImageCms module ?
    # if it is signed 32-bit int ("I") often does not work..
    bands = tiff_image.getbands()
    if (len(bands) == 1 and bands[0] == "I"):
        print("DEBUG: single-band, might not be supported", bands[0])
        #return None
    print("DEBUG: image bands", tiff_image.getbands())
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fp:
        tiff_image.convert('RGB').save(fp, "JPEG", quality=100)
    return fp.name    

def convert_tiff_to_png(tiff_image):
    # if image is CMYK/grayscale ("L") might work or not,
    # might have to abort/use different method with ImageCms module ?
    # if it is signed 32-bit int ("I") often does not work..
    bands = tiff_image.getbands()
    if (len(bands) == 1 and bands[0] == "I"):
        print("DEBUG: single-band, might not be supported", bands[0])
        #return None
    print("DEBUG: image bands", tiff_image.getbands())

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fp:
        tiff_image.convert('RGB').save(fp, "PNG", quality=100)
    return fp.name    

def convert_tiff_to_gif(tiff_image):
    # if image is CMYK/grayscale ("L") might work or not,
    # might have to abort/use different method with ImageCms module ?
    # if it is signed 32-bit int ("I") often does not work..
    bands = tiff_image.getbands()
    if (len(bands) == 1 and bands[0] == "I"):
        print("DEBUG: single-band, might not be supported", bands[0])
        #return None
    print("DEBUG: image bands", tiff_image.getbands())

    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as fp:
        tiff_image.convert('RGB').save(fp, "GIF", quality=100)
    return fp.name    

# note: commons at least once has thrown error due to client policy?
# "Client Error: Forbidden. Please comply with the User-Agent policy"
# keep an eye out for problems..
def downloadimage(url):
    headers={'User-Agent': 'pywikibot'}
    # Image.open(urllib.request.urlopen(url, headers=headers))

    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
                            
    if (len(response.content) < 50):
        print("ERROR: less than 50 bytes for image")
        return None

    f = io.BytesIO(response.content)
    if (f.readable() == False or f.closed == True):
        print("ERROR: can't read image from stream")
        return None

    return Image.open(f)

# strip id from other things that may be after it:
# there might be part of url or some html in same field..
def stripid(oldsource):
    # space after url?
    indexend = oldsource.find(" ")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some other text after url?
    indexend = oldsource.find(",")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find(")")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # html tag after url?
    indexend = oldsource.find("<")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find(">")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # wikimarkup after url?
    indexend = oldsource.find("[")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("]")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("{")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("}")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("|")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("*")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("&")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("#")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("?")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # linefeed at end?
    if (oldsource.endswith("\n")):
        oldsource = oldsource[:len(oldsource)-1]

    return oldsource

# if there's garbage in id, strip to where it ends
def leftfrom(string, char):
    index = string.find(char)
    if (index > 0):
        return string[:index]

    return string

def isSupportedMimetype(strmime):
    if (strmime.find("audio") >= 0 
        or strmime.find("ogg") >= 0 
        or strmime.find("/svg") >= 0 
        or strmime.find("/pdf") >= 0 
        or strmime.find("image/vnd.djvu") >= 0
        or strmime.find("video") >= 0):
        return False
    return True

# check for list of images we are forbidden from changing (403 error)
def isblockedimage(page):
    pagename = str(page)

    # timeout all the time..
    if (pagename.find("Sonkajärven kivikirkko") >= 0):
        return True

    # Python throws error due to large size of the image.
    # We can only skip it for now..
    if (pagename.find("Sotavirkailija Kari Suomalainen.jpg") >= 0):
        return True 
    
    # if there is svg file for some reason -> skip it
    if (pagename.find(".svg") >= 0):
        return True
    if (pagename.find(".pdf") >= 0):
        return True

    # commons scales down and size comparison fails -> skip this for now
    if (pagename.find("Bronze age socketed axes from Finland.jpg") >= 0):
        return True
    # upload ends up being smaller than original somehow -> skip this
    if (pagename.find("Suomineito.jpg") >= 0):
        return True

    # 403 forbidden when uploading new version
    if (pagename.find("Dubrovnik Lounge & Lobby") >= 0):
        return True
    if (pagename.find("Tuohipallo eli Rapapalli eli Meätshä.jpg") >= 0):
        return True
    if (pagename.find("Fanny Flodin-Gustavson + Ida Flodin.jpg") >= 0):
        return True
        
    if (pagename.find("Aapeli-Liisi-Kivioja-1909.jpg") >= 0 ):
        return True
        
    # conversion from tiff is borked somehow -> avoid uploading for now
    # (python does not handle floating point format in some tiffs correctly?)
    if (pagename.find("Synnytyslaitoksen rakennus Tampereella.jpg") >= 0):
        return True
    
    if (pagename.find("Vilho Penttilä, Kansallis-Osake-Pankin talo, Kauppakatu 4, Tampere.jpg") >= 0):
        return True
    
    # another image where conversion fails, we detect it before upload though
    ##if (pagename.find("Itäinen Viertotie 24. (Hämeentie) jossa toimi Alli Trygg-Heleniuksen Kansankoti") >= 0):

    # close but not close enough
    if (pagename.find("Western Finnish student guard.jpg") >= 0):
        return True

    # uploaded and cropped        
    if (pagename.find("Ernst-Lindelof.jpg") >= 0):
        return True
    if (pagename.find("Bengt-Schalin.jpg") >= 0):
        return True
    if (pagename.find("EAchté c.1890s.jpg") >= 0):
        return True
    if (pagename.find("AOjanperä 1895.jpg") >= 0):
        return True
    if (pagename.find("Aino Öljymäki (1901–1963), Finnish teacher and singer.jpg") >= 0):
        return True
    if (pagename.find("A. F. Granfelt.jpg") >= 0):
        return True


    # copy upload not allowed
    if (pagename.find("Putsaaren piilokirkko") >= 0):
        return True

    return False

# get pages immediately under cat
# and upto depth of 1 in subcats
def getcatpages(pywikibot, commonssite, maincat, recurse=False):
    final_pages = list()
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(commonssite.categorymembers(cat))
    
    for page in pages:
        if isblockedimage(page) == False:
            if page not in final_pages:
                final_pages.append(page)

    # no recursion by default, just get into depth of 1
    if (recurse == True):
        subcats = list(cat.subcategories())
        for subcat in subcats:
            subpages = commonssite.categorymembers(subcat)
            for subpage in subpages:
                # avoid duplicates and those we are blocked from modifying (403 error)
                if isblockedimage(subpage) == False:
                    if subpage not in pages:
                        final_pages.append(subpage)

    return final_pages

# recurse upto given depth:
# 0 for no recursion (only those directly in category)
# 1 is for one level on subcats
# 2 is for two levels and so on
def getpagesrecurse(pywikibot, commonssite, maincat, depth=1):
    #final_pages = list()
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(cat.articles(recurse=depth))
    return pages

# list of pages with links listed in a page 
def getlinkedpages(pywikibot, commonssite, linkpage):
    listpage = pywikibot.Page(commonssite, linkpage)  # The page you're interested in

    pages = list()
    # Get all linked pages from the page
    for linked_page in listpage.linkedPages():
        # avoid duplicates and those we are blocked from modifying (403 error)
        if isblockedimage(linked_page) == False: 
            if linked_page not in pages:
                pages.append(linked_page)

    return pages

# just catch exceptions
def getfilepage(pywikibot, page):
    try:
        return pywikibot.FilePage(page)
    except:
        print("WARN: failed to retrieve filepage: " + page.title())

    return None


# ------- main()

commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki")
#pages = getcatpages(pywikibot, commonssite, "Category:Landscape architects")
#pages = getcatpages(pywikibot, commonssite, "Files from the Antellin kokoelma")

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Simo Rista", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Daniel Nyblin", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Alli Nissinen")
#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Daniel Nyblin", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Pekka Kyytinen")

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Carl Jacob Gardberg", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical pictures of Vyborg Castle")

#pages = getcatpages(pywikibot, commonssite, "Category:Drummers from Finland", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", True)
#pages = getcatpages(pywikibot, commonssite, "Category:People of Finland by year", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Archaeology in Finland")
#pages = getcatpages(pywikibot, commonssite, "Category:Painters from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Winter War", True)

#pages = getcatpages(pywikibot, commonssite, "Category:History of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Aviation Museum")

#pages = getcatpages(pywikibot, commonssite, "Category:SA-kuva", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Lotta Svärd", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Vyborg by decade", 2)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Vyborg")

#pages = getcatpages(pywikibot, commonssite, "Category:Monuments and memorials in Helsinki", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Karl Emil Ståhlberg")
#pages = getcatpages(pywikibot, commonssite, "Category:Photographers from Finland", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:People of Finland by occupation", 2)

#pages = getcatpages(pywikibot, commonssite, "Category:Industrialists from Finland")
#pages = getcatpages(pywikibot, commonssite, "Category:Architects from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Artists from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Musicians from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Composers from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Conductors from Finland", True)

#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Jean Sibelius", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Arvid Järnefelt", 2)

#pages = getcatpages(pywikibot, commonssite, "Category:Alli Trygg-Helenius")
#pages = getcatpages(pywikibot, commonssite, "Category:Eva Kuhlefelt-Ekelund", True)

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist2')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/sakuvat')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/europeana-kuvat')

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp1')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp3')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp4')

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filesfromip')

#pages = getcatpages(pywikibot, commonssite, "Category:Nakkila church", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Finnish Agriculture (1899) by I. K. Inha")

#pages = getcatpages(pywikibot, commonssite, "Category:Kauppakatu (Tampere)")

#pages = getcatpages(pywikibot, commonssite, "Category:Finland in the 1930s")
#pages = getcatpages(pywikibot, commonssite, "Category:Britta Wikström")

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Carl Jacob Gardberg", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Photographs by Paavo Poutiainen", 1)

#pages = getcatpages(pywikibot, commonssite, "Black and white photographs of Finland in the 1950s")
#pages = getcatpages(pywikibot, commonssite, "Black and white photographs of Finland in the 1930s")


pages = getcatpages(pywikibot, commonssite, "Paavo Cajander")


rowcount = 0
#rowlimit = 100

print("Pages found: " + str(len(pages)))

for page in pages:
    rowcount = rowcount +1
    
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    # try to catch exceptions and return later
    file_page = getfilepage(pywikibot, page)
    if (file_page == None):
        continue

    if file_page.isRedirectPage():
        continue

    print(" -- ", rowcount, "/", len(pages), " [ " + page.title() + " ] --")
        
    file_info = file_page.latest_file_info
    
    # there may be other media than images as well
    strmime = str(file_info.mime)
    if (isSupportedMimetype(strmime) == False):
        print("unsupported mime-type: ", strmime, "page:", page.title())
        continue

    # Check only low resolution images
    if file_info.width > 2000 or file_info.height > 2000:
        print("Skipping " + page.title() + ", width or height over 2000")
        continue

    # Find ids used in Finna
    finna_ids=get_finna_ids(page)
    
    # Skip if there is no known ids
    if not finna_ids:
        print("Skipping " + page.title() + " (no known finna ID)")
        continue

    for finnaid in finna_ids:

        if (finnaid.find("?") > 0 or finnaid.find("&") > 0 or finnaid.find("<") > 0 or finnaid.find(">") > 0 or finnaid.find("#") > 0 or finnaid.find("[") > 0 or finnaid.find("]") > 0 or finnaid.find("{") > 0 or finnaid.find("}") > 0 or finnaid.find(")") > 0):
            print("WARN: finna id in " + page.title() + " has unexpected characters, bug or garbage in url? ")
            
            # strip pointless parts if any
            finnaid = stripid(finnaid)
            print("note: finna id in " + page.title() + " is " + finnaid)

        # if redirector -> skip it: some other host that won't have same API to ask data from..
        if (finnaid.find("profium.com") > 0):
            print("WARN: unusable url (redirector) in: " + page.title() + ", id: " + finnaid)
            continue

        # try to fetch metadata with finna API    
        finna_record = get_finna_record(finnaid)
        if (isFinnaRecordOk(finna_record, finnaid) == False):
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

        # TODO! Python throws error if image is larger than 178956970 pixels
        # so we can't handle really large images. Check for those and skip them..


        # use helper to check that it is correctly formed
        imagesExtended = getImagesExtended(finna_record)
        if (imagesExtended == None):
            print("WARN: 'imagesExtended' not found in finna record, skipping: " + finnaid)
            continue

        # Test copyright (old field: rights, but request has imageRights?)
        # imageRights = finna_record['records'][0]['imageRights']
        # should be CC BY 4.0 or Public domain
        copyrightlicense = imagesExtended['rights']['copyright']
        if (isSupportedFinnaLicense(copyrightlicense) == False):
            print("Incorrect copyright: " + copyrightlicense)
            continue

        finna_image_url = ""
        need_index = False
        match_found = False
        
        # there is at least one case where this is not available?
        # -> save from further comparison by checking early
        if "original" not in imagesExtended['highResolution']:
            print("WARN: 'original' not found in hires image, skipping: " + finnaid)
            continue

        # get image from commons for comparison:
        # try to use same size
        commons_image_url = file_page.get_file_url()
        commons_image = downloadimage(commons_image_url)
        if (commons_image == None):
            print("WARN: Failed to download commons-image: " + page.title() )
            continue
        
        # 'images' can have array of multiple images, need to select correct one
        # -> loop through them (they should have just different &index= in them)
        # and compare with the image in commons
        imageList = finna_record['records'][0]['images']
        if (len(imageList) == 0):
            print("no images for item")

        if (len(imageList) == 1):
        
            finna_image_url = "https://finna.fi" + imagesExtended['urls']['large']
            finna_image = downloadimage(finna_image_url)
            if (finna_image == None):
                print("WARN: Failed to download finna-image: " + page.title() )
                continue
            
            # Test if image is same using similarity hashing
            if (is_same_image(finna_image, commons_image) == True):
                match_found = True

        if (len(imageList) > 1):
            # multiple images in finna related to same item -> 
            # need to pick the one that is closest match
            print("Multiple images for same item: " + str(len(imageList)))

            f_imgindex = 0
            for img in imageList:
                finna_image_url = "https://finna.fi" + img
                finna_image = downloadimage(finna_image_url)
                if (finna_image == None):
                    print("WARN: Failed to download finna-image: " + page.title() )
                    continue

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
            
        # TODO: try to use the one from "imagesExtended"
        # (see logic after this)
        hires = imagesExtended['highResolution']['original'][0]

        # TODO: compare with "original" (whatever that is)
        #hiresurl = imagesExtended['highResolution']['original'][0]['url']

        if "data" not in hires:
            print("WARN: 'data' not found in hires image, skipping: " + finnaid)
            continue
        
        # some images don't have size information in the API..
        if "width" not in hires['data'] or "height" not in hires['data']:
            print("WARN: 'width' or 'height' not found in hires-data for image, id: " + finnaid + ", image is: " + str(finna_image.width) + "x" + str(finna_image.height))
            
            # try to use from image instead?
            #finnawidth = finna_image.width
            #finnaheight = finna_image.height
            
            # it seems sizes might be missing when image is upscaled and not "original"?
            # -> verify this
            # -> skip image for now
            continue
        else:
            # verify finna image really is in better resolution than what is in commons
            # before uploading
            finnawidth = int(hires['data']['width']['value'])
            finnaheight = int(hires['data']['height']['value'])
        
        if file_info.width >= finnawidth or file_info.height >= finnaheight:
            print("Skipping " + page.title() + ", resolution already equal or higher than finna: " + str(finnawidth) + "x" + str(finnaheight))
            continue
        #print("DEBUG: Resolution for " + page.title() + " in finna: " + str(finnawidth) + "x" + str(finnaheight) + " old: " + str(file_info.width) + "x" + str(file_info.height))

        if "format" not in hires:
            print("WARN: 'format' not found in hires image, skipping: " + finnaid)
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
            if (local_image == None):
                print("WARN: Failed to download finna-image: " + page.title() )
                continue
            image_file_name = convert_tiff_to_jpg(local_image)
            local_file=True    
        elif hires["format"] == "tif" and file_info.mime == 'image/png':
            print("converting image from tiff to png") # log it
            if (need_index == False):
                finna_image_url = hires['url']
            local_image = downloadimage(finna_image_url)
            if (local_image == None):
                print("WARN: Failed to download finna-image: " + page.title() )
                continue
            image_file_name = convert_tiff_to_png(local_image)
            local_file=True    
        #elif hires["format"] == "tif" and file_info.mime == 'image/gif':
            #print("converting image from tiff to gif") # log it
            #if (need_index == False):
                #finna_image_url = hires['url']
            #local_image = downloadimage(finna_image_url)
            #if (local_image == None):
                #print("WARN: Failed to download finna-image: " + page.title() )
                #continue
            #image_file_name = convert_tiff_to_gif(local_image)
            #local_file=True    
        elif hires["format"] == "jpg" and file_info.mime == 'image/jpeg':
            if (need_index == False):
                finna_image_url = hires['url']
        elif file_info.mime == 'image/jpeg':
            if (need_index == False):
                # this is already same from earlier -> we can remove this
                finna_image_url = "https://finna.fi" + imagesExtended['urls']['large']
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
            if (local_image == None):
                print("WARN: Failed to download finna-image: " + page.title() )
                continue
            # if image is identical by sha-hash -> commons won't allow again
            if (isidentical(local_image, commons_image) == True):
                print("Images are identical files, skipping: " + finnaid)
                continue
                
            # verify that the image we have picked above is the same as in earlier step:
            # internal consistency of the API has an error?
            if (is_same_image(local_image, finna_image) == False):
                print("WARN: Images are NOT same in the API! " + finnaid)
                print("DEBUG: image bands", local_image.getbands())
                continue
            
            # verify if file in commons is still larger?
            # metadata in finna is wrong or server sending wrong image?
            if commons_image.width >= local_image.width or commons_image.height >= local_image.height:
                print("WARN: image in Finna is not larger than in Commons: " + finnaid)
                continue

        else:
            converted_image = Image.open(image_file_name)
            # if image is identical by sha-hash -> commons won't allow again
            if (isidentical(converted_image, commons_image) == True):
                print("Images are identical files, skipping: " + finnaid)
                continue
            # at least one image fails in conversion, see if there are others
            if (is_same_image(converted_image, commons_image) == False):
                print("ERROR! Images are NOT same after conversion! " + finnaid)
                print("DEBUG: image bands", local_image.getbands())
                continue

            # after conversion, file in commons is still larger?
            # conversion routine is borked or other error?
            if file_info.width >= converted_image.width or file_info.height >= converted_image.height:
                print("WARN: converted image is not larger than in Commons: " + finnaid)
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

