# Purpose: add structured data to pictures from finna
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
from urllib.request import urlopen

import urllib.parse

import re
import urllib
import requests
import hashlib
import imagehash
import io
import os
import tempfile
from PIL import Image

from datetime import datetime
from datetime import timedelta
from datetime import timezone

#from http.client import InvalidURL
#import HTTPException

import urllib3
#import sqlite3
import psycopg2

# ----- FinnaData

#class FinnaData:
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

def append_finna_api_parameters(url):

    url += finna_api_parameter('field[]', 'id')
    url += finna_api_parameter('field[]', 'title')
    url += finna_api_parameter('field[]', 'subTitle')
    url += finna_api_parameter('field[]', 'alternativeTitles')
    url += finna_api_parameter('field[]', 'shortTitle')
    url += finna_api_parameter('field[]', 'titleSection')
    url += finna_api_parameter('field[]', 'titleStatement')
    url += finna_api_parameter('field[]', 'uniformTitles')
    url += finna_api_parameter('field[]', 'summary')
    url += finna_api_parameter('field[]', 'imageRights')
    url += finna_api_parameter('field[]', 'images')
    url += finna_api_parameter('field[]', 'imagesExtended')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'openUrl')
    url += finna_api_parameter('field[]', 'nonPresenterAuthors')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'subjects')
    url += finna_api_parameter('field[]', 'subjectsExtendet')
    url += finna_api_parameter('field[]', 'subjectPlaces')
    url += finna_api_parameter('field[]', 'subjectActors')
    url += finna_api_parameter('field[]', 'subjectDetails')
    url += finna_api_parameter('field[]', 'geoLocations')
    url += finna_api_parameter('field[]', 'buildings')
    url += finna_api_parameter('field[]', 'identifierString')
    url += finna_api_parameter('field[]', 'collections')
    url += finna_api_parameter('field[]', 'institutions')
    url += finna_api_parameter('field[]', 'classifications')
    url += finna_api_parameter('field[]', 'events')
    url += finna_api_parameter('field[]', 'languages')
    url += finna_api_parameter('field[]', 'originalLanguages')
    url += finna_api_parameter('field[]', 'year')
    url += finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url += finna_api_parameter('field[]', 'formats')
    url += finna_api_parameter('field[]', 'physicalDescriptions')
    url += finna_api_parameter('field[]', 'physicalLocations')
    url += finna_api_parameter('field[]', 'measurements')
    url += finna_api_parameter('field[]', 'recordLinks')
    url += finna_api_parameter('field[]', 'recordPage')
    url += finna_api_parameter('field[]', 'systemDetails')
    url += finna_api_parameter('field[]', 'fullRecord')
    return url

# note: finna API query id and finna metapage id need different quoting:
# https://www.finna.fi/Record/sls.%25C3%2596TA+335_%25C3%2596TA+335+foto+81
# https://api.finna.fi/v1/record?id=sls.%25C3%2596TA%2B335_%25C3%2596TA%2B335%2Bfoto%2B81&lng=fi&prettyPrint=1

# note: if there is already %25 don't add it again
# OK: sls.%25C3%2596TA%2B112_ota112-9_foto_01536
# ERROR: sls.%2525C3%252596TA%252B112_ota112-9_foto_01536

def get_finna_record(finnaid, quoteid=True):
    finnaid = trimlr(finnaid)
    if (finnaid.startswith("fmp.") == True and finnaid.find("%2F") > 0):
        quoteid = False
    # already quoted, don't mangle again
    if (finnaid.startswith("sls.") == True and finnaid.find("%25") > 0):
        quoteid = False
    if (finnaid.startswith("fng_simberg.") == True and (finnaid.find("%25") > 0 or finnaid.find("%C3") > 0)):
        quoteid = False

    if (finnaid.find("/") > 0):
        quoteid = True
    
    if (quoteid == True):
        print("DEBUG: quoting id:", finnaid)
        quotedfinnaid = urllib.parse.quote_plus(finnaid)
    else:
        quotedfinnaid = finnaid
        print("DEBUG: skipping quoting id:", finnaid)

    if (quotedfinnaid.find("Ö") > 0):
        quotedfinnaid = quotedfinnaid.replace("Ö", "%C3%96")
        #quotedfinnaid = quotedfinnaid.replace("Ö", "%25C3%2596")
        #quotedfinnaid = urllib.parse.quote_plus(quotedfinnaid)

    if (quotedfinnaid.find("å") > 0):
        quotedfinnaid = quotedfinnaid.replace("å", "%C3%A5")

    if (quotedfinnaid.find("+") > 0):
        quotedfinnaid = quotedfinnaid.replace("+", "%2B")
        
    print("DEBUG: fetching record with id:", quotedfinnaid, ", for id:", finnaid)

    url ="https://api.finna.fi/v1/record?id=" +  quotedfinnaid
    url = append_finna_api_parameters(url)

    try:
        response = requests.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        return None

# ----- /FinnaData

# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html
#
def getimagehash(img, hashlen=8):
    print("DEBUG: hashing.. ")

    # average hash
    # ahash generates a lot of false positives ?
    #ahash = imagehash.average_hash(img, hash_size=hashlen) # mean=numpy.mean
    #print("DEBUG: ahash", str(ahash))

    # perceptual hash
    phash = imagehash.phash(img, hash_size=hashlen) # highfreq_factor=4
    print("DEBUG: phash", str(phash))

    # difference hash
    dhash = imagehash.dhash(img, hash_size=hashlen) # no other parameters
    print("DEBUG: dhash", str(dhash))

    # wavelet hash
    #whash = imagehash.whash(img, hash_size=hashlen) # image_scale=None, mode='haar', remove_max_haar_ll=True
    #print("DEBUG: whash", str(whash))

    # color hash
    #chash = imagehash.colorhash(img) # no other parameters
    #print("DEBUG: chash", str(chash))
    
    # crop-resistant hash
    #crhash = imagehash.crop_resistant_hash(img) # 
    #print("DEBUG: crhash", str(crhash))

    ## Note : ahash, dhash and whash all give zeroes when pillow has failed handling tiff-file
    # -> could use to detect failure as well

    # image download has failed or python is broken?
    if ('8000000000000000' == str(phash) or'0000000000000000' == str(dhash)):
        return None
    return tuple((hashlen, str(phash), str(dhash)))

# convert string to base 16 integer for calculating difference
def converthashtoint(h, base=16):
    return int(h, base)

# distance of hashes (count of bits that are different)
def gethashdiff(hint1, hint2):
    return bin(hint1 ^ hint2).count('1')

# Compares if the image is same using similarity hashing
# method is to convert images to 64bit integers and then
# calculate hamming distance. 
#
def is_same_image(imghash1, imghash2):
    
    # check that hash lengths are same
    if (imghash1['phashlen'] != imghash2['phashlen'] or imghash1['dhashlen'] != imghash2['dhashlen']):
        print("WARN: Hash length mismatch")
        return False

    phash_int1 = converthashtoint(imghash1['phashval'])
    dhash_int1 = converthashtoint(imghash1['dhashval'])

    phash_int2 = converthashtoint(imghash2['phashval'])
    dhash_int2 = converthashtoint(imghash2['dhashval'])

    if (phash_int1 == 0 or dhash_int1 == 0 or phash_int2 == 0 or dhash_int2 == 0):
        print("WARN: zero hash detected, file was not read correctly?")
        return False

    # Hamming distance difference (from integers)
    phash_diff = gethashdiff(phash_int1, phash_int2)
    dhash_diff = gethashdiff(dhash_int1, dhash_int2)

    # print hamming distance
    if (phash_diff == 0 and dhash_diff == 0):
        print("Both images have equal hashes, phash: " + imghash1['phashval'] + ", dhash: " + imghash1['dhashval'])
    else:
        print("Phash diff: " + str(phash_diff) + ", image1: " + imghash1['phashval'] + ", image2: " + imghash2['phashval'])
        print("Dhash diff: " + str(dhash_diff) + ", image1: " + imghash1['dhashval'] + ", image2: " + imghash2['dhashval'])

    # max distance for same is that least one is 0 and second is max 3

    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    elif (phash_diff + dhash_diff) <= 8:
        return True
    else:
        return False

# old method, need to convert to using above for simplicity
def is_same_image_old(img1, img2, hashlen=8):

    phash1 = imagehash.phash(img1, hash_size=hashlen)
    dhash1 = imagehash.dhash(img1, hash_size=hashlen)
    phash1_int = converthashtoint(str(phash1))
    dhash1_int = converthashtoint(str(dhash1))

    phash2 = imagehash.phash(img2, hash_size=hashlen)
    dhash2 = imagehash.dhash(img2, hash_size=hashlen)
    phash2_int = converthashtoint(str(phash2))
    dhash2_int = converthashtoint(str(dhash2))

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

    bio = io.BytesIO(response.content)
    if (bio.readable() == False or bio.closed == True):
        print("ERROR: can't read image from stream")
        return None
    if (bio.getbuffer().nbytes < 100):
        print("ERROR: less than 100 bytes in buffer")
        return None
    
    # need to seek(0, 2) for eof first?
    #if (bio.tell() < 100):
        #print("ERROR: tell less than 100 bytes in buffer")
        #return None
    #if (sys.getsizeof(bio) < 100):
        #print("ERROR: sys less than 100 bytes in buffer")
        #return None
    
    return Image.open(bio)

# ----- CachedImageData
class CachedImageData:
    def opencachedb(self):
        # created if it doesn't yet exist
        #self.conn = sqlite3.connect("pwbimagedatacache.db")
        self.conn = psycopg2.connect("dbname=wikidb")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS imagecache(url varchar(500), phashlen integer, phashval varchar(50), dhashlen integer, dhashval varchar(50), recent timestamp, pillowbug char(1))")

    def addtocache(self, url, plen, pval, dlen, dval, ts, pillowbugstate='n'):

        sqlq = "INSERT INTO imagecache(url, phashlen, phashval, dhashlen, dhashval, recent, pillowbug) VALUES ('"+ url + "', "+ str(plen) + ", '"+ pval + "', "+ str(dlen) + ", '"+ dval + "', '" + ts.isoformat() + "', '"+ pillowbugstate +"')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def updatecache(self, url, plen, pval, dlen, dval, ts, pillowbugstate='n'):

        sqlq = "UPDATE imagecache SET phashlen = "+ str(plen) + ", phashval = '"+ pval + "', dhashlen = "+ str(dlen) + ", dhashval = '"+ dval + "', recent = '" + ts.isoformat() + "', pillowbug = '" + pillowbugstate + "' WHERE url = '" + url + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def addtocachewithpillowbug(self, url, ts, pillowbugstate='y'):

        sqlq = "INSERT INTO imagecache(url, recent, pillowbug) VALUES ('"+ url + "', '" + ts.isoformat() + "', '"+ pillowbugstate +"')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def setpillowbug(self, url, pillowbugstate, ts):
        
        sqlq = "UPDATE imagecache SET pillowbug = '"+ pillowbugstate + "', recent = '" + ts.isoformat() + "' WHERE url = '" + url + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findfromcache(self, url):
        sqlq = "SELECT url, phashlen, phashval, dhashlen, dhashval, recent, pillowbug FROM imagecache WHERE url = '" + url + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        #if (res == None):
            #print("DEBUG: no result for query")
            #return None
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['url'] = row[0]
            if (row[1] != None):
                dt['phashlen'] = int(row[1])
            else:
                dt['phashlen'] = 0
            dt['phashval'] = row[2]
            if (row[3] != None):
                dt['dhashlen'] = int(row[3])
            else:
                dt['dhashlen'] = 0
            dt['dhashval'] = row[4]
            dt['timestamp'] = datetime.fromisoformat(str(row[5]))
            dt['pillowbug'] = row[6]
            #print(dt)
            return dt

        return None

    def addorupdate(self, url, plen, pval, dlen, dval, ts):
        tp = self.findfromcache(url)
        if (tp == None):
            self.addtocache(url, plen, pval, dlen, dval, ts)
        else:
            self.updatecache(url, plen, pval, dlen, dval, ts)

# ----- /CachedImageData

# ----- CachedMediainfo
# cache some media info from Commons
class CachedMediainfo:
    def opencachedb(self):
        # created if it doesn't yet exist
        #self.conn = sqlite3.connect("pwbmediainfocache.db")
        self.conn = psycopg2.connect("dbname=wikidb")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS mediainfocache(mediaid integer, recent timestamp)")

    def addtocache(self, mediaid, ts):

        sqlq = "INSERT INTO mediainfocache(mediaid, recent) VALUES ('" + str(mediaid) + "', '" + ts.isoformat() + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def updatecache(self, mediaid, ts):

        sqlq = "UPDATE mediainfocache SET recent = '" + ts.isoformat() + "' WHERE mediaid = '" + str(mediaid) + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findfromcache(self, mediaid):
        sqlq = "SELECT mediaid, recent FROM mediainfocache WHERE mediaid = '" + str(mediaid) + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        #if (res == None):
            #print("DEBUG: no result for query")
            #return None
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['mediaid'] = row[0]
            dt['recent'] = datetime.fromisoformat(str(row[1]))
            #print(dt)
            return dt

        return None

    def addorupdate(self, mediaid, ts):
        tp = self.findfromcache(mediaid)
        if (tp == None):
            self.addtocache(mediaid, ts)
        else:
            self.updatecache(mediaid, ts)

# ----- /CachedMediainfo

# -------- CachedFngData
class CachedFngData:
    def opencachedb(self):
        # created if it doesn't yet exist
        #self.conn = sqlite3.connect("pwbfngcache.db")
        self.conn = psycopg2.connect("dbname=wikidb")
        cur = self.conn.cursor()
        #cur.execute("CREATE TABLE IF NOT EXISTS fngcache(objectid, invnum)")
        cur.execute("CREATE TABLE IF NOT EXISTS fngcache(objectid integer, invnum varchar(250))")

    def addtocache(self, objectid, invnum):

        sqlq = "INSERT INTO fngcache(objectid, invnum) VALUES ('"+ str(objectid) + "', '"+ str(invnum) + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findbyid(self, objectid):
        if (objectid == None):
            return None
        sqlq = "SELECT objectid, invnum FROM fngcache WHERE objectid = '" + str(objectid) + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        #if (res == None):
            #print("DEBUG: no result for query")
            #return None
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['objectid'] = row[0]
            dt['invnum'] = row[1]
            #print(dt)
            return dt

        return None

    def findbyacc(self, invnum):
        if (invnum == None):
            return None
        sqlq = "SELECT objectid, invnum FROM fngcache WHERE invnum = '" + str(invnum) + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        #if (res == None):
            # 
            #print("DEBUG: no result for query")
            #return None
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['objectid'] = row[0]
            dt['invnum'] = row[1]
            #print(dt)
            return dt

        return None

# ----- /CachedFngData


# ----- CommonsMediaInfo
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

    except pywikibot.data.api.APIError as e:
        print('Got an error from the API, the following request were made:')
        print(request)
        print('Error: {}'.format(e))
      
    return False

def wbGetEntity(site, media_identifier):
    #media_identifier = 'M' + str(wd_item_id)
    #print(media_identifier)
    
    # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M62891762
    
    #mediawiki_api_url='https://www.wikidata.org/w/api.php'
    mediawiki_api_url='https://commons.wikimedia.org/w/api.php'
    
    max_retries=10
    retry_after=10
    headers = {
        'User-Agent': 'pywikibot'
    }
    
    params = {
        'action': 'wbgetentities',
        #'sites': 'enwiki',
        'ids': media_identifier,
        'format': 'json'
    }

    request = site.simple_request(**params)
    for n in range(max_retries):
        try:
            
            #method="GET"
            response = request.submit()
            
        except requests.exceptions.ConnectionError as e:
            print("Connection error: {}. Sleeping for {} seconds.".format(e, retry_after))
            time.sleep(retry_after)
            continue
        
        #if 'success' in response:

        if 'error' not in response:
            return response
    return ''


def wbEditEntity(site, media_identifier, data):
    csrf_token = site.tokens['csrf']
    # payload documentation
    # https://www.wikidata.org/w/api.php?action=help&modules=wbeditentity
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
        return True

    except pywikibot.data.api.APIError as e:
        print('Got an error from the API, the following request were made:')
        print(request)
        print('Error: {}'.format(e))

    return False

def addSdcCaption(commons_site, media_identifier, caption, lang='fi'):
    captions={}
    captions[lang] = {u'language' : lang, 'value' : caption }
    data={ u'labels' : captions}
    return wbEditEntity(commons_site, media_identifier, data)

def addSdcMimetype(commons_site, media_identifier, mimetype):
    # 
    #property='P180' # P180 = Depicts
    property='P1163' # mime type
    value={'entity-type':'item','id': mimetype } # Antoinia Toini
    return createMediainfoClaim(commons_site, media_identifier, property, value)

# is there caption in commons for the item yet
def isSdcCaption(commons_site, media_identifier, lang='fi'):
    data = wbGetEntity(commons_site, media_identifier)
    if 'success' not in data:
        return False
    if 'entities' not in data:
        return False
    if len(data['entities']) == 0:
        return False
    for k, v in data['entities'].items():
        for k2, v2 in v.items():
            if (k2 == "labels"):
                if lang in v2:
                    print("found captions :", v2[lang])
                    return True
    return False
    

# ----- /CommonsMediaInfo


# ----- FinnaTimestamp
class FinnaTimestamp:
    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0
        self.maybe_normalized = False
        self.precision = 0

    # 1 for year, 10 for decade, 100 for century..
    def setPrecision(self, precision):
        self.precision = precision

    def setYear(self, year, normalized = False):
        self.year = year
        self.month = 0
        self.day = 0
        self.maybe_normalized = normalized
        self.precision = 1
        
    def setYearMonth(self, year, month):
        self.year = year
        self.month = month
        self.day = 0
        self.precision = -1

    def setDate(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
        self.precision = -2

# ----- /FinnaTimestamp


# ----- KansallisgalleriaData
class KansallisgalleriaData:
    def __init__(self):
        self.invnum = None
        self.teostun = None
        self.qcode = None
        
    def setInventaarionumero(self, invnum):
        self.invnum = invnum
        
    def setTeostunniste(self, teostun):
        self.teostun = teostun

    def setQcode(self, Qcode):
        self.qcode = Qcode
    
    def isValidInventaarionumero(self):
        if (self.invnum != None and len(self.invnum) > 0):
            return True
        return False

    def isValidTeostunniste(self):
        if (self.teostun != None and len(self.teostun) > 0):
            return True
        return False

    def isValidQcode(self):
        if (self.qcode != None and len(self.qcode) > 0):
            return True
        return False

# ----- /KansallisgalleriaData


# strip id from other things that may be after it:
# there might be part of url or some html in same field..
def stripid(oldsource):
    # space after url?
    indexend = oldsource.find(" ")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some other text after url?
    # TODO: sometimes comma is part of ID, sometimes not..
    #indexend = oldsource.find(",")
    indexend = oldsource.find(", ")
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

# link might have "?id=<id>" which we handle here, might have:
# - "/Cover/Show?id="
# - "/Record/DownloadFile?id="
def getlinksourceid(oldsource):
    strlen = len("id=")
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return ""
    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)

# for: "Record/<id>" 
def getrecordid(oldsource):
    # not suitable here, use getlinksourceid()
    indexid = oldsource.find("/Record/DownloadFile")
    if (indexid > 0):
        return ""
    
    strlen = len("/Record/")
    indexid = oldsource.find("/Record/")
    if (indexid < 0):
        return ""
    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)

# commons source information
def findurlbeginfromsource(source, begin):
    # just skip it
    if (len(source) == 0):
        return -1
    
    indexend = len(source)-1
    indexbegin = begin
    while (indexbegin < indexend):
        # may have http or https,
        # also there may be encoded url given to 
        # redirecting services as parameters
        # 
        index = source.find("http", indexbegin)
        if (index < 0):
            # no url proto in string
            return -1

        if ((indexend - index) < 8):
            # nothing usable remaining in string, partial url left unfinished?
            return -1

        # should have http:// or https:// to be valid:
        # check that we have :// since url may given as encoded parameter to another
        if (source[index:index+7].lower() == "http://" 
            or source[index:index+8].lower() == "https://"):
            # should be usable url?
            return index
            
        # otherwise look for another
        indexbegin = index + 7

    # not found
    return -1

# commons source may have human readable stuff in it,
# it may be mixed with wiki-markup and html as well:
# try to locate where url ends from that soup
def findurlendfromsource(source, indexbegin=0):
    #print("DEBUG: source is: [" + source + "]")
    
    indexend = len(source)

    i = indexbegin
    while i < indexend:
        # space after url or between url and description
        if (source[i] == " " and i < indexend):
            indexend = i
            
        # wikimarkup after url?
        # end of url markup?
        if (source[i] == "]" and i < indexend):
            indexend = i
        # template parameter after url?
        if (source[i] == "|" and i < indexend):
            indexend = i
        # end of template with url in it?
        if (source[i] == "}" and i < indexend):
            indexend = i
        # start of template after url?
        if (source[i] == "{" and i < indexend):
            indexend = i

        # html after url?
        if (source[i] == "<" and i < indexend):
            indexend = i

        # some human-readable text after url?
        if (source[i] == "," and i < indexend):
            indexend = i
        if (source[i] == ")" and i < indexend):
            indexend = i

        # just newline after url
        if (source[i] == "\n" and i < indexend):
            indexend = i
        i += 1

    #print("DEBUG: source has url: [" + source[indexbegin:indexend] + "]")
    return indexend

# commons source may have human readable stuff in it,
# also may have multiple urls (old and new),
# parse to plain urls
def geturlsfromsource(source):
    #print("DEBUG: source is: " + source)
    
    urllist = list()
    index = 0
    while (index >= 0 and index < len(source)):
        index = findurlbeginfromsource(source, index)
        if (index < 0):
            break
            
        indexend = findurlendfromsource(source, index)
        url = source[index:indexend]
        print("DEBUG: source has url: " + url)
        urllist.append(url)
        index = indexend

    #print("DEBUG: urllist: ", urllist)
    return urllist

# input: kuvakokoelmat.fi url
# output: old format id
def getkuvakokoelmatidfromurl(source):
    indexlast = source.rfind("/", 0, len(source)-1)
    if (indexlast < 0):
        # no separator found?
        print("invalid url: " + source)
        return ""
    kkid = source[indexlast+1:]
    if (kkid.endswith("\n")):
        kkid = kkid[:len(kkid)-1]

    # .jpg or something at end? remove from id
    indexlast = kkid.rfind(".", 0, len(source)-1)
    if (indexlast > 0):
        # if the part after dot is a number -> leave it
        remainder = kkid[indexlast+1:]
        if (remainder.isnumeric() == False):
            # note: in some cases there maybe be a file extension, 
            # but also there may be a part of the ID in some cases..
            if (remainder.lower() == "jpg" or remainder.lower() == "jpeg"
                or remainder.lower() == "png" or remainder.lower() == "tiff" or remainder.lower() == "tif"):
                # if it is image type extension -> remove it (not part of ID)
                kkid = kkid[:indexlast]
    return kkid

# just for documentation purposes
def getidfromeuropeanaurl(source):
    if (source.find("europeana.eu") < 0):
        # not found?
        return ""

    mid = getkuvakokoelmatidfromurl(source)
    if (len(mid) > 0):
        # urls may have session/tracking parameters in some cases -> remove trash from end
        mid = stripid(mid)
    
    # should be like M012_HK10000_944
    # note: in some cases with multiple underscores last on should be changed to dash
    # such as in HK19321130:115-1877
    # otherwise underscore to colon works
    if (len(mid) > 0 and mid.startswith("M012")):
        mid = mid.replace("_", ":")
        #musketti = "musketti." + mid[:index] + ":" + mid[index+1:]
        musketti = "musketti." + mid
        return musketti
    return "" # failed parsing

def getidfromeuropeana(source):
    eusource = parsesourcefromeuropeana(srcvalue)
    if (len(eusource) < 0):
        print("Failed to retrieve source from europeana")
        return "" # failed to parse, don't add anything

    # museovirasto.finna.fi or museovirasto.<id>
    if (eusource.find("museovirasto") > 0 or eusource.find("finna") > 0):
        # ok, we might use this as-is
        indexrec = eusource.find("/Record/")
        if (indexrec >= 0):
            indexrec = indexrec + len("/Record/")
            newid = eusource[indexrec:]
            newid = stripid(newid)
            print("Found finna id from europeana: " + newid)
            return newid
    
    # if url has musketti-id: europeana.eu/%/M012..
    mid = getidfromeuropeanaurl(srcvalue)
    if (len(mid) <= 0):
        return "" # failed to parse, don't add anything
    print("DEBUG: europeana-link had id: " + mid)
    return mid

# parse inventory number from old-style link
# http://kokoelmat.fng.fi/app?si=A-1995-96
# http://kokoelmat.fng.fi/app?si=A+I+223
def getfngaccessionnumberfromurl(source):
    if (source.find("fng.fi") < 0):
        print("invalid url: " + source)
        return ""

    strlen = len("si=")
    indexid = source.find("si=")
    if (indexid < 0):
        return ""

    source = source[indexid+strlen:]
    source = stripid(source)
    
    # replace + with spaces etc.
    source = urllib.parse.unquote(source)
    source = source.replace("-", " ")
    source = source.replace("+", " ")
    print("DEBUG: accession number from fng-url: " + source)
    return source

# parse objectid from new-style link
# https://www.kansallisgalleria.fi/en/object/624337
def getkansallisgalleriaidfromurl(source):
    if (source.find("kansallisgalleria.fi") < 0):
        print("invalid url: " + source)
        return ""

    strlen = len("/object/")
    indexid = source.find("/object/")
    if (indexid < 0):
        return ""
    source = source[indexid+strlen:]
    
    # result should be plain number
    if (source.endswith("\n")):
        source = source[:len(source)-1]
    if (source.endswith(".")):
        source = source[:len(source)-1]
    # check for some other potential characters
    return stripid(source)

# input: old format "HK"-id, e.g. HK7155:219-65-1
# output: newer "musketti"-id, e.g. musketti.M012%3AHK7155:219-65-1
def convertkuvakokoelmatid(kkid):
    if (len(kkid) == 0):
        print("empty kuvakokoelmat id ")
        return ""

    # verify
    if (kkid.startswith("HK") == False and kkid.startswith("JOKA") == False
        and kkid.startswith("SUK") == False and kkid.startswith("SMK") == False 
        and kkid.startswith("KK") == False and kkid.startswith("VKK") == False 
        and kkid.startswith("1") == False):
        print("does not start appropriately: " + kkid)
        return ""

    if (kkid.startswith("HK") == True):
        index = kkid.find("_")
        if (index < 0):
            print("no underscores: " + kkid)
            return ""
        # one underscore to colon
        # underscores to dash
        # add prefix
        kkid = kkid[:index] + ":" + kkid[index+1:]
        kkid = kkid.replace("_", "-")

    if (kkid.startswith("JOKA") == True):
        # if there is one underscore -> set to colon
        #kkid = kkid.replace("_", ":")
        # if there is two -> only set the latter one to colon and leave first as underscore
        indexlast = kkid.rfind("_", 0, len(kkid)-1)
        if (indexlast > 0):
            kkid = kkid[:indexlast] + ":" + kkid[indexlast+1:]

    if (kkid.startswith("SUK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("SMK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("KK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("VKK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("1") == True):
        kkid = "HK" + kkid
        kkid = kkid.replace("_", ":")

    # url may have something else in it -> remove it
    kkid = leftfrom(kkid, "#")

    musketti = "musketti.M012:" + kkid
    return musketti

# if there's garbage in id, strip to where it ends
def leftfrom(string, char):
    index = string.find(char)
    if (index > 0):
        return string[:index]

    return string

# remove pre- and post-whitespaces when mwparser leaves them
def trimlr(string):
    string = string.lstrip()
    string = string.rstrip()
    return string

# parse Q-code from link
def getqcodefromwikidatalink(target):
    targetqcode = str(target)
    index = targetqcode.find(":")
    if (index < 0):
        return ""
    indexend = targetqcode.find("]", index)
    if (indexend < 0):
        return ""
    targetqcode = targetqcode[index+1:indexend]
    return targetqcode
    
# parse claims or statements from commons SDC
def getcollectiontargetqcode(statements, collectionsqcodes):
    if "P195" not in statements:
        return collectionsqcodes
    
    claimlist = statements["P195"]
    for claim in claimlist:
        # target is expected to be like: [[wikidata:Q118976025]]
        target = claim.getTarget()

        # parse Q-code from link
        targetqcode = getqcodefromwikidatalink(target)

        # no need to add if SDC-data already has a target
        # -> remove from collections to add
        if (targetqcode in collectionsqcodes):
            collectionsqcodes.remove(targetqcode)

        # TODO: finish comparison to wikidata:
        # -might belong to multiple collections -> multiple entries
        # -might have something that isn't in finna list
        # -might be missing something that is in finna list -> should add to commons SDC
        #if (target not in collections):
        # claim.removetarget..

        #dataitem = pywikibot.ItemPage(wikidata_site, "Q118976025")
        # check item, might belong to multiple collections -> compare to list from finna

    # debug
    #print("final collections are: " + str(collections))

    # return list of those to be added
    return collectionsqcodes

# add collection qcode to sdc data
def addcollectiontostatements(pywikibot, wikidata_site, collection):
    # property ID for "collection"
    coll_claim = pywikibot.Claim(wikidata_site, 'P195')
    qualifier_targetcoll = pywikibot.ItemPage(wikidata_site, collection)
    coll_claim.setTarget(qualifier_targetcoll)
    return coll_claim

# helper to find publisher information in statements
def isQcodeInClaimQualifiers(claim, qcode, prop):
    if prop not in claim.qualifiers:
        return False

    foiquali = claim.qualifiers[prop]
    #print("DEBUG: quali:", str(foiquali), "in prop:", prop)
    for fclaim in foiquali:
        ftarget = fclaim.getTarget()
        fqcode = getqcodefromwikidatalink(ftarget)
        if (fqcode == qcode):
            #print("DEBUG: qcode found: " + fqcode)
            return True
    return False

# check if publisher exists in data
def ispublisherinstatements(statements, publisherqcode):
    if "P7482" not in statements: # P7482 is source of file
        #print("source of file not found")
        return False
    
    publisherFound = False
    claimlist = statements["P7482"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q74228490"): # file available on internet
            #print("not available on internet") # DEBUG
            continue
        
        # publisher:
        # kansalliskirjasto, merimuseo, valokuvataiteen museo.. jne.
        publisherFound = isQcodeInClaimQualifiers(claim, publisherqcode, "P123")

    #print("did not find publisherqcode: " + str(publisherqcode))
    return publisherFound

def isoperatorinstatements(statements, operatorqcode):
    if "P7482" not in statements: # P7482 is source of file
        #print("source of file not found")
        return False
    
    operatorFound = False
    claimlist = statements["P7482"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q74228490"): # file available on internet
            #print("not available on internet") # DEBUG
            continue
        
        # some pictures have been imported and marked as being from flickr
        # but when same picture is in Finna we want to mark that as well
        # "P137" is operator
        # "P973" is described at url

        # check: is source flick or finna or something else?
        # if operator == Q103204 -> flickr
        # if operator == Q420747 -> Kansalliskirjasto
        # if operator == Q11895148 -> Suomen valokuvataiteen museo

        # operator:
        # museovirasto, kansallisgalleria (eri domain?), flickr..
        operatorFound = isQcodeInClaimQualifiers(claim, operatorqcode, "P137")

    #print("did not find operatorqcode: " + str(operatorqcode))
    return operatorFound

def issourceurlinstatements(statements, descurl):
    if "P7482" not in statements: # P7482 is source of file
        #print("source of file not found")
        return False
    
    descFound = False
    claimlist = statements["P7482"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q74228490"): # file available on internet
            #print("not available on internet") # DEBUG
            continue

        # url has no q-code, just plain url
        #descFound = isQcodeInClaimQualifiers(claim, descurl, "P973")
        if "P973" in claim.qualifiers:
            foiquali = claim.qualifiers["P973"]
            for fclaim in foiquali:
                ftarget = fclaim.getTarget()
                targettxt = str(ftarget)
                if (targettxt == descurl):
                    descFound = True
                    #print("DEBUG: target match found:", str(targettxt))

    #print("did not find descurl: " + str(descurl))
    return descFound

# add:
# - source of file (finna url)
# - operator ("National Library of Finland")
# - publisher ("Finnish Heritage Agency")
def addsourceoperatorpublisher(pywikibot, wikidata_site, operatorqcode, publisherqcode, sourceurl):
        
    # P7482 "source of file" 
    item_internet = pywikibot.ItemPage(wikidata_site, 'Q74228490')  # file available on the internet
    source_claim = pywikibot.Claim(wikidata_site, "P7482") # property ID for "source of file"
    source_claim.setTarget(item_internet)

    # P973 "described at URL"
    qualifier_url = pywikibot.Claim(wikidata_site, 'P973')  # property ID for "described at URL"
    qualifier_url.setTarget(sourceurl)
    source_claim.addQualifier(qualifier_url, summary='Adding described at URL qualifier')

    # P137 "operator"
    if (len(operatorqcode) > 0):
        qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')  # property ID for "operator"
        qualifier_targetop = pywikibot.ItemPage(wikidata_site, operatorqcode)  # National Library of Finland (Kansalliskirjasto)
        qualifier_operator.setTarget(qualifier_targetop)
        source_claim.addQualifier(qualifier_operator, summary='Adding operator qualifier')

    # P123 "publisher"
    if (len(publisherqcode) > 0):
        # Q3029524 Finnish Heritage Agency (Museovirasto)
        qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')  # property ID for "publisher"
        qualifier_targetpub = pywikibot.ItemPage(wikidata_site, publisherqcode)  # Finnish Heritage Agency (Museovirasto)
        qualifier_publisher.setTarget(qualifier_targetpub)
        source_claim.addQualifier(qualifier_publisher, summary='Adding publisher qualifier')

    return source_claim

def checksourceoperatorpublisher(pywikibot, wikidata_site, statements, operatorqcode, publisherqcode, sourceurl):
    if "P7482" not in statements:
        print("source of file property not in statements")
        return None

    source_found = False
    found_operator = False
    found_publisher = False
    
    claimlist = statements["P7482"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q74228490"): # file available on internet
            #print("not available on internet") # DEBUG
            continue

        print("file source found")
        #print(" sources: ", claim.getSources())
        #print(" qualifiers: ", claim.qualifiers)
        
        # "P7482"
        #  -> "Q74228490"
        #  -> "P973", url

        # check for url in qualifiers
        if "P973" in claim.qualifiers:
            foiquali = claim.qualifiers["P973"]
            #print("DEBUG: quali:", str(foiquali), "in prop:", prop)
            for fclaim in foiquali:
                ftarget = fclaim.getTarget()
                if (ftarget == sourceurl):
                    source_found = True
                    print("exact source url for file found")

    
        sourcelist = claim.getSources()
        for source in sourcelist:
            for key, value in source.items():
                if key == "P973":
                    for v in value: # v is another claim..
                        vtarget = v.getTarget()
                        if (vtarget == sourceurl):
                            source_found = True
                            print("source url found")

        if (len(operatorqcode) > 0):
            found_operator = isQcodeInClaimQualifiers(claim, operatorqcode, "P137")
        if (len(publisherqcode) > 0):
            found_publisher = isQcodeInClaimQualifiers(claim, publisherqcode, "P123")

        if (found_operator == False and len(operatorqcode) > 0):
            print("adding operator to source")
            op_claim = pywikibot.Claim(wikidata_site, 'P137', is_reference=False, is_qualifier=True)
            q_targetop = pywikibot.ItemPage(wikidata_site, operatorqcode)
            op_claim.setTarget(q_targetop)
            claim.addQualifier(op_claim)
            print("added operator to source")
        else:
            print("source already has operator")
            
        if (found_publisher == False and len(publisherqcode) > 0):
            print("adding publisher to source")
            pub_claim = pywikibot.Claim(wikidata_site, 'P123', is_reference=False, is_qualifier=True)
            q_targetpub = pywikibot.ItemPage(wikidata_site, publisherqcode)
            pub_claim.setTarget(q_targetpub)
            claim.addQualifier(pub_claim)
            print("added publisher to source")
        else:
            print("source already has publisher")

        if (source_found == False and len(sourceurl) > 0):
            print("NOTE: should add source url")
            u_claim = pywikibot.Claim(wikidata_site, 'P973', is_reference=False, is_qualifier=True)
            u_claim.setTarget(sourceurl)
            claim.addQualifier(u_claim)
            print("added source url")
        else:
            print("already has source url")
        
    return None

# check if license from Finna is something
# that is also supported in Commons
def isSupportedFinnaLicense(copyrightlicense):
    # CC-BY-SA is also ok in Commons?
    if (copyrightlicense == "CC BY 4.0" 
        or copyrightlicense == "CC BY-SA 4.0"
        or copyrightlicense == "PDM" 
        or copyrightlicense == "CC0"):
        return True
    return False

# from string from Finna to Qcode to wikidata
# CC0: Q6938433
# CC BY 4.0: Q20007257
def getQcodeForLicense(copyrightlicense):
    if (copyrightlicense == "CC0"):
        return "Q6938433"
    if (copyrightlicense == "CC BY 4.0"):
        return "Q20007257"
    if (copyrightlicense == "CC BY-SA 4.0"):
        return "Q18199165"
    
    # "PDM" == Q98592850 ? "tekijänoikeuden omistaja julkaissut public domainiin"?
    # Q88088423 -> status
    # Q98592850 -> license
    
    #if (copyrightlicense == "CC BY-SA"):
        #return "Q6905942"
    #if (copyrightlicense == "CC BY-SA 2.0"):
        #return "Q19068220"
    return ""

# is license in statements
#P275, "CC BY 4.0" is Q20007257
def islicenseinstatements(statements, license):
    if (isSupportedFinnaLicense(license) == False):
        return False
    if "P275" not in statements:
        return False

    # see if our license is already there in SDC
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode == getQcodeForLicense(license)):
            # already set there -> we are fine
            print("found code", targetqcode, "for", license)
            return True
        #else:
            # may have multiple licenses, just ignore (cc by sa/nc..)
            #print("License is NOT as expected, Q-code: " + targetqcode)

    return False

# check for given url in references (sources)
def istargetinsourcelist(claim, key, sourcetocheck):
    sourcelist = claim.getSources()
    for source in sourcelist:
        for key, value in source.items():
            if key == key:
                for v in value: # v is another claim..
                    vtarget = v.getTarget()
                    if (vtarget == sourcetocheck):
                        print("target found in sources:", vtarget)
                        return True
                    else:
                        # note: for now, accept just having a source,
                        # add comparison for domain later
                        #print("DEBUG: target in sources:", vtarget)
                        if (vtarget.find("finna.fi") > 0 and sourcetocheck.find("finna.fi") > 0):
                            return True
                        
    return False

# check if 'P275' is missing 'P854' with reference url
def checklicensesources(pywikibot, wikidata_site, statements, copyrightlicense, sourceurl):
    if "P275" not in statements:
        print("license property not in statements")
        return None

    licqcode = getQcodeForLicense(copyrightlicense)
    if (licqcode == ""):
        return None

    matchfound = False
    
    # note: there may be more than on license per item (not equal)
    # so check source is under appropriate license..
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != licqcode): # not our license
            #print("DEBUG: unsupported license: " + targetqcode)
            continue

        print("license qcode found", licqcode)

        # check for url in qualifiers
        if "P854" in claim.qualifiers:
            foiquali = claim.qualifiers["P854"]
            #print("DEBUG: quali:", str(foiquali), "in prop:", prop)
            for fclaim in foiquali:
                ftarget = fclaim.getTarget()
                if (ftarget == sourceurl):
                    matchfound = True
                    print("exact source url for license found", ftarget)
                    break
                
        # check for url in references (sources)
        if (istargetinsourcelist(claim, "P854", sourceurl) == True):
            matchfound = True
            print("license source found")

        if (matchfound == False):
            print("match not found, adding source url to license")
            u_claim = pywikibot.Claim(wikidata_site, 'P854', is_reference=True, is_qualifier=False)
            u_claim.setTarget(sourceurl)
            claim.addSource(u_claim)
            print("added source url to license")
        else:
            print("license already has source url")
        
    return None

#P275, license
#P854, sourceurl
# Note: only set clearly supported licenses, in other cases
# it might need deeper look at release time, if it is normal photo or artwork and so on.
# So avoid complication and stick to clearly known licenses
def addlicensetostatements(pywikibot, wikidata_site, license, sourceurl):
    # at least PDM and CC0 are be supported in addition to CC BY 4.0.
    if (isSupportedFinnaLicense(license) == False):
        return None
    
    licqcode = getQcodeForLicense(license)
    if (licqcode == ""):
        return None
    
    lic_claim = pywikibot.Claim(wikidata_site, "P275") # property ID for "license"
    qualifier_targetlic = pywikibot.ItemPage(wikidata_site, licqcode)
    lic_claim.setTarget(qualifier_targetlic)
    
    # note: this add qualifer but we want "reference" type
    qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
    qualifier_url.setTarget(sourceurl)
    lic_claim.addSource(qualifier_url, summary='Adding reference URL qualifier')
    # is there "addreference()"?

    # note: commons does not support adding qualifiers to items,
    # you need to add items and qualifiers at same time.

    print("added license to statements")

    return lic_claim

def addCopyrightstatusToSdc(pywikibot, wikidata_site, license, statusqcode, sourceurl):
    if (len(statusqcode) == 0):
        print("DEBUG: empty copyright status")
        return None
    
    # verify we support this license
    if (isSupportedFinnaLicense(license) == False):
        print("DEBUG: not supported license:", license)
        return None

    #P6216 = Q88088423 (copyright status = tekijänoikeuden suojaama, mutta tekijänoikeuden omistaja on asettanut sen public domainiin )
    #P275 = Q98592850 (copyright license = tekijänoikeuden omistaja on julkaissut teoksen public domainiin )

    # PDM or CC0 -> we can determine these
    #if (statusqcode == "Q88088423" or statusqcode == "Q99263261"):

    # not copyrighted: copyright has been waived by releasing into PD
    # tekijänoikeuden suojaama, mutta tekijänoikeuden omistaja on asettanut sen public domainiin
    if (statusqcode != "Q88088423" or license != "PDM"):
        # for now, only mark if it was explicitly waived
        # otherwise it might get complicated..
        print("DEBUG: skipping copyright status:", statusqcode ,"license:", license)
        return None
    if (statusqcode != "Q88088423"):
        print("DEBUG: not supported status:", statusqcode)
        return None
    
    cs_claim = pywikibot.Claim(wikidata_site, "P6216") # property ID for "copyright status"
    qualifier_targetcs = pywikibot.ItemPage(wikidata_site, statusqcode)
    cs_claim.setTarget(qualifier_targetcs)
    
    # note: this add qualifer but we want "reference" type
    qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
    qualifier_url.setTarget(sourceurl)
    cs_claim.addSource(qualifier_url, summary='Adding reference URL qualifier')
    # is there "addreference()"?

    print("DEBUG: adding copyright status:", statusqcode ,"license:", license)
    return cs_claim

# check if same status exists
# there are various complications in determining copyright status,
# only if it has been marked that copyright has been waived we can be confident
def isCopyrightStatusInSDC(statements, statusqcode, sourceurl):
    if (len(statusqcode) == 0):
        #print("DEBUG: no status given")
        return False
    if "P6216" not in statements:
        # no status marked in SDC
        print("DEBUG: no copyright status in SDC")
        return False

    claimlist = statements["P6216"]
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        #if (targetqcode == getQcodeForLicense(license)): # not our license
        if (targetqcode == statusqcode): 
            print("DEBUG: exact status code found:" + targetqcode)
            return True

    # just ignore adding for now, we need more checks that value we've got is usable,
    # see problems related to determining this..
    #print("DEBUG: status exists, ignoring for now")
    return False


def isFinnaIdInStatements(statements, newid):
    if "P9478" not in statements:
        return False
    #print("DEBUG: checking sdc for Finna ID:", newid)

    unquotedNewId = newid.replace("%25", "%")

    # also see if unquoted one matches
    unquotedNewId = urllib.parse.unquote_plus(unquotedNewId)
    # finna-API query needs quoted plus sign, check if target has it or doesn't
    #unquotedNewId = unquotedNewId.replace("%2B", "+")

    #print("DEBUG: looking for finna id from sdc:", newid, unquotedNewId)

    claimlist = statements["P9478"]
    for claim in claimlist:
        # target is expected to be like: "musketti." or "museovirasto."
        # but may be something else (hkm. sibelius. fmp. and so on)
        target = claim.getTarget()
        unquotedTarget = urllib.parse.unquote_plus(target)
        
        #print("DEBUG: target has:", target, unquotedTarget)
        if (target == newid):
            # exact match found: no need to add same ID again
            #print("DEBUG: found Finna-ID", newid)
            return True
        # try to compare with unquoted version(s)
        if (unquotedTarget == unquotedNewId 
            or unquotedTarget == newid 
            or target == unquotedNewId):
            # commons seems to have bug in some character quoting
            # -> try to catch it
            print("NOTE: unquoted target matches unquoted Finna-ID", unquotedTarget)
            return True
        if (newid.startswith("sls.") and target.startswith("sls.")):
            # the quoting is a problem to make work reliably so just skip if there's any sls-ID:
            # there seems to be special rules in commons/wikidata/finna that make it quoting a pain
            print("WARN: SLS-ID found, skip this")
            return True

    # ID not found -> should be added
    #print("DEBUG: did not find finna id from sdc:", newid)
    return False

def addfinnaidtostatements(pywikibot, wikidata_site, finnaid):
    claim_finnaidp = 'P9478'  # property ID for "finna ID"
    finna_claim = pywikibot.Claim(wikidata_site, claim_finnaidp)

    # TODO: sls ID has different quoting rules
    # url might have old style id as quoted -> no need with new id
    finnaunquoted = urllib.parse.unquote(finnaid)
    
    finna_claim.setTarget(finnaunquoted)
    return finna_claim

# pywikibot is bugged in handling conversions from standard formats
# -> brute force it
def getwbdatefromdt(dt):
    #return pywikibot.WbTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    return pywikibot.WbTime(dt.year, dt.month, dt.day)

def isHashvalueInSdcData(statements, prop, hashval):
    if prop not in statements:
        return False

    claimlist = statements[prop]
    for claim in claimlist:
        target = claim.getTarget()
        if (target == hashval):
            # exact match found: no need to add same hash again
            print("hash value match found", hashval)
            return True
    return True # TEST: just skip if there is value, even if it isn't the same
    #return False # check, do we add another if hashes have different length/different value?


# check if perceptual hash exists in sdc data
def isPerceptualHashInSdcData(statements, hashval):
    return isHashvalueInSdcData(statements, "P9310", hashval)

# check if difference hash exists in sdc data
def isDifferenceHashInSdcData(statements, hashval):
    return isHashvalueInSdcData(statements, "P12563", hashval)

# set perceptual hash value to sdc data in commons
def addHashvalueToSdcData(pywikibot, wikidata_site, prop, hashval, hash_methodqcode, comhashtime):

    # note: need "WbTime" which is not a standard datetime
    wbdate = getwbdatefromdt(comhashtime)

    # property ID P9310 for "pHash checksum"
    # property ID P12563 for "dHash checksum"
    p_claim = pywikibot.Claim(wikidata_site, prop)
    p_claim.setTarget(hashval)
    
    # determination method: P459
    # Q104884110 - ImageHash perceptual hash
    # Q124969714 - Imagehash difference hash
    # P348 - software version identifier
    # P571 - inception
    # P2048 - height
    # P2049 - width
    # hashlen?

    det_quali = pywikibot.Claim(wikidata_site, 'P459', is_qualifier=True)  # determination method
    qualifier_targetimagehash = pywikibot.ItemPage(wikidata_site, hash_methodqcode)
    det_quali.setTarget(qualifier_targetimagehash)
    #p_claim.addSource(det_quali, summary='Adding reference URL qualifier')
    p_claim.addQualifier(det_quali, summary='Adding reference URL qualifier')

    i_claim = pywikibot.Claim(wikidata_site, 'P571', is_qualifier=True) # inception time
    i_claim.setTarget(wbdate)
    p_claim.addQualifier(i_claim)

    return p_claim

# set perceptual hash value to sdc data in commons
def addPerceptualHashToSdcData(pywikibot, wikidata_site, hashval, comhashtime):
    return addHashvalueToSdcData(pywikibot, wikidata_site, 'P9310', hashval, "Q104884110", comhashtime)

# set difference hash value to sdc data in commons
def addDifferenceHashToSdcData(pywikibot, wikidata_site, hashval, comhashtime):
    return addHashvalueToSdcData(pywikibot, wikidata_site, 'P12563', hashval, "Q124969714", comhashtime)


# TODO: add missing qualifier to phash/dhash property in sdc data
# for now, just checking if it exists: pywikibot api does not really support this with SDC data
# -> need another way as usual
def checkHashvalueInSdcData(pywikibot, wikidata_site, statements, prop, hashval, hash_methodqcode, comhashtime):
    if prop not in statements:
        return None

    hashqfound = False
    hashtimefound = False

    # note: need "WbTime" which is not a standard datetime
    wbdate = getwbdatefromdt(comhashtime)

    # Q104884110 - Imagehash perceptual hash
    # Q124969714 - Imagehash difference hash

    print("checking for hash and value", hashval)

    # property ID P9310 for "pHash checksum"
    # property ID P12563 for "dHash checksum"
    claimlist = statements[prop] # hash
    for claim in claimlist:
        target = claim.getTarget()
        if (target != hashval):
            # no match: skip
            continue

        print("hashvalue match found", hashval)
        #print("hashvalue sources: ", claim.getSources())
        #print("hashvalue qualifiers: ", claim.qualifiers)

        # check for method of hash
        hashqfound = isQcodeInClaimQualifiers(claim, hash_methodqcode, "P459")

        # check for timestamp of the hash as well
        if "P571" in claim.qualifiers:
            hashtimefound = True
            foiquali = claim.qualifiers["P571"]
            #print("DEBUG: quali:", str(foiquali), "in prop:", prop)
            for fclaim in foiquali:
                ftarget = fclaim.getTarget()
                if (ftarget == wbdate):
                    print("exact timestamp for phash found")

        # ok, hash should match, continue checking for qualifiers
        sourcelist = claim.getSources()
        for source in sourcelist:
            for key, value in source.items():
                if (key == "P459"):
                    print("property for hash determination method found", value)
                    for v in value: # v is another claim..
                        vtarget = v.getTarget()
                        targetqcode = getqcodefromwikidatalink(vtarget)
                        print("target for image hash: ", targetqcode)
                        if (targetqcode == hash_methodqcode):
                            hashqfound = True
                            print("found target for ImageHash ", targetqcode ,", hash value ", hashval)
                        else:
                            print("DEBUG: tq ", targetqcode)

                elif (key == "P571"):
                    #print("property for hash inception time found", value)
                    hashtimefound = True
                    print("found inception for ImageHash")
                else:
                    print("DEBUG: key ", key)
    
        # so, hash match, no qualifier found ->
        # add missing qualifier
        if (hashqfound == False):
            print("adding imagehash method to phash")
            p_claim = pywikibot.Claim(wikidata_site, 'P459', is_reference=False, is_qualifier=True)
            q_targetph = pywikibot.ItemPage(wikidata_site, hash_methodqcode)
            p_claim.setTarget(q_targetph)
            claim.addQualifier(p_claim)
            print("added imagehash method to phash")
        else:
            print("phash already has imagehash method")

        if (hashtimefound == False):
            print("NOTE: should add imagehash inception to phash")
            i_claim = pywikibot.Claim(wikidata_site, 'P571', is_reference=False, is_qualifier=True)
            i_claim.setTarget(wbdate)
            claim.addQualifier(i_claim)
            print("added imagehash inception to phash")
        else:
            print("phash already has inception time")


    # determination method: P459
    # Q104884110 - ImageHash perceptual hash
    # P348 - software version identifier
    # P571 - inception
    # P2048 - height
    # P2049 - width
    # hashlen?

    #return p_claim
    return None

def checkPerceptualHashInSdcData(pywikibot, wikidata_site, statements, hashval, comhashtime):
    return checkHashvalueInSdcData(pywikibot, wikidata_site, statements, 'P9310', hashval, "Q104884110", comhashtime)

def checkDifferenceHashInSdcData(pywikibot, wikidata_site, statements, hashval, comhashtime):
    return checkHashvalueInSdcData(pywikibot, wikidata_site, statements, 'P12563', hashval, "Q124969714", comhashtime)


# generic wrapper to check if given qcode exists for given property
# in SDC data
def isQcodeinProperty(statements, pcode, qcode):
    if (qcode == None):
        return False
    if pcode not in statements:
        return False

    claimlist = statements[pcode]
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode == qcode):
            # exact match found
            print("DEBUG: exact qcode found for", pcode ," value ", qcode)
            return True
    return False

# generic wrapper to check if given value string exists for given property
# in SDC data: don't try to parse as a qcode, just generic value
def isValueinProperty(statements, pcode, value):
    if (value == None):
        return False
    if pcode not in statements:
        return False

    claimlist = statements[pcode]
    for claim in claimlist:
        target = claim.getTarget()
        if (target == value):
            # exact match found
            print("DEBUG: exact value found for", pcode ," value ", value)
            return True
    return False

# kgobjectid should be plain number, same as objectId in object data
def isKansallisgalleriateosInStatements(statements, kgobjectid):
    return isValueinProperty(statements, "P9834", kgobjectid)

# handle adding kansallisgalleria id to structured data:
# if there is old-style accession number add new style object id as well
# so that current links will work
# kgtid should be plain number, same as objectId in object data
def addkansallisgalleriateostosdc(pywikibot, wikidata_site, kgobjectid):
    if (kgobjectid == None):
        return None
    if (len(kgobjectid) == 0):
        return None
    # property ID for "Kansallisgallerian teostunniste" / "Finnish National Gallery artwork ID"
    f_claim = pywikibot.Claim(wikidata_site, 'P9834')
    f_claim.setTarget(kgobjectid)
    return f_claim

# get value from sdc for checking
def getKansallisgalleriateosFromSdc(statements):
    if "P9834" not in statements:
        return None
   
    claimlist = statements["P9834"]
    for claim in claimlist:
        return claim.getTarget()
    return None

# kginventory should be string
def isKansallisgalleriaInventorynumberInStatements(statements, kginventory):
    if "P217" not in statements:
        return False
    
    foundmatch = False
    claimlist = statements['P217']
    for claim in claimlist:
        
        # skip if there is any inventory:
        # might need deeper look into different format (with/without dashes)
        foundmatch = True 
        
        target = claim.getTarget()
        if (target == kginventory):
            # exact match found
            print("DEBUG: exact inventory found", kginventory)
            return True
    return foundmatch

# kginventory is a string,
# collection is a qcode
def addkansallisgalleriaInventorynumberTosdc(pywikibot, wikidata_site, kginventory, collq):
    if (kginventory== None):
        return None
    if (len(kginventory) == 0):
        return None
    # property ID for "inventaarionumero"
    f_claim = pywikibot.Claim(wikidata_site, 'P217')
    f_claim.setTarget(kginventory)

    
    if (collq != None and len(collq) > 0):
        if ("Q2983474" in collq):
            qualifier_coll = pywikibot.Claim(wikidata_site, 'P195')  # property ID for "collection"
            qualifier_target = pywikibot.ItemPage(wikidata_site, "Q2983474")  # Kansallisgalleria (Q2983474)
            qualifier_coll.setTarget(qualifier_target)
            f_claim.addQualifier(qualifier_coll, summary='Adding collection qualifier')
    
    return f_claim

# check if creator qcode is already in SDC
def isCreatorinstatements(statements, creatorqcode):
    return isQcodeinProperty(statements, "P170", creatorqcode)

# add creator (artwork)
# input: creator q-code
#
def addCreatortoStatements(pywikibot, wikidata_site, creatorqcode):
    if (creatorqcode == None):
        return None
    if (len(creatorqcode) == 0):
        return None
    # property ID for "creator" (artwork)
    cr_claim = pywikibot.Claim(wikidata_site, 'P170')
    qualifier_targetcr = pywikibot.ItemPage(wikidata_site, creatorqcode)
    cr_claim.setTarget(qualifier_targetcr)
    return cr_claim

# check if location qcode is already in SDC
def isLocationinstatements(statements, locationqcode):
    return isQcodeinProperty(statements, "P276", locationqcode)

# add location (artwork)
# input: location q-code
#
def addLocationtoStatements(pywikibot, wikidata_site, locationqcode):
    if (locationqcode == None):
        return None
    if (len(locationqcode) == 0):
        return None
    # property ID for "creator" (artwork)
    fo_claim = pywikibot.Claim(wikidata_site, 'P276')
    qualifier_target = pywikibot.ItemPage(wikidata_site, locationqcode)
    fo_claim.setTarget(qualifier_target)
    return fo_claim

# check if inception (creation date) for artwork is in SDC
# 
def isKansallisgalleriaInceptionInStatements(statements, inception):
    if "P571" not in statements:
        return False
    
    foundmatch = False
    claimlist = statements['P571']
    for claim in claimlist:
        foundmatch = True # skip if there is any inception: accuracy/precision might not be same
        
        target = claim.getTarget()
        if (target == inception):
            # exact match found
            print("DEBUG: exact inception found", inception)
            return True
    return foundmatch

# add inception for artwork:
# currently we expect value from wikidata and in correct format
#
def addkansallisgalleriaInceptionTosdc(pywikibot, wikidata_site, inception):
    inc_claim = pywikibot.Claim(wikidata_site, 'P571') # property ID for "inception"
    # note: must format into "WbTime"
    # here we expect valid format from wikidata
    inc_claim.setTarget(inception)
    return inc_claim

# check if collection qcode is already in SDC:
# used for artwork with gallery collection,
# not used for finna-pictures
def isFngCollectioninstatements(statements, collqcode):
    return isQcodeinProperty(statements, "P195", collqcode)

# add collection (gallery) of artwork
# not used for finna pictures
# input: collection q-code
# Q2983474 Kansallisgalleria
# Q1393952 Sinebrychoffin taidemuseo
# Q754507 Ateneum
#
def addFngCollectiontostatements(pywikibot, wikidata_site, collqcode):
    if (collqcode == None):
        return None
    if (len(collqcode) == 0):
        return None
    # property ID for "creator" (artwork)
    f_claim = pywikibot.Claim(wikidata_site, 'P195')
    qualifier_target = pywikibot.ItemPage(wikidata_site, collqcode)
    f_claim.setTarget(qualifier_target)
    return f_claim

# add mime-type to sdc data (string)
# used to force creation of sdc entry
def addmimetypetosdc(pywikibot, wikidata_site, mimetype):
    # property ID for "mime type"
    mime_claim = pywikibot.Claim(wikidata_site, 'P1163')
    #qualifier_targetmime = pywikibot.ItemPage(wikidata_site, mimetype)
    mime_claim.setTarget(mimetype)
    return mime_claim

# add author (written work)
# input: author q-code
#def addauthortostatements(pywikibot, wikidata_site, author):
    # property ID for "author" (writer)
#    au_claim = pywikibot.Claim(wikidata_site, 'P50')
#    qualifier_targetau = pywikibot.ItemPage(wikidata_site, author)
#    au_claim.setTarget(qualifier_targetau)
#    return au_claim

# note: we need "WbTime" which is not a standard datetime
def getwbdate(incdate):
    if (incdate.year != 0 and incdate.month != 0 and incdate.day != 0):
        #print("DEBUG: setting year, month, day")
        return pywikibot.WbTime(incdate.year, incdate.month, incdate.day)
    elif (incdate.year != 0 and incdate.month != 0):
        #print("DEBUG: setting year, month")
        return pywikibot.WbTime(incdate.year, incdate.month)
    else:
        #print("DEBUG: setting year only")
        return pywikibot.WbTime(incdate.year)

# add inception date to sdc data
def addinceptiontosdc(pywikibot, wikidata_site, incdate, sourceurl):
    #wbdate = pywikibot.WbTime.fromTimestr(incdate.isoformat())

    if (incdate.year == 0):
        print("DEBUG: not a valid year for inception")
        return None
    
    # note: need "WbTime" which is not a standard datetime
    wbdate = getwbdate(incdate)

    inc_claim = pywikibot.Claim(wikidata_site, 'P571') # property ID for "inception"
    # note: must format into "WbTime"
    inc_claim.setTarget(wbdate)
    
    # note: this add qualifer but we want "reference" type
    qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
    qualifier_url.setTarget(sourceurl)
    inc_claim.addSource(qualifier_url, summary='Adding reference URL qualifier')

    # also, for earliest/latest date of range?
    # P1319 - earliest date
    # P1326 - latest date
    
    return inc_claim

# check if same inception already exists
def isinceptioninstatements(statements, incdate, sourceurl):
    if "P571" not in statements:
        return False

    # note: need "WbTime" which is not a standard datetime
    wbdate = getwbdate(incdate)

    claimlist = statements["P571"]
    for claim in claimlist:
        target = claim.getTarget()
        #print("DEBUG: target date", str(target))
        if (target == wbdate):
            print("DEBUG: exact target date match found")
            return True

    # just ignore adding for now, we need more checks that value we've got is usable
    # which has problems due to human-readable additions in some cases..
    print("DEBUG: inception exists, ignoring for now")
    return True

# https&#x3A;&#x2F;&#x2F;api.finna.fi&#x2F;v1&#x2F;record&#x3F;id&#x3D;
def parseapiidfromfinnapage(finnapage):
    index = finnapage.find(';api.finna.fi&')
    if (index < 0):
        return ""
    finnapage = finnapage[index:]        

    index = finnapage.find('id')
    if (index < 0):
        return ""
    index = finnapage.find('&#x3D;')
    if (index < 0):
        return ""
    index = index + len("&#x3D;")
    finnapage = finnapage[index:]

    indexend = finnapage.find('"')
    if (indexend < 0):
        indexend = finnapage.find('>')
        if (indexend < 0):
            return ""
    finnapage = finnapage[:indexend]
    
    # convert html code to character (if any)
    finnapage = finnapage.replace("&#x25;3A", ":")
    
    indexend = finnapage.find('&amp')
    if (indexend < 0):
        indexend = finnapage.find('&')
        if (indexend < 0):
            return ""
    finnapage = finnapage[:indexend]
    return finnapage

def parsedatarecordidfromfinnapage(finnapage):
    attrlen = len('data-record-id="')
    indexid = finnapage.find('data-record-id="')
    if (indexid < 0):
        return ""
        
    indexid = indexid+attrlen
    indexend = finnapage.find('"', indexid)
    if (indexend < 0):
        return ""

    return finnapage[indexid:indexend]

# fetch page
def requestpage(pageurl):

    page = ""

    try:
        headers={'User-Agent': 'pywikibot'}
        #response = requests.get(url, headers=headers, stream=True)
    
        request = urllib.request.Request(pageurl, headers=headers)
        print("request done: " + pageurl)

        response = urllib.request.urlopen(request)
        if (response.readable() == False):
            print("response not readable")
            return ""

        htmlbytes = response.read()
        page = htmlbytes.decode("utf8")

        #print("page: " + finnapage)
        return page # page found
        
    except urllib.error.HTTPError as e:
        print(e.__dict__)
        return ""
    except urllib.error.URLError as e:
        print(e.__dict__)
        return ""
    except UnicodeDecodeError as e:
        print(e.__dict__)
        return ""
    except UnicodeEncodeError as e:
        print(e.__dict__)
        return ""
    except http.client.InvalidURL as e:
        print(e.__dict__)
        return ""
    except InvalidURL as e:
        print(e.__dict__)
        return ""
    #except:
        #print("failed to retrieve page")
        #return ""

    return ""

# fetch metapage from finna and try to parse current ID from the page
# since we might have obsolete ID.
# new ID is needed API query.
def parsemetaidfromfinnapage(finnaurl):

    finnapage = requestpage(finnaurl)
    if (len(finnapage) <= 0):
        # failed to retrieve page
        print("WARN: Failed to retrieve page from Finna")
        return ""

    # try a new method to parse the id..
    newid = parseapiidfromfinnapage(finnapage)
    if (len(newid) > 0):
        # sometimes finna has this html code instead of url encoding..
        newid = newid.replace("&#x25;3A", ":")
        print("new id from finna: " + newid)
        return newid

    newid = parsedatarecordidfromfinnapage(finnapage)
    if (len(newid) > 0):
        # in case there is url encoding in place..
        #newid = newid.replace("%3A", ":")
        print("new id from finna: " + newid)
        return newid

    return ""

# input: source reported by commons (url to europeana eu)
def parsesourcefromeuropeana(commonssource):
    if (commonssource.find("europeana.eu") < 0):
        print("Not europeana url: " + commonssource)
        return ""
    if (commonssource.find("proxy.europeana.eu") >= 0):
        print("can't use proxy (might direct to binary image): " + commonssource)
        return ""

    eupage = requestpage(commonssource)
    if (len(eupage) <= 0):
        return ""

    attrlen = len('class="data-provider"')
    indexdp = eupage.find('class="data-provider"')
    if (indexdp < 0):
        return ""
    indexdp = eupage.find('>', indexdp+attrlen)
    if (indexdp < 0):
        return ""
    attrlen = len('href="')
    indexdp = eupage.find('href="', indexdp+1)
    if (indexdp < 0):
        return ""
    indexend = eupage.find('"', indexdp+attrlen)
    if (indexend < 0):
        return ""

    # this should get the actual source of image as it is set in europeana        
    eusource = eupage[indexdp+attrlen:indexend]
    if (len(eusource) <= 0):
        print("Failed to parse source from europeana: " + commonssource)
        return ""

    # this should be the source reported in europeana    
    print("europeana page source: " + eusource)
    return eusource

# note alternate: might have timestamp like "1943-06-24" or "01.06.1930"
# also: might be "yyyymm" or plain year or "mmyyyy".
# other cases: "1920-luku" or "1920 - 1929", there may be other text there as well
def timestringtodatetime(timestring):
    indexcomma = timestring.rfind(",") # there is comma-separated something?
    if (indexcomma > 0):
        #print("DEBUG: removing comma from timestring:", timestring)
        timestring = timestring[:indexcomma]
    indexcomma = timestring.find(",") # there is comma-separated something?
    if (indexcomma > 0):
        #print("DEBUG: removing comma from timestring:", timestring)
        timestring = timestring[:indexcomma]

    # remove dot at end if any
    if (timestring.endswith(".")):
        timestring = timestring[:len(timestring)-1]

    try:
        # two digits for day and month, four digits for year
        if (len(timestring) == 10):
            if (timestring.find('.') > 0): 
                dt = datetime.strptime(timestring, '%d.%m.%Y')
                fdt = FinnaTimestamp()
                fdt.setDate(dt.year, dt.month, dt.day)
                return fdt
            if (timestring.find('-') > 0): 
                dt = datetime.strptime(timestring, '%Y-%m-%d')
                fdt = FinnaTimestamp()
                fdt.setDate(dt.year, dt.month, dt.day)
                return fdt
        
        # single digit for day/month?
        if (len(timestring) == 9 or len(timestring) == 8):
            if (timestring.find('.') > 0): 
                dt = datetime.strptime(timestring, '%d.%m.%Y')
                fdt = FinnaTimestamp()
                fdt.setDate(dt.year, dt.month, dt.day)
                return fdt

        # plain year in string?
        if (timestring.isnumeric() == True):
            if (len(timestring) == 6):
                fdt = FinnaTimestamp()
                # there is year and month like "189605"
                yeara = int(timestring[:4])
                montha = int(timestring[4:6])
                # in some cases, there is another order
                monthb = int(timestring[:2])
                yearb = int(timestring[2:6])
                
                if (montha > 0 and montha < 13 and yeara < 2050 and yeara > 1300):
                    fdt.setYearMonth(yeara, montha)
                    return fdt
                if (monthb > 0 and monthb < 13 and yearb < 2050 and yearb > 1300):
                    fdt.setYearMonth(yearb, monthb)
                    return fdt

            if (len(timestring) == 4):
                num = int(timestring)
                fdt = FinnaTimestamp()
                fdt.setYear(num)
                return fdt
    except:
        print("failed to parse timestamp")
        return None
    
    print("DEBUG: cannot use timestring", timestring)
    return None

def getSubjectsFromFinnarecord(finnarecord):
    records = finnarecord['records'][0]
    if "subjects" not in records:
        return None
    subjects = finnarecord['records'][0]['subjects']
    return subjects


# remove pointless characters if any:
#  sometimes there are newlines and tabs in the string -> strip them out
def fixwhitespaces(s):
    s = s.replace("\n", " ")
    s = s.replace("\t", " ")
    s = s.replace("\r", " ")
    return trimlr(s)

# parse timestamp of picture from finna data
# TODO: sometimes there is a range of approximate dates given
# -> we could parse them but how do we mark them in SDC?
def parseinceptionfromfinna(finnarecord):
    if "records" not in finnarecord:
        print("ERROR: no records in finna record")
        return None

    subjects = getSubjectsFromFinnarecord(finnarecord)
    if (subjects == None):
        print("no subjects in finna record")
        return None
    try:
        for subject in subjects:
            for sbstr in subject:
                #  sometimes there is newlines and tabs in the string -> strip them out
                sbstr = fixwhitespaces(sbstr)
                
                index = sbstr.find("kuvausaika")
                if (index >= 0):
                    index = index+len("kuvausaika")
                    timestamp = sbstr[index:]

                    # something human-readable after a timestamp?
                    if (timestamp.find(",") > 0):
                        timestamp = leftfrom(timestamp, ",")
                    
                    indexend = timestamp.rfind(" ")
                    if (indexend >= 0):
                        timestamp = timestamp[indexend:]
                    print("DEBUG: kuvausaika in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)

                index = sbstr.find("ajankohta:")
                if (index >= 0):
                    index = index+len("ajankohta:")
                    timestamp = sbstr[index:]

                    # something human-readable after a timestamp?
                    if (timestamp.find(",") > 0):
                        timestamp = leftfrom(timestamp, ",")
                    
                    indexend = timestamp.rfind(" ")
                    if (indexend >= 0):
                        timestamp = timestamp[indexend:]
                    print("DEBUG: ajankohta in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)
                
                # "valmistus" may have time, place, materials..
                index = sbstr.find("valmistusaika ")
                if (index >= 0):
                    index = index+len("valmistusaika ")
                    timestamp = sbstr[index:]

                    # something human-readable after a timestamp?
                    if (timestamp.find(",") > 0):
                        timestamp = leftfrom(timestamp, ",")
                    
                    indexend = timestamp.rfind(" ")
                    if (indexend >= 0):
                        timestamp = timestamp[indexend:]
                    print("DEBUG: valmistusaika in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)
                
                # note: in some cases there is just timestamp without a string before it
                fdt = timestringtodatetime(sbstr)
                if (fdt != None):
                    return fdt
                    
        # try to find plain year if there is no other date format
        return parseinceptionyearfromfinna(finnarecord)
    except:
        print("failed to parse timestamp")
        return None
    return None

# some records have only a year in them?
def parseinceptionyearfromfinna(finnarecord):
    if "records" not in finnarecord:
        print("ERROR: no records in finna record")
        return None

    records = finnarecord['records'][0]
    if "year" not in records:
        print("no year in finna record")
        return None
    try:
        year = finnarecord['records'][0]['year']
        year = trimlr(year)
        if (year.isnumeric() == False):
            print("DEBUG: not a numeric year: " + year)

        # if conversion fails -> not a usable number
        yearnum = int(year)

        # TODO: if last digit is zero, we have only per-decade precision?
        # if two last digits are zero, we only have per-century precision?

        fdt = FinnaTimestamp()
        fdt.setYear(yearnum, True)
        return fdt
    except:
        print("failed to parse timestamp")
        return None
    return None

def getnewsourceforfinna(finnarecord):
    return "<br>Image record page in Finna: [https://finna.fi/Record/" + finnarecord + " " + finnarecord + "]\n"

def getqcodeforfinnapublisher(finnarecord, institutionqcode):
    if "records" not in finnarecord:
        print("ERROR: no records in finna record")
        return ""

    records = finnarecord['records'][0]
    if "institutions" not in records:
        print("WARN: no institutions in finna record")
        
        if "buildings" not in records:
            print("ERROR: no institutions or buildings in finna record" + str(records))
            return ""
        else:
            finnainstitutions = records['buildings'][0]
            print("found building in finna record: " + str(finnainstitutions))
    else:
        finnainstitutions = records['institutions'][0]
        print("found institution in finna record: " + str(finnainstitutions))

    # TODO: might need to check both "value" and "translated" for correct name?
    # helsinki city museum has "HKM" and "Helsinki City Museum"

    for key, val in finnainstitutions.items():
        #print("val is: " + val)
        if val in institutionqcode:
            return institutionqcode[val]
        
    return ""

def getqcodeforfinnaoperator(finnarecord):
    if "records" not in finnarecord:
        print("ERROR: no records in finna record")
        return ""
    #records = finnarecord['records'][0]

    # if operator == Kansalliskirjasto -> Q420747
    # if operator == Suomen valokuvataiteen museo -> Q11895148
    # Kansallisgalleria Q2983474 

    #if National Library of Finland (Kansalliskirjasto)
    return "Q420747"

def getqcodeforbydomain(url):
    if (url.find("finna.fi") > 0):
        # National Library of Finland (Kansalliskirjasto)
        return "Q420747"
    if (url.find("fng.fi") > 0):
        # Kansallisgalleria (vanha domain, ei toimiva)
        return "Q2983474"
    if (url.find("kansallisgalleria.fi") > 0):
        # Kansallisgalleria 
        return "Q2983474"
    # ateneum.fi
    # sinebrychoffintaidemuseo.fi
    # kiasma.fi
    # Suomen valokuvataiteen museo -> Q11895148
    
    #if (url.find("flickr.com"):
        #if "museovirastonkuvakokoelmat" or "valokuvataiteenmuseo" or "finnishnationalgallery"
        # return "Q103204"
    return ""

# note: if there are no collections, don't remove from commons as they may have manual additions
def getCollectionsFromRecord(finnarecord, finnaid, labeltoqcode):

    collectionqcodes = list()
    if "collections" not in finnarecord['records'][0]:
        print("WARN: 'collections' not found in finna record: " + finnaid)
        return collectionqcodes
    
    # collections: expecting ['Historian kuvakokoelma', 'Studio Kuvasiskojen kokoelma']
    finna_collections = finnarecord['records'][0]['collections']

    print("found collections in finna record: " + str(finna_collections))

    #if ("Antellin kokoelma" in finna_collections):
        #print("Skipping collection (can't match by hash due similarities): " + finnaid)
        #continue

    # lookup qcode by label TODO: fetch from wikidata 
    for coll in finna_collections:
        if coll in labeltoqcode:
            collectionqcodes.append(labeltoqcode[coll])
    return collectionqcodes

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

    #print("DEBUG: ", finnarecord)
    return True

# get accession number / identifier string from finna
def getFinnaAccessionIdentifier(finnarecord):
    records = finnarecord['records'][0]

    finna_id = ""
    if "id" in records:
        # there is often id even if accession number is not there
        finna_id = records['id']
    
    if "identifierString" not in records:
        print("WARN: no identifier in finna record, id:", finna_id)
        return ""

    finnaidentifier = records['identifierString']
    print("DBEUG: found identifier in finna record: ", str(finnaidentifier))
    return finnaidentifier

def getTitleFromFinna(finnarecord, lang='fi'):
    records = finnarecord['records'][0]
    
    f_title = ""
    if "title" in records:
        #print("DBEUG: found title in finna record: ", records['title'])
        
        # there is a limit to how much commons caption allows
        if (len(records['title']) < 250):
            f_title = records['title']

    #if "shortTitle" in records:
        #print("DBEUG: found shortTitle in finna record: ", records['shortTitle'])
        
    #if "subTitle" in records:
        #print("DBEUG: found subTitle in finna record: ", records['subTitle'])

    #if "summary" in records:
        #print("DBEUG: found summary in finna record: ", records['summary'])

    print("DBEUG: found title in finna record: ", f_title)
    return f_title

# check if we have normal photographic image
# (if not artwork, drawing or something else)
def isFinnaFormatImage(finnarecord):
    records = finnarecord['records'][0]
        
    if "formats" not in records:
        print("ERROR: no formats in finna record" + str(records))
        return ""
    
    finnaformats = records['formats'][0]['value']
    print("DBEUG: found formats in finna record: " + str(finnaformats))

    if (finnaformats == "0/Image/"):
        print("DBEUG: found image format in finna record: " + str(finnaformats))
        return True

    if (finnaformats == "1/Image/Photo/"):
        print("DBEUG: found photo format in finna record: " + str(finnaformats))
        return True

    # note, might be "0/PhysicalObject/" for images of physical objects
    # handle those as photographs as well?
    
    # Note, don't modify when "0/WorkOfArt/"

    # translated names
    if (finnaformats == "Image" or finnaformats == "Kuva" or finnaformats == "Bild"):
        print("DBEUG: found image format in finna record: " + str(finnaformats))
        return True

    print("not an image format in finna record: " + str(finnaformats))
    return False

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

# helper to check in case of malformed json
def getFinnaImagelist(finnarecord):
    if "images" not in finnarecord['records'][0]:
        return None

    # 'images' can have array of multiple images, need to select correct one
    # -> loop through them (they should have just different &index= in them)
    # and compare with the image in commons
    imageList = finnarecord['records'][0]['images']

    if (len(imageList) == 0):
        return None

    # at least one entry exists
    return imageList

def getFinnaDatalist(finnarecord, param):
    if param not in finnarecord['records'][0]:
        print("WARN: '", param ,"' not found in finna record: " + finnaid)
        return None

    finnadata = finnarecord['records'][0][param]
    print("found ", param ," in finna record: " + str(finnadata))
    return finnadata

def getFinnaSubjects(finnarecord):
    datalist = list()
    finnadata = getFinnaDatalist(finnarecord, "subjects")
    if (finnadata == None):
        return datalist
    for d in finnadata:
        for dstr in d:
            #  sometimes there is newlines and tabs in the string -> strip them out
            dstr = fixwhitespaces(dstr)
            datalist.append(dstr)
    return datalist

def getFinnaActors(finnarecord):
    datalist = list()
    finnadata = getFinnaDatalist(finnarecord, "subjectActors")
    if (finnadata == None):
        return datalist
    for dstr in finnadata:
        #  sometimes there is newlines and tabs in the string -> strip them out
        dstr = fixwhitespaces(dstr)
        datalist.append(dstr)
    return datalist

def getFinnaPlaces(finnarecord):
    datalist = list()
    finnadata = getFinnaDatalist(finnarecord, "subjectPlaces")
    if (finnadata == None):
        return datalist
    for dstr in finnadata:
        #  sometimes there is newlines and tabs in the string -> strip them out
        dstr = fixwhitespaces(dstr)
        datalist.append(dstr)
    return datalist

# "nonpresenterauthor" is "creators" in commons-speak:
# in this case we want photographers
# 
def getFinnaNonPresenterAuthors(finnarecord):
    # also: pht for swedish language archive
    photographer_roles = ['kuvaaja', 'Kuvaaja', 'valokuvaaja', 'Valokuvaaja', 'pht']

    datalist = list()
    finnadata = getFinnaDatalist(finnarecord, "nonPresenterAuthors")
    if (finnadata == None):
        return datalist
    if (len(finnadata) == 0):
        print("DEBUG: empty list in nonPresenterAuthors: ", finnaid)
        return datalist
    
    for entry in finnadata:
        if ("name" not in entry or "role" not in entry):
            continue
        name = entry["name"]
        role = entry["role"]

        print("DEBUG: nonPresenterAuthors, name: ", name ," role: ", role)

        if role in photographer_roles:
            datalist.append(name)
    return datalist


# check image metadata if it could be uploaded again with a higher resolution
#
def needReupload(file_info, finna_record, imagesExtended):

    if "highResolution" not in imagesExtended:
        print("WARN: 'highResolution' not found in imagesExtended: " + finnaid)
        return False
    
    # note! 'original' might point to different image than used above! different server in some cases
    hires = imagesExtended['highResolution']

    # there is at least one case where this is not available?
    if "original" not in hires:
        print("WARN: 'original' not found in hires image: " + finnaid)
        return False
            
    hires = imagesExtended['highResolution']['original'][0]
    if "data" not in hires:
        print("WARN: 'data' not found in hires image: " + finnaid)
        return False

    if "format" not in hires:
        print("WARN: 'format' not found in hires image: " + finnaid)
        return False

    # some images don't have size information in the API..
    if "width" not in hires['data'] or "height" not in hires['data']:
        # it seems sizes might be missing when image is upscaled and not "original"?
        # -> verify this
        # -> skip image for now
        return False
    else:
        # verify finna image really is in better resolution than what is in commons
        # before uploading
        finnawidth = int(hires['data']['width']['value'])
        finnaheight = int(hires['data']['height']['value'])
    
    if file_info.width >= finnawidth or file_info.height >= finnaheight:
        print("Page " + page.title() + " has resolution equal or higher than finna: " + str(finnawidth) + "x" + str(finnaheight))
        return False
    
    # resolution smaller, could re-upload (assuming hashes already match)
    print("Page " + page.title() + " has larger image available, could re-upload")
    return True

def reuploadImage(finnaid, file_info, imagesExtended, need_index, file_page, finna_image_url):

    finna_record_url = "https://finna.fi/Record/" + finnaid

    # note: mostly validated in above (called earlier)
    hires = imagesExtended['highResolution']['original'][0]
    
    commons_image_url = file_page.get_file_url()
    commons_image = downloadimage(commons_image_url)
    if (commons_image == None):
        print("WARN: Failed to download commons-image: " + commons_image_url )
        return False

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
            print("WARN: Failed to download finna-image: " + finna_image_url )
            return False
        image_file_name = convert_tiff_to_jpg(local_image)
        local_file=True    
    elif hires["format"] == "tif" and file_info.mime == 'image/png':
        print("converting image from tiff to png") # log it
        if (need_index == False):
            finna_image_url = hires['url']
        local_image = downloadimage(finna_image_url)
        if (local_image == None):
            print("WARN: Failed to download finna-image: " + finna_image_url )
            return False
        image_file_name = convert_tiff_to_png(local_image)
        local_file=True    
    #elif hires["format"] == "tif" and file_info.mime == 'image/gif':
        #print("converting image from tiff to gif") # log it
        #if (need_index == False):
            #finna_image_url = hires['url']
        #local_image = downloadimage(finna_image_url)
        #if (local_image == None):
            #print("WARN: Failed to download finna-image: " + finna_image_url )
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
        return False

    # can't upload if identical to the one in commons:
    # compare hash of converted image if necessary,
    # need to compare full image for both (not thumbnails)
    if (local_file == False):
        # get full image before trying to upload:
        # code above might have switched to another
        # from multiple different images
        local_image = downloadimage(finna_image_url)
        if (local_image == None):
            print("WARN: Failed to download finna-image: " + finna_image_url )
            return False

        # if image is identical by sha-hash -> commons won't allow again
        if (isidentical(local_image, commons_image) == True):
            print("Images are identical files, skipping: " + finnaid)
            return False

        local_hash = getimagehash(local_image)
        if (local_hash == None):
            print("WARN: Failed to hash local image: " + finnaid )
            return False
            
        # verify that the image we have picked above is the same as in earlier step:
        # internal consistency of the API has an error?
        if (is_same_image_old(local_image, finna_image) == False):
            print("WARN: Images are NOT same in the API! " + finnaid)
            print("DEBUG: image bands", local_image.getbands())
            return False
        
        # verify if file in commons is still larger?
        # metadata in finna is wrong or server sending wrong image?
        if commons_image.width >= local_image.width or commons_image.height >= local_image.height:
            print("WARN: image in Finna is not larger than in Commons: " + finnaid)
            return False

    else:
        converted_image = Image.open(image_file_name)
        # if image is identical by sha-hash -> commons won't allow again
        if (isidentical(converted_image, commons_image) == True):
            print("Images are identical files, skipping: " + finnaid)
            return False

        # at least one image fails in conversion, see if there are others
        if (is_same_image_old(converted_image, commons_image) == False):
            print("ERROR! Images are NOT same after conversion! " + finnaid)
            print("DEBUG: image bands", local_image.getbands())
            return False

        # after conversion, file in commons is still larger?
        # conversion routine is borked or other error?
        if file_info.width >= converted_image.width or file_info.height >= converted_image.height:
            print("WARN: converted image is not larger than in Commons: " + finnaid)
            return False

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

    return True


def getFinnaLicense(imagesExtended):
    # should be CC BY 4.0 or Public domain/CC0
    return imagesExtended['rights']['copyright']

# try to determine if image is copyrighted:
# note the comments, this can get complicated..
# there are various complications in determining copyright status,
# only if it has been marked that copyright has been waived we can be confident
def determineCopyrightStatus(finnarecord):
    if (finnarecord == None):
        # can't determine -> safer to assume it is?
        return ""

    #P6216 = Q88088423 (copyright status = tekijänoikeuden suojaama, mutta tekijänoikeuden omistaja on asettanut sen public domainiin )
    #P275 = Q98592850 (copyright license = tekijänoikeuden omistaja on julkaissut teoksen public domainiin )
    
    imagesExtended = getImagesExtended(finnarecord)
    if (imagesExtended == None):
        # can't determine -> safer to assume it is
        return ""

    copyrightlicense = getFinnaLicense(imagesExtended)
    if (copyrightlicense == "PDM"):
        # not copyrighted: copyright has been waived by releasing into PD
        # tekijänoikeuden suojaama, mutta tekijänoikeuden omistaja on asettanut sen public domainiin
        return "Q88088423"
    if (copyrightlicense == "CC0"):
        # might be same as PDM: Q88088423
        # ei tunnettuja tekijänoikeusrajoituksia
        return "Q99263261"
    
    # otherwise.. it's complicated, we need to know when it was taken,
    # if it is artwork or not, is the photographer alive and if not for long..
    # -> safer to just assume it is
    return "Q50423863"

# in the case where structured data is missing from commons-page,
# force creating it early so that rest of the operations can work (adding/checking data).
# otherwise all operations will just fail.
def fixMissingSdcData(pywikibot, wikidata_site, commonssite, file_info, page):
    try:
        #item = pywikibot.ItemPage.fromPage(page) # can't use in commons, no related wikidata item
        # note: data_item() causes exception if wikibase page isn't made yet, see for an alternative
        # repo == site == commonssite
        if (doessdcbaseexist(page) == False):
            print("Wikibase item does not yet exist for: " + page.title() )

            if not 'mediainfo' in page.latest_revision.slots:
                print("no mediainfo yet? we can fail on page: " + page.title() )

            wditem = page.data_item()  # Get the data item associated with the page
            sdcdata = wditem.get_data_for_new_entity() # get new sdc item

            ## add something like P1163 (mime-type) to force creation of sdc-data
            print("adding mime-type: " + str(file_info.mime))
            mime_claim = addmimetypetosdc(pywikibot, wikidata_site, file_info.mime)
            wditem.addClaim(mime_claim)

            #file_info.mime == 'image/jpeg'
            
            # alternate method
            #addSdcMimetype(commonssite, file_media_identifier, str(file_info.mime))

            if (doessdcbaseexist(page) == False):
                print("ERROR: Failed adding Wikibase item for: " + page.title() )
                #exit(1)
                # failed to create sdc data for some reason and still missing
                return False
            #continue
        return True
    except:
        print("pywikibot failed")
        return False
    
    # exists alraedy or created successfully -> ok
    return True

def getValueFromWdItem(wikidataitem, pcode):
    instance_of = wikidataitem.claims.get(pcode, [])
    if (instance_of == None):
        print("DEBUG: property is not defined", pcode)
        return None
    if (len(instance_of) > 1):
        print("DEBUG: more than one instance")

    for claim in instance_of:
        target = claim.getTarget()
        if (target != None):
            #print("target: ", str(target))
            return target
    return None

def getQcodeFromWdItem(wikidataitem, pcode):
    instance_of = wikidataitem.claims.get(pcode, [])
    if (instance_of == None):
        print("DEBUG: property is not defined", pcode)
        return None
    if (len(instance_of) > 1):
        print("DEBUG: more than one instance")
        
    for claim in instance_of:
        target = claim.getTarget()
        if (target != None):
            #print("target: ", str(target))
            #print("id: ", str(target.id))
            return target.id
    return None

# get author qcode for artwork from wikidata:
# use when artwork qcode is known
#
def getAuthorFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return None
    if (len(qcodes) == 0):
        return None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None
    author = getQcodeFromWdItem(wikidata_item, 'P170')
    return author

# get location (=gallery/instituion) for artwork from wikidata
#
def getLocationFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return None
    if (len(qcodes) == 0):
        return None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None
    location = getQcodeFromWdItem(wikidata_item, 'P276')
    return location

# get collection qcode for artwork from wikidata:
# use when artwork qcode is known.
# usually "kansallisgalleria" for artwork
#
def getCollectionsFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return None
    if (len(qcodes) == 0):
        return None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None
    
    instance_of = wikidata_item.claims.get('P195', [])
    if (instance_of == None):
        print("DEBUG: no property for collections")
        return None
        
    if (len(instance_of) == 0):
        print("DEBUG: no collection instances", str(instance_of))
    if (len(instance_of) > 1):
        print("DEBUG: multiple collection instances", str(instance_of))
        
    collections = list()
    for claim in instance_of:
        target = claim.getTarget()
        print("target: ", str(target))
        print("id: ", str(target.id))
        if target.id not in collections:
            collections.append(target.id)
    
    print("DEBUG: found collections", str(collections))
    return collections

# in some cases, all relevant information is in wikidata-item
# instead of in commons page in a template:
# try to lookup the wikidata-items to locate possible inventory number / object id
#
# properties:
# catalog code (P528), described at URL (P973), described by source (P1343),
def getKansallisgalleriaTeostunnisteFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return None
    if (len(qcodes) == 0):
        return None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None

    # try teostunniste first
    teostunniste = getValueFromWdItem(wikidata_item, 'P9834')
    if (teostunniste == None):
        print("DEBUG: teostunniste not found for", itemqcode)
    
    return teostunniste

def getKansallisgalleriaInventaarionumeroFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return None
    if (len(qcodes) == 0):
        return None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None

    # use inventory number to lookup teostunniste if it doesn't yet exist
    inventaario = getValueFromWdItem(wikidata_item, 'P217')
    if (inventaario == None):
        print("DEBUG: inventory number not found for", itemqcode)

    return inventaario

# get creation data for artwork
#
def getKansallisgalleriaInceptionFromWikidata(pywikibot, wikidata_site, qcodes):
    if (qcodes == None):
        return False, None
    if (len(qcodes) == 0):
        return False, None
    if (len(qcodes) > 1):
        print("WARN: more than one qcode")
    print("DEBUG: qcodes", str(qcodes))
    
    itemqcode = qcodes[0]
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return False, None

    foundval = False
    incdt = getValueFromWdItem(wikidata_item, 'P571')
    if (incdt == None):
        print("DEBUG: inception not found for", itemqcode)
    else:
        #print("DEBUG: inception found", str(incdt))
        foundval = True

    # python fucks up "none" check if there are zero fields in the timestamp
    # -> force a bool to tell that we really found a value
    return foundval, incdt

# get name of institution-template (for commons) from wikidata
#
def getInstitutionTemplateFromWikidata(pywikibot, wikidata_site, itemqcode):
    if (itemqcode == None):
        return None
    if (len(itemqcode) == 0):
        return None
    
    wikidata_item = pywikibot.ItemPage(wikidata_site, itemqcode)
    if not wikidata_item.exists():
        print("WARN: qcode", itemqcode, "does not exist in wikidata")
        return None
    template = getValueFromWdItem(wikidata_item, 'P1612')
    return template


# ----- CommonsTemplate
# helper to contain stuff related to commons template parsing,
# also contain adding information where missing
class CommonsTemplate:
   
    def isChanged(self):
        return self.changed

    # mwparser is has bugs so try to handle them
    def getTemplateName(self, template):
        name = leftfrom(template.name, "\n") # mwparserfromhell is bugged
        name = trimlr(name)
        return name

    # if template type is "information" it doesn't have all necessary fields
    # but don't change if it is "artwork" or something else already
    def fixTemplateType(self, template):
        name = self.getTemplateName(template)
        if (name == "Information"):
            template.name.replace("Information", "Photograph")
            self.changed = True
            return True
        if (name == "information"):
            template.name.replace("information", "Photograph")
            self.changed = True
            return True
        return False

    # note: page may have multiple templates
    def isSupportedCommonsTemplate(self, template):
        #print("DEBUG commons template: ", template.name)
        name = self.getTemplateName(template)
        name = name.lower()
        if (name == "information" 
            or name == "photograph" 
            or name == "artwork" 
            or name == "art photo"):
            return True
        #print("DEBUG: not supported template: ", name)
        return False

    # get first supported template from list of templates
    # (list may contain other templates contained within as nesting)
    def getSupportedTemplate(self):
        for template in self.templatelist:
            if (self.isSupportedCommonsTemplate(template) == True):
                return template
        return None

    # note: page may have multiple templates
    def getSourceFromCommonsTemplate(self, template):
        if template.has("Source"):
            return template.get("Source")
        if template.has("source"):
            return template.get("source")
        return None

    # note: page may have multiple templates
    def getAccessionFromCommonsTemplate(self, template):
        if template.has("Accession number"):
            return template.get("Accession number")
        if template.has("accession number"):
            return template.get("accession number")
        if template.has("ID"):
            return template.get("ID")
        if template.has("Id"):
            return template.get("Id")
        if template.has("id"):
            return template.get("id")
        return None

    def getAuthorFromCommonsTemplate(self, template):
        if template.has("Author"):
            return template.get("Author")
        if template.has("author"):
            return template.get("author")
        return None

    def getPhotographerFromCommonsTemplate(self, template):
        if template.has("Photographer"):
            return template.get("Photographer")
        if template.has("photographer"):
            return template.get("photographer")
        return None

    # note: multipiple names, may be "institution", "gallery" or "museum"
    #
    def getInstitutionFromCommonsTemplate(self, template, fullsearch=False):
        if template.has("Institution"):
            return template.get("Institution")
        if template.has("institution"):
            return template.get("institution")

        if (fullsearch == True):
            if template.has("Gallery"):
                return template.get("Gallery")
            if template.has("gallery"):
                return template.get("gallery")

            if template.has("Museum"):
                return template.get("Museum")
            if template.has("museum"):
                return template.get("museum")
        return None

    def getDepictedPeopleCommonsTemplate(self, template):
        if template.has("depicted people"):
            return template.get("depicted people")
        if template.has("Depicted people"):
            return template.get("Depicted people")
        if template.has("Depicted_people"):
            return template.get("Depicted_people")
        if template.has("depicted_people"):
            return template.get("depicted_people")
        return None

    def getDepictedPlacesCommonsTemplate(self, template):
        if template.has("depicted place"):
            return template.get("depicted place")
        if template.has("Depicted place"):
            return template.get("Depicted place")
        if template.has("Depicted_place"):
            return template.get("Depicted_place")
        if template.has("depicted_place"):
            return template.get("depicted_place")
        return None

    # note: page may have multiple templates
    # The template artwork has field "references"
    def getReferencesFromCommonsTemplate(self, template):
        if template.has("References"):
            return template.get("References")
        if template.has("references"):
            return template.get("references")
        return None

    # note: page may have multiple templates
    def getWikidataParamFromCommonsTemplate(self, template):
        if template.has("Wikidata"):
            return template.get("Wikidata")
        if template.has("wikidata"):
            return template.get("wikidata")
        return None

    # missing or empty value
    def isEmptyParamValue(self, par):
        if (par == None):
            return True
        parval = str(par.value)
        parval = trimlr(parval)
        if (len(parval) == 0):
            return True
        return False

    # work around parser/python bugs
    def getParValue(self, par):
        if (par == None):
            return True
        parval = str(par.value)
        return trimlr(parval)

    # add institution text to the template field
    # should have institution-template
    #def addInstitution(self, institution):

    # add department (collection) text to the template field
    #def addDepartment(self, department):

    # add author text to the template field:
    # should have creator-template
    #def addAuthor(self, author):

    # add institution to the template field
    def addOrSetInstitution(self, template, instVal):
        if (len(instVal) == 0):
            return False
        par = self.getInstitutionFromCommonsTemplate(template, True)
        if (par == None):
            template.add("Institution", instVal)
            self.changed = True
            return True
        else:
            if (self.isEmptyParamValue(par) == True):
                par.value = instVal + "\n"
                self.changed = True
                return True
            # if it is not empty, don't do anything
            # could append but might add duplicates by mistake
        return False

    # add accession number/id text to the template field
    # note: may have different names for this field..
    def addOrSetAccNumber(self, template, accValue):
        if (len(accValue) == 0):
            return False
        par = self.getAccessionFromCommonsTemplate(template)
        if (par == None):
            template.add("Accession number", accValue)
            self.changed = True
            return True
        else:
            if (self.isEmptyParamValue(par) == True):
                par.value = accValue + "\n"
                self.changed = True
                return True
            # if it is not empty, don't do anything
            # could append but might add duplicates by mistake
        return False

    def addOrSetPhotographers(self, template, photographers):
        if (photographers == None):
            return False
        if (len(photographers) == 0):
            return False

        # TODO: if there are authors, skip adding photographers?
        parAuthors = self.getAuthorFromCommonsTemplate(template)
        if (self.isEmptyParamValue(parAuthors) == False):
            authors = self.getParValue(parAuthors)
            authors = authors.replace("\n", "")
            if (len(authors) > 0 and authors != "Museovirasto"):
                # something already in author that is not institution
                # -> don't add again
                print("Already has authors: ", authors)
                return False

        people = photographers
        people = ""
        for p in photographers:
            if (len(people) > 0):
                people += ";"
            people += p
        #people = "{{fi|" + people + "}}"
        
        #
        print("Adding photographers: ", people)
        par = self.getPhotographerFromCommonsTemplate(template)
        if (par == None):
            template.add("photographer", people)
            self.changed = True
            return True
        else:
            if (self.isEmptyParamValue(par) == True):
                par.value = people + "\n"
                self.changed = True
                return True
            # if it is not empty, don't do anything
            # could append but might add duplicates by mistake
        return False


    def addOrSetDepictedPeople(self, template, peoplelist):
        if (peoplelist == None):
            return False
        if (len(peoplelist) == 0):
            return False
        
        people = peoplelist
        people = ""
        for p in peoplelist:
            if (len(people) > 0):
                people += ";"
            people += p
        people = "{{fi|" + people + "}}"

        print("Adding depicted people: ", people)
        par = self.getDepictedPeopleCommonsTemplate(template)
        if (par == None):
            template.add("depicted people", people)
            self.changed = True
            return True
        else:
            if (self.isEmptyParamValue(par) == True):
                par.value = people + "\n"
                self.changed = True
                return True
            # if it is not empty, don't do anything
            # could append but might add duplicates by mistake
        return False

    def addOrSetDepictedPlaces(self, template, placelist):
        if (placelist == None):
            return False
        if (len(placelist) == 0):
            return False

        places = ""
        for p in placelist:
            if (len(places) > 0):
                places += ";"
            places += p
        places = "{{fi|" + places + "}}"
        
        print("Adding depicted places: ", places)
        par = self.getDepictedPlacesCommonsTemplate(template)
        if (par == None):
            template.add("depicted place", places)
            self.changed = True
            return True
        else:
            if (self.isEmptyParamValue(par) == True):
                par.value = places + "\n"
                self.changed = True
                return True
            # if it is not empty, don't do anything
            # could append but might add duplicates by mistake
        return False


    # call to initialize
    def parseTemplate(self, page_text):
        self.wikicode = mwparserfromhell.parse(page_text)
        self.templatelist = self.wikicode.filter_templates()

        # reset dirty-flag: have we modified it to warrant saving?
        self.changed = False
        
        #self.template = getSupportedTemplate()

        # TODO: further checks if we can process this page correctly
        # note: a page may have multiple templates
        return True

# ----- /CommonsTemplate

# The template artwork has field "references", where data might be coming from wikidata 
# instead of being in page. This means there's need to access wikidata-site
# properties:
# catalog code (P528), described at URL (P973), described by source (P1343),
def getUrlsFromCommonsReferences(ct):

    for template in ct.templatelist:
        # at least three different templates have been used..
        if (ct.isSupportedCommonsTemplate(template) == True):
            refpar = ct.getReferencesFromCommonsTemplate(template)
            if (refpar != None):
                srcvalue = str(refpar.value)
                srcurls = geturlsfromsource(srcvalue)
                if (len(srcurls) > 0):
                    #print("DEBUG found urls in references")
                    return srcurls
            #else:
                #print("DEBUG: no references par in template")
                
                
    # TODO: if there aren't "hard-coded" references
    # try to look for them in wikidata properties
    
    #print("DEBUG: no urls found in template")
    return None


# find source urls from template(s) in commons-page
def getsourceurlfrompagetemplate(ct):

    for template in ct.templatelist:
        # at least three different templates have been used..
        if (ct.isSupportedCommonsTemplate(template) == True):
            #paracc = getAccessionFromCommonsTemplate(template)
            #if (paracc != None):
                #accurls = geturlsfromsource(str(paracc.value))
                # if accession has finna-url but source doesn't -> try it instead
            
            par = ct.getSourceFromCommonsTemplate(template)
            if (par != None):
                srcvalue = str(par.value)
                srcurls = geturlsfromsource(srcvalue)
                if (len(srcurls) > 0):
                    return srcurls

            #else:
                #print("DEBUG: no source par in template")
        #else:
            #print("DEBUG: not supported template")

    #print("DEBUG: no urls found in template")
    return None

# get wikidata q-codes related to commons page:
# qcode-field is used for artwork usually
def getwikidatacodefrompagetemplate(ct):

    wikidatacodes = list() # wikidata qcodes from template/page
    
    for template in ct.templatelist:
        if (ct.isSupportedCommonsTemplate(template) == True):

            wdpar = ct.getWikidataParamFromCommonsTemplate(template)
            if (wdpar != None):
                qcode = str(wdpar.value)
                qcode = trimlr(qcode)
                if (len(qcode) > 1): # at least Q and some number
                    wikidatacodes.append(qcode)

    if (len(wikidatacodes) == 0):
        print("DEBUG: no qcodes found in template", page.title())
    else:
        print("DEBUG: qcodes found in template", wikidatacodes)
    return wikidatacodes

# helper to check if list has similar category
# like if there is "Aircraft in Helsinki" then don't add "Aircraft in Finland":
# check if a cat has same base phrase like "Aircraft in "
# Also something like "1980 in Helsinki" or "1980 in Finland" you can check for location cats.
# Note: there needs case-insensitive support for some category types?
def findcatwithphrase(phrase, existingcategories):
    print("DEBUG: looking for phrase: ", phrase)
    for cat in existingcategories:
        print("DEBUG: existing cat: ", cat )
        if (cat.find(phrase) >= 0):
            return True
    print("DEBUG: phrase not found in existing cats: ", phrase)
    return False

# lookup subjects in finna-data that easily map into commons-categories
# and that we can add to commons-pages
#
def getcategoriesforsubjects(pywikibot, finnarecord, existingcategories, inceptiondt):
    # subject tags to commons-categories:
    # must be in subjects-list from Finna
    #
    # Ssteamboats: non ocean-going
    # Steamships of Finland
    # Naval ships of Finland
    # Sailing ships of Finland
    subject_categories = {
        #'muotokuvat': 'Portrait photographs',
        #'henkilökuvat': 'Portrait photographs',
        #'henkilövalokuvat': 'Portrait photographs',
        #'saamenpuvut' : 'Sami clothing',
        #'Osuusliike Elanto': 'Elanto',
        #'Valmet Oy': 'Valmet',
        #'Salora Oy': 'Salora',
        #'Veljekset Åström Oy': 'Veljekset Åström',
        #'Yntyneet Paperitehtaat': 'Yntyneet Paperitehtaat',
        #'Turun linna' : 'Turku Castle',
        #'Hämeen linna' : 'Häme Castle',
        #'Olavinlinna' : 'Olavinlinna'
        #'Raaseporin linna' : 'Raseborg castle',
        #'Hvitträsk': 'Hvitträsk'
        #'kiväärit' : 'Rifles'
    }

    # can we determine automatically "in", "at", "from" or "of" for more genericity?
    # aircraft may be "in" country or city, or "at" airport..
    #
    # also it might not be only prefix but as postfix e.g. "black and white photographs of buses in finland"
    # -> need to improve lookup of the cat hierarchy
    subject_categories_with_country = {
        #'professorit': 'Professors from',
        #'kauppaneuvokset' : 'Businesspeople from',
        #'toimitusjohtajat' : 'Businesspeople from',
        #'miehet' : 'Men of',
        #'naiset' : 'Women of',
        #'perheet' : 'Families of',
        #'miesten puvut': 'Men wearing suits in',
        #'muotinäytökset' : 'Fashion shows in',
        #'lentonäytökset': 'Air shows in',
        #'veturit' : 'Locomotives of',
        #'junat' : 'Trains of',
        #'junanvaunut' : 'Railway coaches of',
        #'rautatieasemat' : 'Train stations in',
        #'laivat' : 'Ships in',
        #'veneet' : 'Boats in',
        #'matkustajalaivat' : 'Passenger ships in',
        #'purjeveneet' : 'Sailboats in',
        #'moottoriveneet' : 'Motorboats in',
        #'lossit' : 'Cable ferries in',
        #'lentokoneet' : 'Aircraft in',
        #'moottoripyörät' : 'Motorcycles in',
        #'moottoripyöräurheilu' : 'Motorcycle racing in',
        #'moottoriurheilu' : 'Motorsports in',
        #'linja-autot': 'Buses in',
        #'kuorma-autot' : 'Trucks in',
        #'autot' : 'Automobiles in',
        #'henkilöautot' : 'Automobiles in',
        #'autourheilu' : 'Automobile racing in',
        #'autokilpailut' : 'Automobile races in',
        #'auto-onnettomuudet' : 'Automobile accidents in',
        #'hotellit' : 'Hotels in',
        #'kodit' : 'Accommodation buildings in',
        #'asuinrakennukset' : 'Houses in',
        #'liikerakennukset' : 'Buildings in',
        #'kerrostalot' : 'Apartment buildings in',
        #'osuusliikkeet' : 'Consumers\' cooperatives in',
        #'saunat' : 'Sauna buildings in',
        #'nosturit' : 'Cranes in',
        #'kaivinkoneet' : 'Excavators in',
        #'tehtaat' : 'Factories in',
        #'teollisuusrakennukset' : 'Factories in',
        #'konepajateollisuus' : 'Machinery industry in',
        #'paperiteollisuus' : 'Pulp and paper industry in',
        #'sahateollisuus' : 'Sawmills in',
        #'koulurakennukset' : 'School buildings in',
        #'sairaalat' : 'Hospitals in',
        #'museot' : 'Museums in',
        #'rakennushankkeet' : 'Construction in',
        #'laulujuhlat' : 'Music festivals in',
        #'festivaalit' : 'Music festivals in',
        #'rukit' : 'Spinning wheels in',
        #'meijerit' : 'Dairies in',
        #'ravintolat' : 'Restaurants in',
        #'mainoskuvat' : 'Advertisements in',
        #'koira' : 'Dogs of',
        #'hevosajoneuvot' : 'Horse-drawn vehicles in',
        #'polkupyörät' : 'Bicycles in',
        #'aikakauslehdet' : 'Magazines of',
        # sanomalehtipaperi
        #'sanomalehdet' : 'Newspapers of',
        #'ammattikoulutus' : 'Vocational schools in',
        #'salmet' : 'Straits of',
        #'uimarannat' : 'Beaches of',
        #'uimapuvut' : 'Swimwear in',
        #'kylvö' : 'Agriculture in',
        #'peltoviljely' : 'Agriculture in',
        #'maanviljely' : 'Agriculture in',
        #'maatalous' : 'Agriculture in',
        #'uitto' : 'Timber floating in',
        #'uittorännit' : 'Timber floating in',
        # retkeilyalueet, retkeilyvarusteet
        #'retkeily' : 'Camping in'
    }
    
    extracatstoadd = list()

    subjectlist = getFinnaSubjects(finnarecord)
    if (subjectlist == None or len(subjectlist) == 0):
        print("no subjects in finna record")
        return extracatstoadd

    placeslist = getFinnaPlaces(finnarecord)

    # TODO: list can have places without country
    isInFinland = False
    for t in placeslist:
        if ('Suomi' in t):
            isInFinland = True

    isInPortraits = False
    for subject in subjectlist:
        #print("DEBUG: subject '", subject ,"' in finna record")

        if (subject == 'muotokuvat' or subject == 'henkilökuvat'):
            isInPortraits = True

        if subject in subject_categories:
            cattext = subject_categories[subject]
            
            if cattext not in extracatstoadd: # avoid duplicates
                extracatstoadd.append(cattext)

    if (findcatwithphrase("Portrait photographs", existingcategories) == False):
        if (isInPortraits == True and isInFinland == True):
            if 'miehet' in subjectlist:
                extracatstoadd.append("Portrait photographs of men of Finland")
            if 'naiset' in subjectlist:
                extracatstoadd.append("Portrait photographs of women of Finland")
            if ('Portrait photographs of men of Finland' not in extracatstoadd and 'Portrait photographs of women of Finland' not in extracatstoadd):
                extracatstoadd.append("Portrait photographs of Finland")
        elif (isInPortraits == True):
            extracatstoadd.append("Portrait photographs")

    #if (isInPortraits == True):
        #print("DEBUG: extra cats for portraits: ", str(extracatstoadd))

    if (inceptiondt != None):
        # only use year if we are confident it is at least one year:
        # we need a better detection when year is only decade or century..
        if (inceptiondt.year != 0 and inceptiondt.precision < 0):
            if (isInPortraits == True and isInFinland == True):
                extracatstoadd.append(f'People of Finland in {inceptiondt.year}')
            if (isInPortraits == True):
                extracatstoadd.append(f'{inceptiondt.year} portrait photographs')
            #print("DEBUG: extra cats with year: ", str(extracatstoadd))

    if (placeslist == None or len(placeslist) == 0):
        print("no places in finna record")
        return extracatstoadd
    if isInFinland == False:
        print("Suomi not found in places in finna record")
        return extracatstoadd
    
    # if existing categories has already more accurate category
    # like "Aircraf in Helsinki" don't add broader "Aircraft in Finland"
    #if (existingcategories
    
    for subject in subjectlist:
        #print("DEBUG: subject '", subject ,"' in finna record")
        if subject in subject_categories_with_country: # skip unknown tags
            cattext = subject_categories_with_country[subject]
            if (findcatwithphrase(cattext, existingcategories) == False):
                if cattext not in extracatstoadd: # avoid duplicates
                    # TODO: get from placeslist appropriate location
                    cattext = cattext + " " + "Finland"
                    
                    extracatstoadd.append(cattext)

    print("DEBUG: extra cats to add: ", str(extracatstoadd))
    return extracatstoadd

# list may have "Suomi, <place>" in as single string
# -> check each if it can be split and has given string
def isplaceinlistparts(place, placeslist):
    for p in placeslist:
        partlist = p.split(",")
        for t in partlist:
            if (trimlr(t) == place):
                print("DEBUG: found ", t)
                return True
    return False

def get_category_place(placeslist):
    # for now, use hack to translate into category
    if ('Nokia' in placeslist):
        return "Nokia, Finland"
    if ('Maarianhamina' in placeslist):
        return "Mariehamn"
    if ('Viipuri' in placeslist):
        return "Vyborg"
    
    # places with year/decade templates
    cat_place = {
        "Helsinki","Hanko","Hamina","Heinola","Hyvinkää","Hämeenlinna","Espoo","Forssa","Iisalmi","Imatra","Inari","Joensuu","Jyväskylä","Jämsä","Kaarina","Kajaani","Kauhajoki","Kerava","Kemi","Kokkola","Kotka","Kuopio","Kuusamo","Kouvola","Lahti","Lappajärvi","Lappeenranta","Lohja","Loviisa","Mikkeli","Naantali","Pietarsaari","Porvoo","Pori","Pornainen","Oulu","Raahe","Raisio","Rauma","Rovaniemi","Salo","Savonlinna","Seinäjoki","Siilinjärvi","Sipoo","Sotkamo","Turku","Tampere","Tornio","Uusikaupunki","Vantaa","Vaasa","Virolahti"
    }
    for p in cat_place:
        if (isplaceinlistparts(p, placeslist) == True):
            return p
        
    if 'Suomi' in placeslist:
        return "Finland"
    return ""

def getcategoriesforplaceandtime(pywikibot, finna_record, inceptiondt, placeslist, existingcategories):
    extracatstoadd = list()
    print("DEBUG: testing cats for time and place")
    
    # TODO: add only location name if we can't determine year?
    if (inceptiondt == None):
        print("DEBUG: no timestamp")
        return extracatstoadd
    if (inceptiondt.year == 0):
        print("DEBUG: no year")
        return extracatstoadd
    if (len(placeslist) == 0):
        print("DEBUG: no places")
        return extracatstoadd

    # for now, we don't have anything do with here in this case..
    # TODO: may have "Suomi, <place>" in the list as single entry..
    if (isplaceinlistparts("Suomi", placeslist) == False):
        print("DEBUG: Finland isn't included in places")
        return extracatstoadd
    
    # TODO: placelist might have a string like "Suomi, Espoo" 
    # which would need to be split accordingly..
    # it also might have "Suomi, Uusimaa, Espoo" or simply "Uusikaupunki"
    # or "entinen kunta/pitäjä, <place>"
    place = get_category_place(placeslist)
    if (len(place) == 0):
        print("DEBUG: unnkown place:", str(placeslist))
        return extracatstoadd

    # note: might need to check the year
    # in case it is for decade instead of exact year..
    yearstr = str(inceptiondt.year)
    cattext = yearstr + " in " + place

    # already has exact cat
    if (findcatwithphrase(cattext, existingcategories) == True):
        return extracatstoadd

    # cat with part of it being same location? 
    # -> maybe a combination class -> skip it
    if (findcatwithphrase(place, existingcategories) == True):
        return extracatstoadd

    # category with same year?
    # -> maybe combination class -> skip it
    if (findcatwithphrase(yearstr, existingcategories) == True):
        return extracatstoadd

    # category with same year but more generic location?
    # -> could replace with a more specific category
    catgeneric = yearstr + " in Finland"
    if ('Suomi' in placeslist and findcatwithphrase(catgeneric, existingcategories) == True):
        return extracatstoadd

    # otherwise might be safe to add the category now
    extracatstoadd.append(cattext)
    print("Adding cat for time and place:", cattext)
    return extracatstoadd

# when you need a category but there is no collection in data (museum of finnish architecture)
#extracatstoadd = getcategoriesforinstitutions(pywikibot, d_institutionqtocategory, finna_record)
def getcategoriesforinstitutions(pywikibot, institutionqtocategory, pubqcode, opqcode):
    extracatstoadd = list()

    #for pub in pubqcode:
    if pubqcode in institutionqtocategory: # skip unknown tags
        cattext = institutionqtocategory[pubqcode]
        if cattext not in extracatstoadd: # avoid duplicates
            extracatstoadd.append(cattext)

    #for op in opqcode:
    if opqcode in institutionqtocategory: # skip unknown tags
        cattext = institutionqtocategory[opqcode]
        if cattext not in extracatstoadd: # avoid duplicates
            extracatstoadd.append(cattext)

    return extracatstoadd

# lookup category names by collection qcodes
#
def getcategoriesforcollections(pywikibot, categories, collectiontocategory):

    collcatstoadd = list()

    for catq in categories:
        if catq in collectiontocategory:
            cattext = collectiontocategory[catq]
            if cattext not in collcatstoadd: # avoid duplicates
                collcatstoadd.append(cattext)

    return collcatstoadd

# add categories for each collection to the commons-page if they don't yet exist.
# lookup text by qcode (parsed from finna record)
#
def addCategoriesToCommons(pywikibot, tmptext, categories):
    catsadded = False
    for cattext in categories:
        tmp = "[[Category:" + cattext + "]]"
        
        if (tmptext.find(tmp) < 0):
            print("DEBUG: adding category: ", tmp)
            
            if (tmptext.endswith("\n") == False):
                tmptext += "\n" # avoid same line when missing linefeed
                
            tmptext += tmp
            tmptext += "\n"
            catsadded = True

    return catsadded, tmptext

# list existing categories in commons wikitext
# (ignore those coming from templates or wikidata now)
def listExistingCommonsCategories(oldtext):
    #oldtext = page.text()
    catsfound = list()
    
    indexBegin = 0
    while (indexBegin >= 0 and indexBegin <= len(oldtext)):
        indexTmp = oldtext.find("[[Category:", indexBegin)
        if (indexTmp > 0):
            indexTmp = oldtext.find(":", indexTmp) + 1
            indexEnd = oldtext.find("]]", indexTmp)
            if (indexEnd < 0):
                # incomplete category-marking
                break

            cattext = oldtext[indexTmp:indexEnd]
            catsfound.append(cattext)
            #print("DEBUG: category found: " + cattext)
            indexBegin = indexEnd
        else:
            # no more catgories
            indexBegin = indexTmp
            break
    print("DEBUG: existing categories found: " + str(catsfound))
    return catsfound


def isSupportedMimetype(strmime):
    if (strmime.find("audio") >= 0 
        or strmime.find("ogg") >= 0 
        or strmime.find("/svg") >= 0 
        or strmime.find("/pdf") >= 0 
        or strmime.find("image/vnd.djvu") >= 0
        or strmime.find("video") >= 0):
        return False
    return True

# filter blocked images that can't be updated for some reason
def isblockedimage(page):
    pagename = str(page)

    # if there is svg file for some reason -> skip it
    if (pagename.find(".svg") >= 0):
        return True
    if (pagename.find(".pdf") >= 0):
        return True

    # Python throws error due to large size of the image.
    # We can only skip it for now..
    if (pagename.find("Sotavirkailija Kari Suomalainen.jpg") >= 0):
        return True

    # no blocking currently here
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
                if isblockedimage(subpage) == False: 
                    if subpage not in final_pages: # avoid duplicates
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
        if isblockedimage(linked_page) == False: 
            if linked_page not in pages: # avoid duplicates
                pages.append(linked_page)

    return pages

# list of newest pages in given category
def getnewestpagesfromcategory(pywikibot, commonssite, maincat, limit=100):

    cat = pywikibot.Category(commonssite, maincat)
    newest = cat.newest_pages(limit)
    
    pages = list()
    for page in newest:
        #print("name: ", page.title())
        fp = pywikibot.FilePage(commonssite, page.title())
        pages.append(fp)
    return pages

def getuseruploads(commonssite, username, limit=100):
    user = pywikibot.User(commonssite, username)
    contribs = user.contributions(total=limit)  # Get the user's last 5000 edits

    uploadsummary = ''
    for contrib in contribs:
        uploadsummary += str(contrib) + "\n"
    return uploadsummary
    

# different method to parse links
#
#def getdumplistpage(pywikibot, commonssite, linkpage):
    #listpage = pywikibot.Page(commonssite, linkpage)  # The page you're interested in


# simply to aid in debuggimg
def getpagesfixedlist(pywikibot, commonssite):
    pages = list()
    #fp = pywikibot.FilePage(commonssite, 'File:Seppo Lindblom 1984.jpg')

    # objectId = 624337
    #fp = pywikibot.FilePage(commonssite,"File:Helene Schjerfbeck (1862-1946)- The Convalescent - Toipilas - Konvalescenten (32721924996).jpg")
    
    # wikidata Q20771282 accession number A I 36:4
    #fp = pywikibot.FilePage(commonssite, 'File:Magnus von Wright - Katajanokka, luonnos - A I 36-4 - Finnish National Gallery.jpg')
    
    
    #fp = pywikibot.FilePage(commonssite, 'File:Tulppaani nurmialueella Suvilahdessa by Sakari Kiuru 2020.tiff')
    
    
    # TEST: file removed?
    #fp = pywikibot.FilePage(commonssite, 'File:Satu Pentikäinen 1980.jpg')
    #fp = pywikibot.FilePage(commonssite, 'File:Vaasan kaupunginlääkäri, taiteenkerääjä ja -lahjoittaja Karl Hedman.tiff')
    #fp = pywikibot.FilePage(commonssite, 'File:Veikko Vennamo-1970s.jpg')
    #fp = pywikibot.FilePage(commonssite, 'File:Tiny ticket sale kiosk in Seurasaari, Helsinki, Finland, 2023 July.jpg')
    #fp = pywikibot.FilePage(commonssite, "File:'Kauppakartano' mall in Korso, Vantaa, Finland, 2022.jpg")

    #fp = pywikibot.FilePage(commonssite, "File:Bikers in Helsinki 1940 (2516C; JOKAHBL3C A51-2).tif")


    #fp = pywikibot.FilePage(commonssite, "File:Customers in Elanto grocery store 1951 (2573E; JOKAHBL3D B05-2).tif")

    #fp = pywikibot.FilePage(commonssite, "The workshop of Veljekset Åström Oy 1934 (JOKAKAL3B-3634).tif")

    #fp = pywikibot.FilePage(commonssite, 'File:Antti Kosolan orkesteri Lancastria-laivan kannella.jpg')
#    fp = pywikibot.FilePage(commonssite, 'File:Munkkiniemi, Kuusisaari.jpg')

#    fp = pywikibot.FilePage(commonssite, 'File:Alvar Cawén - The Convalescent - A IV 4283 - Finnish National Gallery.jpg')


    #fp = pywikibot.FilePage(commonssite, 'File:Helene Schjerfbeck - Hjördis.jpg')
    #fp = pywikibot.FilePage(commonssite, 'File:Haavoittunut soturi hangella by Helena Schjerfbeck 1880.jpg')
    #fp = pywikibot.FilePage(commonssite, 'File:Akseli Gallen-Kallela -Taos Home in Moonlight.jpg')

    #fp = pywikibot.FilePage(commonssite, 'File:Helene Schjerfbeck - The Door - A IV 3680 - Finnish National Gallery.jpg')

    #fp = pywikibot.FilePage(commonssite, 'File:Axel Gustav Estlander.jpg')



    pages.append(fp)
    return pages


# brute force check if wikibase exists for structured data:
# need to add it manually for now if it doesn't
def doessdcbaseexist(page):
    try:
        wditem = page.data_item()  # Get the data item associated with the page
        #if (wditem.exists() == False):
        data = wditem.get() # all the properties in json-format
        return True # no exception -> ok, we can use it
    except:
        print("WARN: failed to retrieve structured data")

    return False

# just catch exceptions
def getfilepage(pywikibot, page):
    try:
        return pywikibot.FilePage(page)
        #if (filepage.latest_file_info == None):
            #print("WARN: no info available for filepage")
        
        # see that we can access this: if file has been removed throws exception
        #file_info = filepage.latest_file_info
        #return filepage
    except:
        print("ERROR: failed to retrieve filepage: " + page.title())

    return None


def verifyTeosIdInSdc(claims, page, fngcache):
    kgteosid = getKansallisgalleriateosFromSdc(claims)
    if (kgteosid != None):
        fnginv = fngcache.findbyid(kgteosid)
        if (fnginv == None):
            print("WARN: SDC has object id", kgteosid ," which does not exist in database for page", page.title())
            return False
    return True

# try some sanitizing of the id in case of weird descriptions/bugs
def checkcleanupfinnaid(finnaid, page):
    if (len(finnaid) >= 50):
        print("WARN: finna id in " + page.title() + " is unusually long? bug or garbage in url? ")
        
    if (len(finnaid) <= 5):
        print("WARN: finna id in " + page.title() + " is unusually short? bug or garbage in url? ")
        
    # just for logging what is wrong
    if (finnaid.find("?") > 0 or finnaid.find("&") > 0 or finnaid.find("<") > 0 or finnaid.find(">") > 0 or finnaid.find("#") > 0 or finnaid.find("[") > 0 or finnaid.find("]") > 0 or finnaid.find("{") > 0 or finnaid.find("}") > 0):
        print("WARN: finna id in " + page.title() + " has unexpected characters, bug or garbage in url? ")
        
        # remove strange charaters and stuff after if any
        finnaid = stripid(finnaid)
        print("note: finna id in " + page.title() + " is " + finnaid)

    if (finnaid.find("\n") > 0):
        print("WARN: removing newline from: " + page.title())
        finnaid = leftfrom(finnaid, "\n")
        
    if (finnaid.endswith("\n")):
        print("WARN: finna id in " + page.title() + " ends with newline ")
        finnaid = finnaid[:len(finnaid)-1]
    return finnaid

# ------ main()

# institutions maintaining collection(s)
#
d_institutionqcode = dict()
d_institutionqcode["Museovirasto"] = "Q3029524"
d_institutionqcode["Sotamuseo"] = "Q283140"
d_institutionqcode["Sibelius-museon arkisto"] = "Q4306382"
d_institutionqcode["Sibelius-museo"] = "Q4306382"
d_institutionqcode["Suomen valokuvataiteen museo"] = "Q11895148"
d_institutionqcode["Suomen Ilmailumuseo"] = "Q1418126"
d_institutionqcode["Suomen kansallismuseo"] = "Q1418136"
    
# or Kansallisgalleria / Ateneumin taidemuseo
d_institutionqcode["Kansallisgalleria"] = "Q2983474"
d_institutionqcode["Kansallisgalleria Arkistokokoelmat"] = "Q2983474"
d_institutionqcode["Kansallisgalleria/Arkisto ja kirjasto"] = "Q2983474"
d_institutionqcode["Ateneumin taidemuseo"] = "Q754507"
d_institutionqcode["Sinebrychoffin taidemuseo"] = "Q1393952"
d_institutionqcode["Tekniikan museo"] = "Q5549583"
d_institutionqcode["Museokeskus Vapriikki"] = "Q18346706"
d_institutionqcode["Varkauden museokeskus Konsti"] = "Q126368681"
d_institutionqcode["Helsingin kaupunginmuseo"] = "Q2031357"
d_institutionqcode["Helsinki City Museum"] = "Q2031357"
d_institutionqcode["HKM Valokuva"] = "Q2031357"
d_institutionqcode["HKM"] = "Q2031357"

d_institutionqcode["Vantaan kaupunginmuseo"] = "Q26723704"
d_institutionqcode["Keravan museopalvelut"] = "Q121266100"
d_institutionqcode["Turun museokeskus"] = "Q18346797"
d_institutionqcode["The Museum Centre of Turku"] = "Q18346797"
d_institutionqcode["Työväenmuseo Werstas"] = "Q11899172"
d_institutionqcode["Työväen Arkisto"] = "Q11899166"
d_institutionqcode["Satakunnan Museo"] = "Q6304688"
d_institutionqcode["Lusto - Suomen Metsämuseo"] = "Q11879901"
d_institutionqcode["Lusto – Suomen Metsämuseo"] = "Q11879901"
d_institutionqcode["Suomen Metsästysmuseo"] = "Q1678320"
d_institutionqcode["Svenska litteratursällskapet i Finland"] = "Q769544"
d_institutionqcode["Lappeenrannan museot"] = "Q58636578"
d_institutionqcode["Hyvinkään kaupunginmuseo"] = "Q41776741"
d_institutionqcode["Helsingin yliopistomuseo"] = "Q3329065"
d_institutionqcode["Suomen Rautatiemuseo"] = "Q1138355"
d_institutionqcode["Salon historiallinen museo"] = "Q56403058"
d_institutionqcode["Etelä-Karjalan museo"] = "Q18346681"
d_institutionqcode["ETELÄ-KARJALAN MUSEO"] = "Q18346681"
d_institutionqcode["Pohjois-Karjalan museo"] = "Q11888467"
d_institutionqcode["Kymenlaakson museo"] = "Q18346674"
d_institutionqcode["Pielisen museo"] = "Q11887930"
d_institutionqcode["Forssan museo"] = "Q23040125"
d_institutionqcode["Suomen käsityön museo"] = "Q18346792"
d_institutionqcode["Aalto-yliopiston arkisto"] = "Q300980"
d_institutionqcode["Kokemäen maatalousmuseo"] = "Q11872136"
d_institutionqcode["Suomen maatalousmuseo Sarka"] = "Q11895074"
d_institutionqcode["Maaseudun sivistysliitto"] = "Q11880431"
d_institutionqcode["Ilomantsin museosäätiö"] = "Q121266098"
d_institutionqcode["Lapin maakuntamuseo"] = "Q18346675"
d_institutionqcode["Uudenkaupungin museo"] = "Q58636637"
d_institutionqcode["Kuopion kulttuurihistoriallinen museo"] = "Q58636575"
d_institutionqcode["KUOPION KULT. HIST. MUSEO"] = "Q58636575"
d_institutionqcode["Varkauden museot"] = "Q58636646"
d_institutionqcode["Keski-Suomen museo"] = "Q11871078"
d_institutionqcode["Nurmeksen museo"] = "Q18661027"
d_institutionqcode["Lahden museot"] = "Q115322278"
d_institutionqcode["Postimuseo"] = "Q5492225"
d_institutionqcode["Nuorisotyön tallentaja Nuoperi"] = "Q125428627"
d_institutionqcode["Arkkitehtuurimuseo"] = "Q1418116" # MFA
d_institutionqcode["Tuusulan museo"] = "Q58636633"

# qcode of collections -> label
#
d_labeltoqcode = dict()
d_labeltoqcode["Studio Kuvasiskojen kokoelma"] = "Q118976025"
d_labeltoqcode["Historian kuvakokoelma"] = "Q107388072" # /Museovirasto/Historian kuvakokoelma/
d_labeltoqcode["Valokuvaamo Pietisen kokoelma"] = "Q120728209" 
d_labeltoqcode["Suomen merimuseon kuvakokoelma"] = "Q123272489" 
d_labeltoqcode["JOKA Journalistinen kuva-arkisto"] = "Q113292201"
d_labeltoqcode["Pekka Kyytisen kokoelma"] = "Q123308670"
d_labeltoqcode["Kansatieteen kuvakokoelma"] = "Q123308681"
d_labeltoqcode["Rakennushistorian kuvakokoelma"] = "Q123308774"
d_labeltoqcode["Lentokuva Hannu Vallaksen kokoelma"] = "Q123311165"
d_labeltoqcode["Antellin kokoelmat"] = "Q123313922"
d_labeltoqcode["Antellin kokoelma"] = "Q123313922"
d_labeltoqcode["Scan-Foton ilmakuvakokoelma"] = "Q123458587"
d_labeltoqcode["Scan-Foto"] = "Q123458587"
d_labeltoqcode["Foto Roosin kokoelma"] = "Q126078977"
d_labeltoqcode["Kosken kuvaamo"] = "Q126095096"
d_labeltoqcode["Börje Sandbergin kokoelma"] = "Q123357635"
d_labeltoqcode["Enckellin kokoelma"] = "Q123357692"
d_labeltoqcode["Karjalaisen osakunnan kokoelma"] = "Q123357711"
d_labeltoqcode["V. K. Hietasen kokoelma"] = "Q123357725"
d_labeltoqcode["Samuli Paulaharjun kokoelma"] = "Q123357749"
d_labeltoqcode["F. E. Fremlingin kokoelma"] = "Q123357911"
d_labeltoqcode["Markku Lepolan kokoelma"] = "Q123358422"
d_labeltoqcode["Eero Saurin kokoelma"] = "Q123365328"
d_labeltoqcode["Uuno Peltoniemen kokoelma"] = "Q123378273"
d_labeltoqcode["UA Saarisen kokoelma"] = "Q123383695"
d_labeltoqcode["Kari Pulkkisen kokoelma"] = "Q123396656"
d_labeltoqcode["Lauri Sorvojan kokoelma"] = "Q123397451"
d_labeltoqcode["Matti Tapolan kokoelma"] = "Q123398725"
d_labeltoqcode["Hannu Lindroosin kokoelma"] = "Q123398791"
d_labeltoqcode["Helge Heinosen kokoelma"] = "Q123398858"
d_labeltoqcode["Helge W. Heinosen kokoelma"] = "Q123398858"
d_labeltoqcode["Valokuvaamo Jäniksen kokoelma"] = "Q123396641"
d_labeltoqcode["Yleisetnografinen kuvakokoelma"] = "Q122414127"
d_labeltoqcode["Suomalais-ugrilainen kuvakokoelma"] = "Q123358672"
d_labeltoqcode["Suomalais-Ugrilaisen Seuran kokoelma"] = "Q125974815"
d_labeltoqcode["Fazerin konserttitoimiston kokoelma"] = "Q123378084"
d_labeltoqcode["Numismaattiset kokoelmat"] = "Q123390334"
d_labeltoqcode["Matkailun edistämiskeskuksen kokoelma"] = "Q123463484"
d_labeltoqcode["Osuusliike Elannon kokoelma"] = "Q123463766"
d_labeltoqcode["Salon Strindberg"] = "Q123439974"
d_labeltoqcode["Seppo Konstigin kokoelma"] = "Q123457977"
d_labeltoqcode["Urpo Rouhiaisen kokoelma"] = "Q123457996"
d_labeltoqcode["Sari Gustafssonin kokoelma"] = "Q123458004"
d_labeltoqcode["Jukka Kuusiston kokoelma"] = "Q123458213"
d_labeltoqcode["Veijo Laineen kokoelma"] = "Q123458458"
d_labeltoqcode["Atte Matilaisen kokoelma"] = "Q123531731"
d_labeltoqcode["Kustannusosakeyhtiö Otavan kokoelma"] = "Q123502566"
d_labeltoqcode["Otava"] = "Q123502566"
d_labeltoqcode["Otavamedia"] = "Q123502645"
d_labeltoqcode["Kaleva"] = "Q123508471"
d_labeltoqcode["Hufvudstadsbladet"] = "Q123508495"
d_labeltoqcode["Helsingin Sanomat"] = "Q123508499"
d_labeltoqcode["Turun Sanomat"] = "Q123508529"
d_labeltoqcode["Maaseudun Tulevaisuus"] = "Q123508530"
d_labeltoqcode["Itä-Häme"] = "Q123508537"
d_labeltoqcode["Uusi Suomi"] = "Q123508540"
d_labeltoqcode["Uusi Suomi − Iltalehti"] = "Q123508540"
d_labeltoqcode["Östnyland"] = "Q123508541"
d_labeltoqcode["Östnyland Borgåbladet"] = "Q123508541"
d_labeltoqcode["Västra Nyland"] = "Q124670813"
d_labeltoqcode["Satakunnan Kansan kuva-arkisto"] = "Q123508726"
d_labeltoqcode["Suomen Lähetysseura ry:n kuvakokoelma"] = "Q123508491"
d_labeltoqcode["Hyvinkään kaupunginmuseon kokoelma"] = "Q123508767"
d_labeltoqcode["Hyvinkään kaupunginmuseon valokuvakokoelma"] = "Q123508767"
d_labeltoqcode["Sote-kokoelma"] = "Q123508776"
d_labeltoqcode["VR:n kuvakokoelma"] = "Q123508783"
d_labeltoqcode["Suomen Rautatiemuseon kuvakokoelma"] = "Q123508786"
d_labeltoqcode["Arkeologian kuvakokoelma"] = "Q123508795"
d_labeltoqcode["Meriarkeologian kuvakokoelma"] = "Q126020900"
d_labeltoqcode["Hugo Simbergin valokuvat"] = "Q123523516"
d_labeltoqcode["I K Inha"] = "Q123555486"
d_labeltoqcode["Valokuvaamo Atelier Nyblinin kokoelma"] = "Q126002123"
d_labeltoqcode["Collianderin kokoelma"] = "Q123694615"
d_labeltoqcode["Heikki Y. Rissasen kokoelma"] = "Q123699187"
d_labeltoqcode["Jaakko Julkusen kokoelma"] = "Q123746517"
d_labeltoqcode["Wiipuri-kokoelma"] = "Q123523357"
d_labeltoqcode["Wiipuri-museon kokoelma"] = "Q123523357"
d_labeltoqcode["Kulutusosuuskuntien Keskusliitto"] = "Q123555033"
d_labeltoqcode["Kulutusosuuskuntien Keskusliiton kokoelma"] = "Q123555033"
d_labeltoqcode["Kulutusosuuskuntien Keskusliitto (KK)"] = "Q123555033"
d_labeltoqcode["Rafael Olins fotosamling"] = "Q123563819"
d_labeltoqcode["Kuurojen museo"] = "Q58685161"
d_labeltoqcode["Vankilamuseon kokoelma"] = "Q123699925"
d_labeltoqcode["TKA Kanninen"] = "Q123700007"
d_labeltoqcode["Turun linnan kuvakokoelma"] = "Q123734837"
d_labeltoqcode["Valokuvat ITE Uusimaaseutu"] = "Q123746149"
d_labeltoqcode["Ilomantsin valokuva-arkisto"] = "Q123749213"
d_labeltoqcode["Runebergbibliotekets bildsamling"] = "Q123915494"
d_labeltoqcode["István Ráczin kokoelma"] = "Q123964511"
d_labeltoqcode["Melissa Hanhirova - Helsinki Pride kokoelma"] = "Q107388083"
d_labeltoqcode["Kai Honkasen kokoelma"] = "Q123976124"
d_labeltoqcode["Niilo Tuuran kokoelma"] = "Q123982549"
d_labeltoqcode["Collanin kokoelma"] = "Q123982572"
d_labeltoqcode["Göran Schildts arkiv"] = "Q123986127"
d_labeltoqcode["VSO-kokoelma"] = "Q123989767"
d_labeltoqcode["Ugin museon valokuvakokoelma"] = "Q123989773"
d_labeltoqcode["Keijo Laajiston kokoelma"] = "Q123991088"
d_labeltoqcode["Heikki Innasen kokoelma"] = "Q124061515"
d_labeltoqcode["Meritalon museon valokuvakokoelma"] = "Q124088603"
d_labeltoqcode["Artur Faltinin kokoelma"] = "Q124124102"
d_labeltoqcode["Tapio Kautovaaran kokoelma"] = "Q124157066"
d_labeltoqcode["Anna-Liisa Nupponen"] = "Q124157465"
d_labeltoqcode["Urpo Häyrisen kokoelma"] = "Q124254475"
d_labeltoqcode["Yrjö Yli-Vakkurin kokoelma"] = "Q124608095"
d_labeltoqcode["Yleinen merivartiokokoelma"] = "Q124288898"
d_labeltoqcode["Postimuseon kokoelmat"] = "Q124288911"
d_labeltoqcode["Mobilia kuvat"] = "Q124325340"
d_labeltoqcode["Karjalan Liiton kokoelma"] = "Q124289082"
d_labeltoqcode["Helsingin kaupunginmuseon kuvakokoelma"] = "Q124299286"
d_labeltoqcode["HKM Valokuva"] = "Q124299286"
d_labeltoqcode["Vilho Uomalan kokoelma"] = "Q124672017"
d_labeltoqcode["Pressfoto Zeeland"] = "Q125141028"
d_labeltoqcode["Nuoperin valokuvakokoelma"] = "Q125428578"
d_labeltoqcode["Ylä-Karjalan kuva-arkisto"] = "Q125429017"
d_labeltoqcode["Seurasaaren kuvakokoelma"] = "Q126021273"
d_labeltoqcode["S. E. Multamäen kokoelma"] = "Q125946755"
d_labeltoqcode["Metsätehon kokoelma"] = "Q125947321"
d_labeltoqcode["Hämeen linnan kuvakokoelma"] = "Q125980519"
d_labeltoqcode["Olavinlinnan kuvakokoelma"] = "Q125980786"
d_labeltoqcode["Juha Lankisen kokoelma"] = "Q125994258"
d_labeltoqcode["Kuva-arkisto"] = "Q125995005" # lappeenrannan/etelä-karjalan museon
d_labeltoqcode["Korttikeskuksen kokoelma"] = "Q126101695"
d_labeltoqcode["Kustannusosakeyhtiö Kiven kokoelma"] = "Q126160418"
d_labeltoqcode["Aarne Mikonsaari"] = "Q126162086"
d_labeltoqcode["LPR kaupungin kuva-arkisto"] = "Q126162424"
d_labeltoqcode["Kulttuuriympäristön kuvakokoelma"] = "Q126163175"
d_labeltoqcode["Digikuvakokoelma"] = "Q126173053"
d_labeltoqcode["Valokuvat/KUV/KV"] = "Q126177397"
d_labeltoqcode["Diat/KUV/KD"] = "Q126193435"
d_labeltoqcode["Heikki Havaksen negatiivikokoelma"] = "Q126201599"
d_labeltoqcode["Timo Kirveen kokoelma"] = "Q126210138"


# collection qcode (after parsing) to commons-category
#
d_collectionqtocategory = dict()
d_collectionqtocategory["Q113292201"] = "JOKA Press Photo Archive"
d_collectionqtocategory["Q123508786"] = "Collections of the Finnish Railway Museum"
d_collectionqtocategory["Q123272489"] = "Media by The Maritime Museum of Finland" # Suomen merimuseon kuvakokoelma

#d_collectionqtocategory["Q107388072"] = "Historical Picture Collection" # Historian kuvakokoelma
d_collectionqtocategory["Q107388072"] = "Historical Picture Collection of The Finnish Heritage Agency" # Historian kuvakokoelma

#d_collectionqtocategory["Q123308681"] = "Ethnographic Picture Collection" # Kansatieteen kuvakokoelma
d_collectionqtocategory["Q123308681"] = "Ethnographic Picture Collection of The Finnish Heritage Agency" # Kansatieteen kuvakokoelma

#d_collectionqtocategory["Q123308774"] = "Architectural History Collection" # Rakennushistorian kokoelma
d_collectionqtocategory["Q123308774"] = "Architectural History Collection of The Finnish Heritage Agency" # Rakennushistorian kokoelma

#d_collectionqtocategory["Q123358672"] = "Finno-Ugric Picture Collection" # Suomalais-ugrilainen kuvakokoelma
d_collectionqtocategory["Q123358672"] = "Finno-Ugric Picture Collection of The Finnish Heritage Agency" # Suomalais-ugrilainen kuvakokoelma

#d_collectionqtocategory["Q122414127"] = "Ethnographic Collection" # Yleisetnografinen kuvakokoelma
d_collectionqtocategory["Q122414127"] = "Ethnographic Collection of The Finnish Heritage Agency" # Yleisetnografinen kuvakokoelma

# there are no colections in museum of architecture? -> need to determine by publisher
#d_collectionqtocategory[""] = "Files from Museum of Finnish Architecture" # 

d_collectionqtocategory["Q123508795"] = "Archeological Picture Collection" # Arkeologian kuvakokoelma
#d_collectionqtocategory["Q123508795"] = "Arkeologian kuvakokoelma" # 


# note! only add this if not already in one of the subcategories below this one
# -> TODO: check the hierarchy of categories
#d_collectionqtocategory["Q118976025"] = "Photographs by Kuvasiskot" # Studio Kuvasiskojen kokoelma

# there are no colections in museum of architecture? -> need to determine by publisher
d_institutionqtocategory = dict()
d_institutionqtocategory["Q1418116"] = "Files from Museum of Finnish Architecture" # 


# institution qcode (after parsing) to commons-template
# three institutions have the template currently..
#
d_institutionqtotemplate = dict()
d_institutionqtotemplate["Q3029524"] = "Finnish Heritage Agency" 
d_institutionqtotemplate["Q2031357"] = "Helsinki City Museum" 
d_institutionqtotemplate["Q18346797"] = "Turku Museum Centre" 
d_institutionqtotemplate["Q26723704"] = "Vantaa City Museum" 
d_institutionqtotemplate["Q41776741"] = "Hyvinkää City Museum" 
d_institutionqtotemplate["Q283140"] = "SA-Kuva" 
d_institutionqtotemplate["Q769544"] = "Society of Swedish Literature in Finland" 
d_institutionqtotemplate["Q18346681"] = "South Karelia Museum" 
d_institutionqtotemplate["Q1418116"] = "Museum of Finnish Architecture" # MFA
d_institutionqtotemplate["Q11879901"] = "Lusto" # metsämuseo


# Accessing wikidata properties and items
wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata
wikidata_site.login()

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()


# for testing only
#pages = getpagesfixedlist(pywikibot, commonssite)


# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Kuvasiskot", 2)
#pages = getcatpages(pywikibot, commonssite, "Files from the Antellin kokoelma")

#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency")
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical images of Finland", 3)
#pages = getcatpages(pywikibot, commonssite, "Category:History of Finland", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:History of Karelia", 2)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Aviation Museum")

#pages = getcatpages(pywikibot, commonssite, "Category:Lotta Svärd", True)
#pages = getcatpages(pywikibot, commonssite, "Category:SA-kuva", True)
#pages = getcatpages(pywikibot, commonssite, "Category:SA-kuva")
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finland in World War II", 3)

#pages = getcatpages(pywikibot, commonssite, "Category:Swedish Theatre Helsinki Archive", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Society of Swedish Literature in Finland", 2)

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist2')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/sakuvat')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/europeana-kuvat')

## TEST
#pages = list()

#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp1')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp2')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp3')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp4')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp5')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp6')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp7')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp8')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp9')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp10')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp11')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp12')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp13')
#pages += getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp14')


#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filesfromip')

#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/fng-kuvat')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/kansallisgalleriakuvat')

#pages = getcatpages(pywikibot, commonssite, "Category:Images uploaded from Wikidocumentaries")

# many are from valokuvataiteenmuseo via flickr
# many from fng via flickr
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical photographs of Helsinki by I. K. Inha", 1)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finnish Museum of Photography", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Files from the Finnish Museum of Photography", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Photographs by Hugo Simberg", 2)

#pages = getcatpages(pywikibot, commonssite, "Category:Finnish Agriculture (1899) by I. K. Inha")

#pages = getpagesrecurse(pywikibot, commonssite, "Files uploaded by FinnaUploadBot", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "JOKA Press Photo Archive", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by Samuli Paulaharju", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by Kuvasiskot", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by I. K. Inha", 1)

#pages = getpagesrecurse(pywikibot, commonssite, "J. E. Rosberg", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by J. E. Rosberg", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by Carl Gustaf Emil Mannerheim", 1)


pages = getpagesrecurse(pywikibot, commonssite, "Historical Picture Collection of The Finnish Heritage Agency", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Ethnographic Picture Collection of The Finnish Heritage Agency", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Ethnographic Collection of The Finnish Heritage Agency", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Media by The Maritime Museum of Finland", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Collections of the Finnish Railway Museum", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Cartes de visite in Swedish Theatre Helsinki Archive", 0)

#pages = getnewestpagesfromcategory(pywikibot, commonssite, "Files uploaded by FinnaUploadBot", 200)
#pages = getnewestpagesfromcategory(pywikibot, commonssite, "Photographs by Kuvasiskot", 50)
#pages = getnewestpagesfromcategory(pywikibot, commonssite, "Files uploaded by FinnaUploadBot", 30)

#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by Tapio Kautovaara", 0)

#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by C.P. Dyrendahl", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Photographs by Th. Nyblin", 0)


cachedb = CachedImageData() 
cachedb.opencachedb()

fngcache = CachedFngData() 
fngcache.opencachedb()

# some media info for faster handling/less transfers
micache = CachedMediainfo() 
micache.opencachedb()


rowcount = 0
#rowlimit = 10

print("Pages found: " + str(len(pages)))

for page in pages:
    rowcount += 1
    
    # 14 is category -> recurse into subcategories
    if (page.namespace() != 6):  # 6 is the namespace ID for files
        continue

    # alternative listing method is not filtered before this
    if (isblockedimage(page) == True): 
        continue

    # try to catch exceptions and return later
    filepage = getfilepage(pywikibot, page)
    if (filepage == None):
        continue
    if filepage.isRedirectPage():
        continue

    print(" ////////", rowcount, "/", len(pages), ": [ " + page.title() + " ] ////////")

    file_media_identifier='M' + str(filepage.pageid)
    file_info = filepage.latest_file_info
    oldtext = page.text
    
    # there may be other media than images as well
    strmime = str(file_info.mime)
    if (isSupportedMimetype(strmime) == False):
        print("unsupported mime-type: ", strmime, "page:", page.title())
        continue

    print("media id ", str(filepage.pageid) ," has latest change in commons: ", filepage.latest_file_info.timestamp.isoformat(), " revision change: ", filepage.latest_revision.timestamp.isoformat())

    # check when we have processed this 
    cached_info = micache.findfromcache(filepage.pageid)
    if (cached_info != None):
        print("media id ", str(filepage.pageid) ," has cached change : ", cached_info['recent'].isoformat())
        if (filepage.latest_revision.timestamp.replace(tzinfo=timezone.utc) <= cached_info['recent'].replace(tzinfo=timezone.utc)
            and filepage.latest_file_info.timestamp.replace(tzinfo=timezone.utc) <= cached_info['recent'].replace(tzinfo=timezone.utc)):
            print("skipping, page with media id ", filepage.pageid, " was processed recently ", cached_info['recent'].isoformat() ," page ", page.title())
            continue

    #item = pywikibot.ItemPage.fromPage(page) # can't use in commons, no related wikidata item
    # note: data_item() causes exception if wikibase page isn't made yet, see for an alternative
    if (fixMissingSdcData(pywikibot, wikidata_site, commonssite, file_info, page) == False):
        print("ERROR: Failed adding Wikibase item for: " + page.title() )
        exit(1)
        
    wditem = page.data_item()  # Get the data item associated with the page
    sdcdata = wditem.get() # all the properties in json-format
    if "statements" not in sdcdata:
        print("No statements found for claims: " + page.title())
        continue
    
    #wdrepo = wikidata_site.data_repository()
    claims = sdcdata['statements']  # claims are just one step from dataproperties down

    print("Wikibase statements found for: " + page.title() )
    
    if (verifyTeosIdInSdc(claims, page, fngcache) == False):
        print("WARN: SDC has invalid object id for page", page.title())
        #exit(1)

    # try to parse template in commons-page
    ct = CommonsTemplate()
    if (ct.parseTemplate(page.text) == False):
        print("WARN: problem parsing template(s) in page " + page.title())

    kg_data = KansallisgalleriaData()

    # if there are qcodes for item in wikidata -> find those from page
    wikidataqcodes = getwikidatacodefrompagetemplate(ct)
    if (len(wikidataqcodes) > 0):
        print("DEBUG: found qcodes in template for " + page.title())
        
        kg_teostunniste = getKansallisgalleriaTeostunnisteFromWikidata(pywikibot, wikidata_site, wikidataqcodes)
        fng_inventaario = getKansallisgalleriaInventaarionumeroFromWikidata(pywikibot, wikidata_site, wikidataqcodes)

        if (kg_teostunniste == None and fng_inventaario != None):
            print("DEBUG: inventory number ", fng_inventaario ," found, looking object id for ", page.title())
            fngid = fngcache.findbyacc(fng_inventaario)
            if (fngid != None):
                kg_teostunniste = str(fngid['objectid'])
                print("DEBUG: found ", kg_teostunniste ," for ", fng_inventaario)
            else:
                print("DEBUG: could not find object id for ", fng_inventaario)
        if (kg_teostunniste != None and fng_inventaario == None):
            print("DEBUG: object id ", kg_teostunniste ," found, looking inventory number for ", page.title())
            fnginv = fngcache.findbyid(kg_teostunniste)
            if (fnginv != None):
                fng_inventaario = str(fnginv['invnum'])
                print("DEBUG: found ", fng_inventaario ," for ", kg_teostunniste)
            else:
                print("DEBUG: could not find inventory number for ", kg_teostunniste)
        if (fng_inventaario != None):
            kg_data.setInventaarionumero(fng_inventaario)
        if (kg_teostunniste != None):
            kg_data.setTeostunniste(kg_teostunniste)
        kg_data.setQcode(wikidataqcodes)

    # find source urls in template(s) in commons-page
    srcurls = getsourceurlfrompagetemplate(ct)
    if (srcurls == None):
        print("DEBUG: no urls found in templates of " + page.title())
        continue
    if (len(srcurls) == 0):
        print("DEBUG: no urls found in templates of " + page.title())
        continue

    # TODO: for artworks, template has "references" field,
    # but values might be coming from wikidata and not in source data
    # -> need a different method to parse this

    refurls = getUrlsFromCommonsReferences(ct)
    if (refurls != None):
        print("DEBUG: found urls in references for " + page.title())

    kkid = ""
    finnaid = ""
    finnarecordid = ""
    fngacc = ""
    kgtid = ""

    for srcvalue in srcurls:
        if (srcvalue.find("elonet.finna.fi") > 0):
            # elonet-service differs
            continue
        
        if (srcvalue.find("fng.fi") > 0):
            # parse inventory number from old-style link
            fngacc = getfngaccessionnumberfromurl(srcvalue)
        if (srcvalue.find("kansallisgalleria.fi") > 0):
            # parse objectid from new-style link
            kgtid = getkansallisgalleriaidfromurl(srcvalue)
            
        if (srcvalue.find("kuvakokoelmat.fi") > 0):
            kkid = getkuvakokoelmatidfromurl(srcvalue)
            
        #if (srcvalue.find("europeana.eu") > 0):
            #kkid = getidfromeuropeana(srcvalue)
            
        if (srcvalue.find("finna.fi") > 0):
            # try metapage-id first
            finnarecordid = getrecordid(srcvalue)
            # try old-style/download id
            if (finnarecordid == ""):
                finnaid = getlinksourceid(srcvalue)

    if (len(kgtid) == 0 and len(fngacc) > 0):
        #print("DEBUG: searching objectid by inventory id", fngacc)
        fngid = fngcache.findbyacc(fngacc)
        if (fngid != None):
            # change to string as other python methods will need it (sdc)
            kgtid = str(fngid['objectid'])
            print("DEBUG: found objectid: ", kgtid, " for inventory number: ", fngacc)
        else:
            print("DEBUG: no objectid by inventory number", fngacc)

    if (len(kgtid) > 0 and len(fngacc) == 0):
        #print("DEBUG: searching objectid by inventory id", fngacc)
        fnginv = fngcache.findbyid(kgtid)
        if (fnginv != None):
            # change to string as other python methods will need it (sdc)
            fngacc = str(fnginv['invnum'])
            print("DEBUG: found inventory number: ", fngacc, " for object id: ", kgtid)
        else:
            print("DEBUG: no inventory number by object id", kgtid)


    if (len(fngacc) == 0 and kg_data.isValidInventaarionumero() == True):
        print("DEBUG: using inventory number", kg_data.invnum ," from wikidata")
        fngacc = kg_data.invnum

    # use what we found from wikidata
    if (len(kgtid) == 0 and kg_data.isValidTeostunniste() == True):
        print("DEBUG: using object id", kg_data.teostun ," from wikidata")
        kgtid = kg_data.teostun

    # inventory number in commons/wikidata is not matching?
    if (kg_data.isValidInventaarionumero() == True and fngacc != kg_data.invnum):
        print("WARN: inventory number mismatch", fngacc, "", kg_data.invnum)
        #fnginv = fngcache.findbyid(kg_data.teostun)
        #if (fnginv != None):
            #fngacc = str(fnginv['invnum'])

    # id in commons/wikidata is not matching?
    if (kg_data.isValidTeostunniste() == True and kgtid != kg_data.teostun):
        print("WARN: object id mismatch", kgtid, "", kg_data.teostun)
        #fngid = fngcache.findbyacc(kg_data.invnum)
        #if (fngid != None):
            #kgtid = str(fngid['objectid'])

    if (len(kgtid) > 0 and len(fngacc) > 0):
        #print("DEBUG: kansallisgalleria id found:", kgtid)
        if (fngcache.findbyid(kgtid) == None or fngcache.findbyacc(fngacc) == None):
            print("WARN: db does not have matches for", kgtid, "", fngacc)
            # may or may not be invalid, some may be missing from the data
            # and there are inventory numbers with dashes and without them randomly
            # -> we might not have every possible value
            #continue
        if (fngcache.findbyid(kgtid) != None):
            accnum = fngcache.findbyid(kgtid)
            if (accnum != None):
                tmpacc = str(accnum['invnum'])
                if (tmpacc != fngacc):
                    print("WARN: inventory numbers are different", tmpacc ," and ", fngacc)
                    # maybe we should trust our database
                    fngacc = tmpacc
        
        # should have collection Q2983474 Kansallisgalleria when adding object id
        fng_collectionqcodes = getCollectionsFromWikidata(pywikibot, wikidata_site, wikidataqcodes)
        locationqcode = getLocationFromWikidata(pywikibot, wikidata_site, wikidataqcodes)

        #isHamArtMuseum = False
        # if collection or institution or location is Q5710459 (HAM Helsingin taidemuseo)
        # the inventory number might point to different work
        # -> skip things then
        if (locationqcode == "Q5710459" or "Q5710459" in fng_collectionqcodes):
            #isHamArtMuseum = True
            print("skipping inventory/object number for HAM", page.title())
            micache.addorupdate(filepage.pageid, datetime.now(timezone.utc))
            # skip the rest as that requires finna id and finna record
            continue
        
        if (fng_collectionqcodes != None):
            print("DEBUG: found collection qcodes", fng_collectionqcodes)
            for fngcoll in fng_collectionqcodes:
                if (isFngCollectioninstatements(claims, fngcoll) == False):
                    print("DEBUG: adding collection qcode to SDC", fngcoll)
                    fng_collclaim = addFngCollectiontostatements(pywikibot, wikidata_site, fngcoll)
                    if (fng_collclaim != None):
                        wditem.addClaim(fng_collclaim)
        else:
            print("WARN: did not find collection qcode")

        if (locationqcode != None):
            if (isLocationinstatements(claims, locationqcode) == False):
                print("DEBUG: adding location qcode to SDC", locationqcode)
                locationclaim = addLocationtoStatements(pywikibot, wikidata_site, locationqcode)
                if (locationclaim != None):
                    wditem.addClaim(locationclaim)

        # if collection or institution or location is Q5710459 (HAM Helsingin taidemuseo)
        # the inventory number might point to different work
        # -> don't add these then
        if (isKansallisgalleriateosInStatements(claims, kgtid) == False):
            print("DEBUG: adding kansallisgalleria object id to SDC", kgtid)
            fo_claim = addkansallisgalleriateostosdc(pywikibot, wikidata_site, kgtid)
            if (fo_claim != None):
                wditem.addClaim(fo_claim)
            else:
                print("WARN: failed adding kansallisgalleria id", page.title())
            #if (addKansallisgalleriaIdToSdcData(pywikibot, wikidata_site, commonssite, page, kgtid) == False):
                #print("WARN: failed adding kansallisgalleria id", page.title())

        if (fng_collectionqcodes != None):
            if (isKansallisgalleriaInventorynumberInStatements(claims, fngacc) == False):
                print("DEBUG: adding kansallisgalleria inventory number to SDC", fngacc)
                fo_claim = addkansallisgalleriaInventorynumberTosdc(pywikibot, wikidata_site, fngacc, fng_collectionqcodes)
                if (fo_claim != None):
                    wditem.addClaim(fo_claim)
                else:
                    print("WARN: failed adding kansallisgalleria inventory number", page.title())

        creatorqcode = getAuthorFromWikidata(pywikibot, wikidata_site, wikidataqcodes)
        if (creatorqcode != None):
            if (isCreatorinstatements(claims, creatorqcode) == False):
                print("DEBUG: adding creator qcode to SDC", creatorqcode)
                creatorclaim = addCreatortoStatements(pywikibot, wikidata_site, creatorqcode)
                if (creatorclaim != None):
                    wditem.addClaim(creatorclaim)
                    #commonssite.addClaim(wditem, f_claim)

        # python fucks up checking for None when there are zero fields in a timestamp
        # -> force another bool
        incfound, fng_inc = getKansallisgalleriaInceptionFromWikidata(pywikibot, wikidata_site, wikidataqcodes)
        if (incfound == True):
            if (isKansallisgalleriaInceptionInStatements(claims, fng_inc) == False):
                print("DEBUG: adding inception to SDC")
                inc_claim = addkansallisgalleriaInceptionTosdc(pywikibot, wikidata_site, fng_inc)
                if (inc_claim != None):
                    wditem.addClaim(inc_claim)
            else:
                print("DEBUG: inception exists, skipping")
        else:
            print("DEBUG: inception not found")

        commons_image_url = filepage.get_file_url()
        tpcom = cachedb.findfromcache(commons_image_url)
        if (tpcom == None):
            # get image from commons for comparison:
            # try to use same size
            commons_image = downloadimage(commons_image_url)
            if (commons_image == None):
                print("WARN: Failed to download commons-image: " + page.title() )
                continue
            print("DEBUG: commons image bands", commons_image.getbands())
            
            commonshash = getimagehash(commons_image)
            if (commonshash == None):
                print("WARN: Failed to hash commons-image: " + page.title() )
                continue
            
            # same lengths for p and d hash, keep change time from commons
            cachedb.addorupdate(commons_image_url, 
                                commonshash[0], commonshash[1], commonshash[0], commonshash[2], 
                                filepage.latest_file_info.timestamp)


        micache.addorupdate(filepage.pageid, datetime.now(timezone.utc))
        # skip the rest as that requires finna id and finna record
        continue

    if (len(finnaid) == 0 and len(finnarecordid) == 0):
        print("no finna id and no finna record found")

    # use newer record id if there was, ignore old style id
    if (len(finnarecordid) > 0):
        finnaid = finnarecordid

    # old kuvakokoelmat id -> try conversion
    if (len(finnaid) == 0 and len(kkid) > 0):
        finnaid = convertkuvakokoelmatid(kkid)
        finnaid = urllib.parse.quote(finnaid) # quote for url
        print("Converted old id in: " + page.title() + " from: " + kkid + " to: " + finnaid)

    if (len(finnaid) == 0):
        # urls coming from wikidata instead of in page?
        finna_ids = get_finna_ids(page)
        if (len(finna_ids) >= 1):
            print("NOTE: " + page.title() + " has external urls but not in expected place", str(finna_ids))
            # might have something usable..
            finnaid = finna_ids[0]
        else:
            print("Could not find a finna id in " + page.title() + ", skipping.")
        continue
 
    # kuvasiskot has "musketti" as part of identier, alternatively "museovirasto" may be used in some cases
    # various other images in finna have "hkm"
    # there are lots more like "fpm" (finnish photography museum) and so on -> don't warn
    #if (finnaid.find("musketti") < 0 and finnaid.find("museovirasto") < 0 and finnaid.find("hkm") < 0):
        #print("WARN: unexpected id in: " + page.title() + ", id: " + finnaid)
        #continue
    if (finnaid.find("profium.com") > 0):
        print("WARN: unusable url (redirector) in: " + page.title() + ", id: " + finnaid)
        continue
    
    # check for potentially unexpected characters after parsing (unusual description or something else)
    finnaid = checkcleanupfinnaid(finnaid, page)

    print("finna ID found: " + finnaid)
    
    # note: in some cases, there is quoted ID which will not work
    # since quoting again mangles characters -> try unquoting
    #if (finnaid.find("%25") >= 0):
        #finnaid = urllib.parse.unquote(finnaid)
        #print("using unquoted finna ID: " + finnaid)

    sourceurl = "https://www.finna.fi/Record/" + finnaid

    if (finnaid.find("musketti") >= 0 or finnaid.find("hkm.HKM") >= 0):
    
        # obsolete id -> try to fetch page and locate current ID
        finnaid = parsemetaidfromfinnapage(sourceurl)
        if (finnaid == ""):
            print("WARN: could not parse current finna id in " + page.title() + " , skipping, url: " + sourceurl)
            continue
        if (finnaid.find("\n") > 0):
            finnaid = leftfrom(finnaid, "\n")
            print("WARN: removed newline from new finna id for: " + page.title() + ", " + finnaid )
           
        if (finnaid.find("museovirasto.") == 0 or finnaid.find("hkm.") == 0):
            print("new finna ID found: " + finnaid)
            sourceurl = "https://www.finna.fi/Record/" + finnaid
        else:
            print("WARN: unexpected finna id in " + page.title() + ", id from finna: " + finnaid)
            #continue

    finna_record = get_finna_record(finnaid)
    if (isFinnaRecordOk(finna_record, finnaid) == False):
        continue
    
    # check what finna reports as identifier
    finna_accession_id = getFinnaAccessionIdentifier(finna_record)
    print("finna record ok: ", finnaid, " accession id: ", finna_accession_id)

    
    # TODO! Python throws error if image is larger than 178956970 pixels
    # so we can't handle really large images. Check for those and skip them..

    # try to find from cache first
    commons_image_url = filepage.get_file_url()
    tpcom = cachedb.findfromcache(commons_image_url)
    if (tpcom == None):
        # get image from commons for comparison:
        # try to use same size
        commons_image = downloadimage(commons_image_url)
        if (commons_image == None):
            print("WARN: Failed to download commons-image: " + page.title() )
            continue
        print("DEBUG: commons image bands", commons_image.getbands())
        
        commonshash = getimagehash(commons_image)
        if (commonshash == None):
            print("WARN: Failed to hash commons-image: " + page.title() )

            cachedb.addtocachewithpillowbug(commons_image_url, 
                                filepage.latest_file_info.timestamp,
                                'y')
            continue
        
        # same lengths for p and d hash, keep change time from commons
        cachedb.addorupdate(commons_image_url, 
                            commonshash[0], commonshash[1], commonshash[0], commonshash[2], 
                            filepage.latest_file_info.timestamp)

        print("Commons-image data added to cache for: " + page.title() )
        tpcom = cachedb.findfromcache(commons_image_url)
    else:
        # compare timestamp: if too old recheck the hash
        print("Commons-image cached data found for: " + page.title() + " timestamp: " + tpcom['timestamp'].isoformat())
        
        if (tpcom["pillowbug"] != None and tpcom["pillowbug"] == 'y'):
            print("Pillow is bugging on image: " + page.title() + ", skipping")
            continue

        
        # NOTE! force timezone since python is garbage in handling UTC-times:
        # python loses timezone even when the original string from database includes it
        # so we need to force both into same even if they already are in the same timezone, 
        # only difference is that other is marked zulu-time and other is marked +0.
        if (tpcom['timestamp'].replace(tzinfo=timezone.utc) < filepage.latest_file_info.timestamp.replace(tzinfo=timezone.utc)):
            print("Updating cached data for Commons-image: " + page.title() )
            commons_image = downloadimage(commons_image_url)
            if (commons_image == None):
                print("WARN: Failed to download commons-image: " + page.title() )
                continue
            print("DEBUG: commons image bands", commons_image.getbands())
            
            commonshash = getimagehash(commons_image)
            if (commonshash == None):
                print("WARN: Failed to hash commons-image: " + page.title() )
                # might be transient bug?
                cachedb.setpillowbug(commons_image_url, 
                                    'f', 
                                    filepage.latest_file_info.timestamp)
                continue
            cachedb.addorupdate(commons_image_url, 
                                commonshash[0], commonshash[1], commonshash[0], commonshash[2], 
                                filepage.latest_file_info.timestamp)
            tpcom = cachedb.findfromcache(commons_image_url)

    # just sanity check: if cache is cutting url we might get wrong entry as result
    if (tpcom['url'] != commons_image_url):
        print("ERROR: commons url mismatch for: " + page.title() )
        exit(1)

    if ('8000000000000000' == tpcom['phashval']):
        print("WARN: phash is bogus for: ", page.title())
        cachedb.setpillowbug(commons_image_url, 
                            'y', 
                            filepage.latest_file_info.timestamp)
        continue
    if ('0000000000000000' == tpcom['dhashval']):
        print("WARN: dhash is bogus for: ", page.title())
        cachedb.setpillowbug(commons_image_url, 
                            'y', 
                            filepage.latest_file_info.timestamp)
        continue
    if ('0000000000000040' == tpcom['dhashval']):
        print("WARN: dhash is bogus for: ", page.title())
        cachedb.setpillowbug(commons_image_url, 
                            'y', 
                            filepage.latest_file_info.timestamp)
        continue
    if ('0000000000000080' == tpcom['dhashval']):
        print("WARN: dhash is bogus for: ", page.title())
        cachedb.setpillowbug(commons_image_url, 
                            'y', 
                            filepage.latest_file_info.timestamp)
        continue
    

    # if we have passed, mark as none
    cachedb.setpillowbug(commons_image_url, 
                        'n', 
                        filepage.latest_file_info.timestamp)

    if (isPerceptualHashInSdcData(claims, tpcom['phashval']) == False):
        print("adding phash to statements for: ", finnaid)
        hashclaim = addPerceptualHashToSdcData(pywikibot, wikidata_site, tpcom['phashval'], tpcom['timestamp'])
        commonssite.addClaim(wditem, hashclaim)
    else:
        print("testing phash qualifiers for: ", finnaid)
        checkPerceptualHashInSdcData(pywikibot, wikidata_site, claims, tpcom['phashval'], tpcom['timestamp'])

    if (isDifferenceHashInSdcData(claims, tpcom['dhashval']) == False):
        print("adding dhash to statements for: ", finnaid)
        hashclaim = addDifferenceHashToSdcData(pywikibot, wikidata_site, tpcom['dhashval'], tpcom['timestamp'])
        commonssite.addClaim(wditem, hashclaim)
    else:
        print("testing dhash qualifiers for: ", finnaid)
        checkDifferenceHashInSdcData(pywikibot, wikidata_site, claims, tpcom['dhashval'], tpcom['timestamp'])

    # use helper to check that it is correctly formed
    imagesExtended = getImagesExtended(finna_record)
    if (imagesExtended == None):
        print("WARN: 'imagesExtended' not found in finna record, skipping: " + finnaid)
        continue

    imageList = getFinnaImagelist(finna_record)
    if (imageList == None):
        print("WARN: 'images' not found in finna record, skipping: " + finnaid)
        continue

    finna_image_url = ""
    match_found = False
    need_index = False
    if (len(imageList) == 1):
    
        finna_image_url = "https://finna.fi" + imagesExtended['urls']['large']

        tpfinna = cachedb.findfromcache(finna_image_url)
        if (tpfinna == None):
            # get image from finnafor comparison:
            # try to use same size
            finna_image = downloadimage(finna_image_url)
            if (finna_image == None):
                print("WARN: Failed to download finna-image: " + page.title() )
                continue
            print("DEBUG: finna image bands", finna_image.getbands(), finna_image_url)
            
            finnahash = getimagehash(finna_image)
            if (finnahash == None):
                print("WARN: Failed to hash finna-image: " + page.title() )
                cachedb.addtocachewithpillowbug(finna_image_url, 
                                    datetime.now(timezone.utc),
                                    'y')
                continue
            
            # same lengths for p and d hash
            cachedb.addorupdate(finna_image_url, finnahash[0], finnahash[1], finnahash[0], finnahash[2], datetime.now(timezone.utc))
            tpfinna = cachedb.findfromcache(finna_image_url)
        #else:
            # compare timestamp: if too old recheck the hash

        if (tpfinna['url'] != finna_image_url):
            print("ERROR: finna url mismatch for: " + page.title() )
            exit(1)
        
        # Test if image is same using similarity hashing
        if (is_same_image(tpfinna, tpcom) == True):
            match_found = True

    if (len(imageList) > 1):
        # multiple images in finna related to same item -> 
        # need to pick the one that is closest match
        print("Multiple images for same item: " + str(len(imageList)))

        f_imgindex = 0
        for img in imageList:
            finna_image_url = "https://finna.fi" + img

            tpfinna = cachedb.findfromcache(finna_image_url)
            if (tpfinna == None):
                # get image from finnafor comparison:
                # try to use same size
                finna_image = downloadimage(finna_image_url)
                if (finna_image == None):
                    print("WARN: Failed to download finna-image: " + page.title() )
                    continue
                print("DEBUG: finna image bands", finna_image.getbands(), finna_image_url)
                    
                finnahash = getimagehash(finna_image)
                if (finnahash == None):
                    print("WARN: Failed to hash finna-image: " + page.title() )
                    cachedb.addtocachewithpillowbug(finna_image_url, 
                                        datetime.now(timezone.utc),
                                        'y')
                    continue
                # same lengths for p and d hash
                cachedb.addorupdate(finna_image_url, finnahash[0], finnahash[1], finnahash[0], finnahash[2], datetime.now(timezone.utc))
                tpfinna = cachedb.findfromcache(finna_image_url)
            #else:
                # compare timestamp: if too old recheck the hash

            if (tpfinna['url'] != finna_image_url):
                print("ERROR: finna url mismatch for: " + page.title() )
                exit(1)

            # Test if image is same using similarity hashing
            if (is_same_image(tpfinna, tpcom) == True):
                match_found = True
                need_index = True
                print("Matching image index: " + str(f_imgindex))
                break
            else:
                f_imgindex = f_imgindex + 1

    if (match_found == False):
        print("No matching image found, skipping: " + finnaid)
        continue

    if (needReupload(file_info, finna_record, imagesExtended) == True):
        print("Note: image should be uploaded with higher resolution for: " + finnaid)
        #if (reuploadImage(finnaid, file_info, imagesExtended, need_index, filepage, finna_image_url) == True):
            #print("image reuploaded with higher resolution for: ", page.title())
            # after uploading, recalculate and update hashed
        #else:
            #print("WARN: Could not reupload with higher resolution for: ", page.title())

    # TODO: can we simplify lookup?
    # does this work? if 'fi' in filepage.labels,  filepage.labels['fi'] = finna_title

    if (isSdcCaption(commonssite, file_media_identifier, 'fi') == False):
        finna_title = getTitleFromFinna(finna_record, 'fi')
        if (len(finna_title) > 0 and len(finna_title) < 250):
            addSdcCaption(commonssite, file_media_identifier, finna_title, 'fi')
            print("Caption added to page: ", page.title())

    # note: if there are no collections, don't remove from commons as they may have manual additions
    collectionqcodes = getCollectionsFromRecord(finna_record, finnaid, d_labeltoqcode)
    if (len(collectionqcodes) == 0):
        print("No collections for: " + finnaid)
    else:
        print("Collections qcodes found:", str(collectionqcodes))

    publisherqcode = getqcodeforfinnapublisher(finna_record, d_institutionqcode)
    if (len(publisherqcode) == 0):
        print("WARN: failed to find a publisher in finna for: " + finnaid)
    else:
        print("found publisher " + publisherqcode + " in finna for: " + finnaid)
        if (ispublisherinstatements(claims, publisherqcode) == False):
            print("publisher " + publisherqcode + " not found in commons for: " + finnaid)
        else:
            print("publisher " + publisherqcode + " found in commons for: " + finnaid)

    # TODO: get operator by url domain instead?
    # if domain is kansallisgalleria -> no finna API available
    operatorqcode = getqcodeforfinnaoperator(finna_record)
    if (len(operatorqcode) == 0):
        print("WARN: failed to find a operator qcode for: " + finnaid)

    claimsForSource = False
    operatorFound = False
    publisherFound = False
    descFound = False
    if "P7482" in claims:
        print("DEBUG: claims found for: " + finnaid)
        claimsForSource = True
        
        descFound = issourceurlinstatements(claims, sourceurl)
        if (len(operatorqcode) > 0):
            operatorFound = isoperatorinstatements(claims, operatorqcode)
            
        if (descFound == True and operatorFound == True):
            print("DEBUG: no need to add source")
        else:
            # has source claims but not same operator or url?
            # file imported from flickr?
            print("DEBUG: operator/descriptive url missing for:", operatorqcode)
            
        if (len(publisherqcode) > 0):
            publisherFound = ispublisherinstatements(claims, publisherqcode)
            if (publisherFound == False):
                print("DEBUG: publisher missing for:", publisherqcode)
                # other data may have been added before publisher was added to wikidata
                # -> try to add publisher
            else:
                print("DEBUG: publisher found", publisherqcode)

    # NOTE! currently there is no way to add part of the missing information to a claim?
    # it is all or nothing -> we get duplicates if we try to add just part
    # or we get failure if we try to omit existing information
    #
    if claimsForSource == False or (operatorFound == False and descFound == False):
        source_claim = addsourceoperatorpublisher(pywikibot, wikidata_site, operatorqcode, publisherqcode, sourceurl)
        if (source_claim != None):
            commonssite.addClaim(wditem, source_claim)
            print("added source")

    if claimsForSource == True:
        print("DEBUG: should add to existing")
        checksourceoperatorpublisher(pywikibot, wikidata_site, claims, operatorqcode, publisherqcode, sourceurl)

    # Test copyright (old field: rights, but request has imageRights?)
    # imageRights = finna_record['records'][0]['imageRights']
    
    # should be CC BY 4.0 or Public domain/CC0
    copyrightlicense = getFinnaLicense(imagesExtended)
    if (isSupportedFinnaLicense(copyrightlicense) == False):
        print("NOTE: License is not fully supported: " + copyrightlicense)
    else:
        # is license in statements
        #P275, "CC BY 4.0", may be "PDM" or "CC0"
        #P854, sourceurl
        if (islicenseinstatements(claims, copyrightlicense) == False):
            print("license missing or not same in statements", copyrightlicense)
            lic_claim = addlicensetostatements(pywikibot, wikidata_site, copyrightlicense, sourceurl)
            if (lic_claim != None):
                commonssite.addClaim(wditem, lic_claim)
                print("license added to statements", copyrightlicense)
        else:
            print("testing license sources for: ", finnaid)
            checklicensesources(pywikibot, wikidata_site, claims, copyrightlicense, sourceurl)

        statusqcode = determineCopyrightStatus(finna_record)
        if (statusqcode != ""):
            if (isCopyrightStatusInSDC(claims, statusqcode, sourceurl) == False):
                print("status", statusqcode ," is missing or not same in statements for license", copyrightlicense)
                #cs_claim = addCopyrightstatusToSdc(pywikibot, wikidata_site, copyrightlicense, statusqcode, sourceurl)
                #if (cs_claim != None):
                    #commonssite.addClaim(wditem, cs_claim)
                    #print("status code", statusqcode ," added to statements for license", copyrightlicense)

    # subjects / "kuvausaika 08.01.2016" -> inception
    inceptiondt = parseinceptionfromfinna(finna_record)
    if (inceptiondt != None):
        #print("DEBUG: found inception date for: " + finnaid + " " + inceptiondt.isoformat())
        if (isinceptioninstatements(claims, inceptiondt, sourceurl) == False):
            print("DEBUG: adding inception date for: " + finnaid)
            inc_claim = addinceptiontosdc(pywikibot, wikidata_site, inceptiondt, sourceurl)
            commonssite.addClaim(wditem, inc_claim)
        else:
            print("DEBUG: sdc already has inception date for: " + finnaid)
    else:
        print("DEBUG: could not parse inception date for: " + finnaid)

    # check SDC and try match with finna list collectionqcodes
    # note: give copy to getcollectiontargetqcode() so we can reuse the list
    collectionstoadd = getcollectiontargetqcode(claims, collectionqcodes.copy())
    if (len(collectionstoadd) > 0):
        print("adding statements for collections: " + str(collectionstoadd))

        # Q118976025 "Studio Kuvasiskojen kokoelma"
        for collection in collectionstoadd:
            coll_claim = addcollectiontostatements(pywikibot, wikidata_site, collection)

            # batching does not work correctly with pywikibot:
            # need to commit each one
            commonssite.addClaim(wditem, coll_claim)
    else:
        print("no collections to add")

    # if the stored ID is not same (new ID) -> add new
    if (isFinnaIdInStatements(claims, finnaid) == False):
        print("adding finna id to statements: ", finnaid)
        finna_claim = addfinnaidtostatements(pywikibot, wikidata_site, finnaid)
        commonssite.addClaim(wditem, finna_claim)
    else:
        print("id found, not adding again", finnaid)

    photographers = getFinnaNonPresenterAuthors(finna_record)
    if (len(photographers) > 0):
        print("DEBUG: photographers in finna: ", str(photographers))
        
        # TODO: get qcode by name in list
        #for photographer in photographers:
        
            #creatorclaim = addCreatortoStatements(pywikibot, wikidata_site, creatorqcode)
            #if (creatorclaim != None):
                #wditem.addClaim(creatorclaim)


    placeslist = getFinnaPlaces(finna_record)
    actorslist = getFinnaActors(finna_record)

    tmptext = oldtext
    oldcategories = listExistingCommonsCategories(oldtext)
    
    #  try to check if item type in Finna is "photograph" (not "artwork")
    if (isFinnaFormatImage(finna_record) == True):

        for template in ct.templatelist:
            # if there is "information" template change it to "photograph"
            # since we want additional fields there
            if (ct.isSupportedCommonsTemplate(template) == True):
                if (ct.fixTemplateType(template) == True):
                    print("Fixed template type for: " + page.title())
                if (ct.addOrSetAccNumber(template, finna_accession_id) == True):
                    print("Fixed accession number for: " + page.title())
                
                institutiontemplate = None
                if publisherqcode in d_institutionqtotemplate: # skip unknown tags
                    # try local lookup
                    institutiontemplate = d_institutionqtotemplate[publisherqcode]
                    print("DEBUG: matching institution template: ", institutiontemplate)
                else:
                    # try wikidata lookup
                    institutiontemplate = getInstitutionTemplateFromWikidata(pywikibot, wikidata_site, publisherqcode)
                    print("DEBUG: found institution template from Wikidata: ", institutiontemplate)

                # if we found a match -> add wrapping for template
                if (institutiontemplate != None and len(institutiontemplate) > 0):
                    institutiontemplate = "{{Institution:" + institutiontemplate + "}}"
                    if (ct.addOrSetInstitution(template, institutiontemplate) == True):
                        print("Fixed institution for: " + page.title())


                if (ct.addOrSetPhotographers(template, photographers) == True):
                    print("Added photographers for: " + page.title())

                if (ct.addOrSetDepictedPeople(template, actorslist) == True):
                    print("Added depicted people for: " + page.title())

                if (ct.addOrSetDepictedPlaces(template, placeslist) == True):
                    print("Added depicted places for: " + page.title())
                    

        if (ct.isChanged() == True):
            tmptext = str(ct.wikicode)

    categoriesadded = False
    # add commons-categoeris for collections
    collcatstoadd = getcategoriesforcollections(pywikibot, collectionqcodes, d_collectionqtocategory)
    if (len(collcatstoadd) > 0):
        print("Adding collection categories for: ", finnaid, "categories ", str(collcatstoadd))
        res, tmptext = addCategoriesToCommons(pywikibot, tmptext, collcatstoadd) 
        if (res == True):
            print("Collection categories added for: " + finnaid)
            categoriesadded = True
        else:
            print("No collection categories added for: " + finnaid)

    # add commons-categoeris for other tags (subjects)
    extracatstoadd = list() # disabled for now

    # categories like "music festivals in finland" and other combinations
    #extracatstoadd += getcategoriesforsubjects(pywikibot, finna_record, oldcategories, inceptiondt)

    # categories like "1931 in helsinki"
    #extracatstoadd += getcategoriesforplaceandtime(pywikibot, finna_record, inceptiondt, placeslist, oldcategories)

    # when you need a category but there is no collection in data (museum of finnish architecture)
    extracatstoadd += getcategoriesforinstitutions(pywikibot, d_institutionqtocategory, publisherqcode, operatorqcode)

    if (len(extracatstoadd) > 0):
        print("Adding subject categories for: ", finnaid, "categories ", str(extracatstoadd))
        res, tmptext = addCategoriesToCommons(pywikibot, tmptext, extracatstoadd)
        if (res == True):
            print("Subject categories added for: " + finnaid)
            categoriesadded = True
        else:
            print("No subject categories added for: " + finnaid)

    summary = ''
    if (ct.isChanged() == True):
        print("Changed wikitext for: " + page.title())
        summary = 'Fixing template fields'
    if (categoriesadded == True):
        summary += 'Adding categories'

    if (oldtext != tmptext and len(summary) > 0):
        print("Saving with summary: ", summary)
        pywikibot.info('Edit summary: {}'.format(summary))
        page.text = tmptext
        page.save(summary)


    # cache that we have recently processed this page successfully:
    # this isn't perfect but should speed up things a bit due to data transfer latency
    micache.addorupdate(filepage.pageid, datetime.now(timezone.utc))

    #pywikibot.info('----')
    #pywikibot.showDiff(oldtext, newtext,2)
    #summary='Adding structured data to file'
    #pywikibot.info('Edit summary: {}'.format(summary))

    #question='Do you want to accept these changes?'
    #choice = pywikibot.input_choice(
    #            question,
    #            [('Yes', 'y'),('No', 'N'),('Quit', 'q')],
    #            default='N',
    #            automatic_quit=False
    #        )

    #pywikibot.info(choice)
    #if choice == 'q':
    #    print("Asked to exit. Exiting.")
    #    exit()

    #if choice == 'y':
        # script setfinnasource is used for this
        #if (addFinnaIdForKuvakokoelmatSource == True):
            #page.text=newtext
            #page.save(summary)
        
        # batching does not work correctly with pywikibot
        #if (flag_add_source == True):
            #commonssite.addClaim(wditem, source_claim)
        #if (flag_add_collection == True):
            #commonssite.addClaim(wditem, coll_claim)
        #if (flag_add_finna == True):
            #commonssite.addClaim(wditem, finna_claim)

    # don't try too many at once
    #if (rowcount >= rowlimit):
    #    print("Limit reached")
    #    exit(1)
    #    break

