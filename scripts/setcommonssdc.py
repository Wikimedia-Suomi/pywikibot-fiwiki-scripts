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
import sqlite3

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

def get_finna_record(finnaid, quoteid=True):
    if (finnaid.startswith("fmp.") == True and finnaid.find("%2F") > 0):
        quoteid = False
    #if (finnaid.startswith("sls.") == True and finnaid.find("%") > 0):
        #quoteid = False

    if (finnaid.find("/") > 0):
        quoteid = True
    
    if (quoteid == True):
        quotedfinnaid = urllib.parse.quote_plus(finnaid)
    else:
        quotedfinnaid = finnaid
    #print("DEBUG: fetching record with id ", quotedfinnaid, " for id ", finnaid)

    url="https://api.finna.fi/v1/record?id=" +  quotedfinnaid
    url+= finna_api_parameter('field[]', 'id')
    url+= finna_api_parameter('field[]', 'title')
    url+= finna_api_parameter('field[]', 'subTitle')
    url+= finna_api_parameter('field[]', 'shortTitle')
    url+= finna_api_parameter('field[]', 'summary')
    url+= finna_api_parameter('field[]', 'imageRights')
    url+= finna_api_parameter('field[]', 'images')
    url+= finna_api_parameter('field[]', 'imagesExtended')
    #url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'openUrl')
    url+= finna_api_parameter('field[]', 'nonPresenterAuthors')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'subjects')
    #url+= finna_api_parameter('field[]', 'subjectsExtendet')
    url+= finna_api_parameter('field[]', 'subjectPlaces')
    url+= finna_api_parameter('field[]', 'subjectActors')
    url+= finna_api_parameter('field[]', 'subjectDetails')
    # url+= finna_api_parameter('field[]', 'geoLocations')
    url+= finna_api_parameter('field[]', 'buildings')
    url+= finna_api_parameter('field[]', 'identifierString')
    url+= finna_api_parameter('field[]', 'collections')
    url+= finna_api_parameter('field[]', 'institutions')
    url+= finna_api_parameter('field[]', 'classifications')
    url+= finna_api_parameter('field[]', 'events')
    url+= finna_api_parameter('field[]', 'languages')
    url+= finna_api_parameter('field[]', 'originalLanguages')
    url+= finna_api_parameter('field[]', 'year')
    #url+= finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url+= finna_api_parameter('field[]', 'formats')
    #url+= finna_api_parameter('field[]', 'physicalDescriptions')
    url+= finna_api_parameter('field[]', 'measurements')

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
    phash = imagehash.phash(img, hash_size=hashlen)
    dhash = imagehash.dhash(img, hash_size=hashlen)
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

# ----- CachedImageData
class CachedImageData:
    def opencachedb(self):
        # created if it doesn't yet exist
        self.conn = sqlite3.connect("pwbimagedatacache.db")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS imagecache(url, phashlen, phashval, dhashlen, dhashval, timestamp)")

    def addtocache(self, url, plen, pval, dlen, dval, ts):

        sqlq = "INSERT INTO imagecache(url, phashlen, phashval, dhashlen, dhashval, timestamp) VALUES ('"+ url + "', "+ str(plen) + ", '"+ pval + "', "+ str(dlen) + ", '"+ dval + "', '" + ts.isoformat() + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def updatecache(self, url, plen, pval, dlen, dval, ts):

        sqlq = "UPDATE imagecache SET phashlen = "+ str(plen) + ", phashval = '"+ pval + "', dhashlen = "+ str(dlen) + ", dhashval = '"+ dval + "', timestamp = '" + ts.isoformat() + "' WHERE url = '" + url + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findfromcache(self, url):
        sqlq = "SELECT url, phashlen, phashval, dhashlen, dhashval, timestamp FROM imagecache WHERE url = '" + url + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = res.fetchall()
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['url'] = row[0]
            dt['phashlen'] = int(row[1])
            dt['phashval'] = row[2]
            dt['dhashlen'] = int(row[3])
            dt['dhashval'] = row[4]
            dt['timestamp'] = datetime.fromisoformat(row[5])
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

def addSdcCaption(commons_site, media_identifier, lang, caption):
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

# ----- /CommonsMediaInfo


# ----- FinnaTimestamp
class FinnaTimestamp:
    def setYear(self, year):
        self.year = year
        self.month = 0
        self.day = 0
        
    def setYearMonth(self, year, month):
        self.year = year
        self.month = month
        self.day = 0

    def setDate(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
# ----- /FinnaTimestamp


# strip id from other things that may be after it:
# there might be part of url or some html in same field..
def stripid(oldsource):
    # space after url?
    indexend = oldsource.find(" ")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some other text after url?
    # TODO: sometimes comma is part of ID, sometimes not..
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
    indexend = len(source)-1

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
        #print("DEBUG: source has url: " + url)
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

    indexlast = kkid.rfind(".", 0, len(source)-1)
    if (indexlast > 0):
        # .jpg or something at end? remove id
        kkid = kkid[:indexlast]
    return kkid

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
def getcollectiontargetqcode(statements, collections):
    if "P195" not in statements:
        return collections
    
    claimlist = statements["P195"]
    for claim in claimlist:
        # target is expected to be like: [[wikidata:Q118976025]]
        target = claim.getTarget()

        # parse Q-code from link
        targetqcode = getqcodefromwikidatalink(target)

        # no need to add if SDC-data already has a target
        # -> remove from collections to add
        if (targetqcode in collections):
            collections.remove(targetqcode)

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
    return collections

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

# check if 'P275' is missing 'P854' with reference url
def checklicensesources(statements, license, sourceurl):
    if "P275" not in statements:
        print("license property not in statements")
        return False

    # note: there may be more than on license per item (not equal)
    # so check source is under appropriate license..
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != getQcodeForLicense(license)): # not our license
            #print("DEBUG: unsupported license: " + targetqcode)
            continue
    
        sourcelist = claim.getSources()
        for source in sourcelist:
            for key, value in source.items():
                if key == "P854":
                    for v in value: # v is another claim..
                        vtarget = v.getTarget()
                        if (vtarget == sourceurl):
                            matchfound = True
                            print("license source found")
                            return True
        print("license source not found, url: " + sourceurl)
    return False

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
    
    return lic_claim

# CC0: Q6938433
# CC BY 4.0: Q20007257
def addreferencetolicense(pywikibot, wikidata_site, license, sourceurl):
    if (isSupportedFinnaLicense(license) == False):
        return False

    # if there are multiple licenses, check that we add source to right one
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != getQcodeForLicense(license)): # not our license
            #print("DEBUG: unsupported license: " + targetqcode)
            continue

        # note: this add qualifer but we want "reference" type
        #qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
        #qualifier_url.setTarget(sourceurl)
        #claim.addSource(qualifier_url, summary='Adding reference URL qualifier')
        # is there "addreference()"?
    
    return True

def isfinnaidinstatements(statements, newid):
    if "P9478" not in statements:
        return False

    # also see if unquoted one matches
    unquotedNewId = urllib.parse.unquote_plus(newid)

    claimlist = statements["P9478"]    
    for claim in claimlist:
        # target is expected to be like: "musketti." or "museovirasto."
        # but may be something else (hkm. sibelius. fmp. and so on)
        target = claim.getTarget()
        if (target == newid):
            # match found: no need to add same ID again
            return True
        unquotedTarget = urllib.parse.unquote_plus(target)
        if (unquotedTarget == unquotedNewId 
            or unquotedTarget == newid 
            or target == unquotedNewId):
            # commons seems to have bug in some character quoting
            # -> try to catch it
            print("NOTE: unquoted target matches unquoted Finna-ID", unquotedTarget)
            return True

    # ID not found -> should be added
    return False

def addfinnaidtostatements(pywikibot, wikidata_site, finnaid):
    claim_finnaidp = 'P9478'  # property ID for "finna ID"
    finna_claim = pywikibot.Claim(wikidata_site, claim_finnaidp)
    # url might have old style id as quoted -> no need with new id
    finnaunquoted = urllib.parse.unquote(finnaid)
    finna_claim.setTarget(finnaunquoted)
    return finna_claim

def addcollectiontostatements(pywikibot, wikidata_site, collection):
    claim_collp = 'P195'  # property ID for "collection"
    coll_claim = pywikibot.Claim(wikidata_site, claim_collp)
    qualifier_targetcoll = pywikibot.ItemPage(wikidata_site, collection)
    coll_claim.setTarget(qualifier_targetcoll)
    return coll_claim

# add mime-type to sdc data
def addmimetypetosdc(pywikibot, wikidata_site, mimetype):
    claim_mimep = 'P1163'  # property ID for "mime type"
    mime_claim = pywikibot.Claim(wikidata_site, claim_mimep)
    #qualifier_targetmime = pywikibot.ItemPage(wikidata_site, mimetype)
    mime_claim.setTarget(mimetype)
    return mime_claim

# add inception date to sdc data
def addinceptiontosdc(pywikibot, wikidata_site, incdate):
    #wbdate = pywikibot.WbTime.fromTimestr(incdate.isoformat())

    if (incdate.year == 0):
        print("DEBUG: not a valid year for inception")
        return None

    # note: need "WbTime" which is not a standard datetime
    if (incdate.year != 0 and incdate.month != 0 and incdate.day != 0):
        #print("DEBUG: setting year, month, day")
        wbdate = pywikibot.WbTime(incdate.year, incdate.month, incdate.day)
    elif (incdate.year != 0 and incdate.month != 0):
        #print("DEBUG: setting year, month")
        wbdate = pywikibot.WbTime(incdate.year, incdate.month)
    else:
        #print("DEBUG: setting year only")
        wbdate = pywikibot.WbTime(incdate.year)

    claim_incp = 'P571'  # property ID for "inception"
    inc_claim = pywikibot.Claim(wikidata_site, claim_incp)
    #qualifier_targetmime = pywikibot.ItemPage(wikidata_site, mimetype)
    
    # note: must format into "WbTime"
    inc_claim.setTarget(wbdate)
    return inc_claim

def isinceptioninstatements(statements, incdt):
    if "P571" in statements:
        return True
    return False

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

# note alternate: might have timestamp like "1943-06-24" or "01.06.1930"
def timestringtodatetime(timestring):
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

    # plain year in string?
    if (timestring.isnumeric() == True):
        if (len(timestring) == 6):
            # there is year and month like "189605"
            year = int(timestring[:4])
            month = int(timestring[4:6])
            fdt = FinnaTimestamp()
            fdt.setYearMonth(year, month)
            return fdt
        if (len(timestring) == 4):
            num = int(timestring)
            fdt = FinnaTimestamp()
            fdt.setYear(num)
            return fdt
    
    return None

# parse timestamp of picture from finna data
# TODO: sometimes there is a range of approximate dates given
# -> we could parse them but how do we mark them in SDC?
def parseinceptionfromfinna(finnarecord):
    if "records" not in finnarecord:
        print("ERROR: no records in finna record")
        return None

    records = finnarecord['records'][0]
    if "subjects" not in records:
        print("no subjects in finna record")
        return None
    try:
        subjects = finna_record['records'][0]['subjects']
        for subject in subjects:
            for sbstr in subject:
                index = sbstr.find("kuvausaika ")
                if (index >= 0):
                    index = index+len("kuvausaika ")
                    timestamp = sbstr[index:]
                    # TODO: sometimes there is newlines and tabs in the string -> strip them out
                    timestamp = trimlr(timestamp)
                    print("DEBUG: kuvausaika in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)

                index = sbstr.find("ajankohta: ")
                if (index >= 0):
                    index = index+len("ajankohta: ")
                    timestamp = sbstr[index:]
                    # TODO: sometimes there is newlines and tabs in the string -> strip them out
                    timestamp = trimlr(timestamp)
                    print("DEBUG: ajankohta in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)
                
                # "valmistus" may have time, place, materials..
                index = sbstr.find("valmistusaika ")
                if (index >= 0):
                    index = index+len("valmistusaika ")
                    timestamp = sbstr[index:]
                    # TODO: sometimes there is newlines and tabs in the string -> strip them out
                    timestamp = trimlr(timestamp)
                    print("DEBUG: valmistusaika in subjects: " + timestamp)
                    return timestringtodatetime(timestamp)
                
                # note: in some cases there is just timestamp without a string before it
                #dt = timestringtodatetime(timestamp)
                #if (dt != None):
                    #return dt
                    
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
        year = finna_record['records'][0]['year']
        year = trimlr(year)
        if (year.isnumeric() == False):
            print("DEBUG: not a numeric year: " + year)
            
        fdt = FinnaTimestamp()
        fdt.setYear(int(year))
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
        # Kansallisgalleria 
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

def getFinnaLicense(imagesExtended):
    # should be CC BY 4.0 or Public domain/CC0
    return imagesExtended['rights']['copyright']

def isSupportedCommonsTemplate(template):
    #print("DEBUG commons template: ", template.name)
    name = template.name.lower()
    name = leftfrom(name, "\n") # mwparserfromhell is bugged
    name = trimlr(name)
    if (name == "information" 
        or name == "photograph" 
        or name == "artwork" 
        or name == "art photo"):
        return True
    #print("DEBUG: not supported template: ", name)
    return False

def getSourceFromCommonsTemplate(template):
    if template.has("Source"):
        return template.get("Source")
    if template.has("source"):
        return template.get("source")
    return None

def getAccessionFromCommonsTemplate(template):
    if template.has("Accession number"):
        return template.get("Accession number")
    if template.has("accession number"):
        return template.get("accession number")
    if template.has("Id"):
        return template.get("Id")
    if template.has("id"):
        return template.get("id")
    return None

# find source urls from template(s) in commons-page
def getsourceurlfrompagetemplate(page_text):
    wikicode = mwparserfromhell.parse(page_text)
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        # at least three different templates have been used..
        if (isSupportedCommonsTemplate(template) == True):
            #paracc = getAccessionFromCommonsTemplate(template)
            #if (paracc != None):
                #accurls = geturlsfromsource(str(paracc.value))
                # if accession has finna-url but source doesn't -> try it instead
            
            par = getSourceFromCommonsTemplate(template)
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

def isSupportedMimetype(strmime):
    if (strmime.find("audio") >= 0 
        or strmime.find("ogg") >= 0 
        or strmime.find("/svg") >= 0 
        or strmime.find("/pdf") >= 0 
        or strmime.find("image/vnd.djvu") >= 0
        or strmime.find("video") >= 0):
        print("unsupported mime-type: ", strmime)
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

    ## TESTING
    #if (pagename.find("Hanna Cederholm") >= 0):
        #return False
    #return True

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
    except:
        print("WARN: failed to retrieve filepage: " + page.title())

    return None


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
d_institutionqcode["Helsingin kaupunginmuseo"] = "Q2031357"
d_institutionqcode["Vantaan kaupunginmuseo"] = "Q26723704"
d_institutionqcode["Keravan museopalvelut"] = "Q121266100"
d_institutionqcode["Turun museokeskus"] = "Q18346797"
d_institutionqcode["Työväenmuseo Werstas"] = "Q11899172"
d_institutionqcode["Työväen Arkisto"] = "Q11899166"
d_institutionqcode["Satakunnan Museo"] = "Q6304688"
d_institutionqcode["Suomen Metsästysmuseo"] = "Q1678320"
d_institutionqcode["Svenska litteratursällskapet i Finland"] = "Q769544"
d_institutionqcode["Lappeenrannan museot"] = "Q58636578"
d_institutionqcode["Hyvinkään kaupunginmuseo"] = "Q41776741"
d_institutionqcode["Helsingin yliopistomuseo"] = "Q3329065"
d_institutionqcode["Suomen Rautatiemuseo"] = "Q1138355"
d_institutionqcode["Salon historiallinen museo"] = "Q56403058"
d_institutionqcode["Etelä-Karjalan museo"] = "Q18346681"
d_institutionqcode["Kymenlaakson museo"] = "Q18346674"
d_institutionqcode["Pielisen museo"] = "Q11887930"


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
d_labeltoqcode["Valokuvaamo Jäniksen kokoelma"] = "Q123396641"

d_labeltoqcode["Yleisetnografinen kuvakokoelma"] = "Q122414127"
d_labeltoqcode["Suomalais-ugrilainen kuvakokoelma"] = "Q123358672"
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
d_labeltoqcode["Satakunnan Kansan kuva-arkisto"] = "Q123508726"
d_labeltoqcode["Suomen Lähetysseura ry:n kuvakokoelma"] = "Q123508491"
d_labeltoqcode["Hyvinkään kaupunginmuseon kokoelma"] = "Q123508767"
d_labeltoqcode["Sote-kokoelma"] = "Q123508776"
d_labeltoqcode["VR:n kuvakokoelma"] = "Q123508783"
d_labeltoqcode["Suomen Rautatiemuseon kuvakokoelma"] = "Q123508786"
d_labeltoqcode["Arkeologian kuvakokoelma"] = "Q123508795"
d_labeltoqcode["Hugo Simbergin valokuvat"] = "Q123523516"

d_labeltoqcode["Wiipuri-kokoelma"] = "Q123523357"
d_labeltoqcode["Wiipuri-museon kokoelma"] = "Q123523357"

# Accessing wikidata properties and items
wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)
#pages = getcatpages(pywikibot, commonssite, "Archaeologists from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Kantele players", True)
#pages = getcatpages(pywikibot, commonssite, "Files from the Antellin kokoelma")

#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", 3)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical images of Finland", 3)

#pages = getcatpages(pywikibot, commonssite, "People of Finland in the 1980s", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Archaeology in Finland")
#pages = getcatpages(pywikibot, commonssite, "Category:Painters from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Winter War", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Continuation War", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by photographer from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:People of Finland by year", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:People of Finland by year", 3)

#pages = getcatpages(pywikibot, commonssite, "Category:History of Finland", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:History of Karelia", 2)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Aviation Museum")

#pages = getcatpages(pywikibot, commonssite, "Category:Lotta Svärd", True)
#pages = getcatpages(pywikibot, commonssite, "Category:SA-kuva", True)
#pages = getcatpages(pywikibot, commonssite, "Files uploaded by FinnaUploadBot", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Fortresses in Finland", 4)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finland in World War II", 3)
#pages = getcatpages(pywikibot, commonssite, "Category:Vyborg in the 1930s")
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Vyborg", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Miss Finland winners", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Monuments and memorials in Helsinki", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Events in Finland by year", 3)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Culture of Finland", 4)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Musicians from Finland", 3)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Artists from Finland", 3)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Opera of Finland", 3)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:People of Finland by occupation", 2)

#Category:Cities in Finland by decade

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Economy of Finland", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Companies of Finland", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Politics of Finland", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Shipyards in Finland", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Designers from Finland", 2)

#pages = getcatpages(pywikibot, commonssite, "Category:Writers from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Architects from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Artists from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Musicians from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Composers from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Conductors from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Journalists from Finland", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Vivica Bandler")

#pages = getcatpages(pywikibot, commonssite, "Category:Swedish Theatre Helsinki Archive", True)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Society of Swedish Literature in Finland", 2)

#pages = getcatpages(pywikibot, commonssite, "Category:Salon Strindberg & Atelier Universal")

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


#pages = getpagesrecurse(pywikibot, commonssite, "Category:Journalists from Finland", 2)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finnish Museum of Photography", 3)

# many are from valokuvataiteenmuseo via flickr
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical photographs of Helsinki by I. K. Inha", 1)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finnish Museum of Photography", 3)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Files from the Finnish Museum of Photography", 0)


#pages = getpagesrecurse(pywikibot, commonssite, "Category:Photographs by I. K. Inha", 2)
#pages = getcatpages(pywikibot, commonssite, "Category:Finnish Agriculture (1899) by I. K. Inha")

# many are from valokuvataiteenmuseo via flickr
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical photographs of Helsinki by I. K. Inha", 1)

# many from fng via flickr
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Photographs by Hugo Simberg", 2)

pages = getcatpages(pywikibot, commonssite, "Category:Teachers from Finland")


cachedb = CachedImageData() 
cachedb.opencachedb()

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
        
    file_media_identifier='M' + str(filepage.pageid)
    file_info = filepage.latest_file_info
    oldtext=page.text
    
    # there may be other media than images as well
    strmime = str(file_info.mime)
    if (isSupportedMimetype(strmime) == False):
        continue

    print(" ////////", rowcount, "/", len(pages), ": [ " + page.title() + " ] ////////")
    print("latest change in commons: " + filepage.latest_file_info.timestamp.isoformat())

    #item = pywikibot.ItemPage.fromPage(page) # can't use in commons, no related wikidata item
    # note: data_item() causes exception if wikibase page isn't made yet, see for an alternative
    # repo == site == commonssite
    if (doessdcbaseexist(page) == False):
        print("Wikibase item does not yet exist for: " + page.title() )
        
        wditem = page.data_item()  # Get the data item associated with the page
        sdcdata = wditem.get_data_for_new_entity() # get new sdc item
        
        ## add something like P1163 (mime-type) to force creation of sdc-data
        print("adding mime-type: " + str(file_info.mime))
        mime_claim = addmimetypetosdc(pywikibot, wikidata_site, file_info.mime)
        commonssite.addClaim(wditem, mime_claim)

        #file_info.mime == 'image/jpeg'
        #addSdcCaption(commonssite, file_media_identifier, "fi", "testing")
        
        # alternate method
        #addSdcMimetype(commonssite, file_media_identifier, str(file_info.mime))

        if (doessdcbaseexist(page) == False):
            print("ERROR: Failed adding Wikibase item for: " + page.title() )
            exit(1)
        #continue
        
    wditem = page.data_item()  # Get the data item associated with the page
    sdcdata = wditem.get() # all the properties in json-format
    
    if "statements" not in sdcdata:
        print("No statements found for claims: " + page.title())
        continue
    claims = sdcdata['statements']  # claims are just one step from dataproperties down

    print("Wikibase statements found for: " + page.title() )

    # find source urls in template(s) in commons-page
    srcurls = getsourceurlfrompagetemplate(page.text)
    if (srcurls == None):
        print("DEBUG: no urls found in templates of " + page.title())
        continue
    if (len(srcurls) == 0):
        print("DEBUG: no urls found in templates of " + page.title())
        continue

    kkid = ""
    finnaid = ""
    finnarecordid = ""
    for srcvalue in srcurls:
        if (srcvalue.find("elonet.finna.fi") > 0):
            # elonet-service differs
            continue
        if (srcvalue.find("kuvakokoelmat.fi") > 0):
            kkid = getkuvakokoelmatidfromurl(srcvalue)
        if (srcvalue.find("finna.fi") > 0):
            # try metapage-id first
            finnarecordid = getrecordid(srcvalue)
            # try old-style/download id
            if (finnarecordid == ""):
                finnaid = getlinksourceid(srcvalue)

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
            print("NOTE: " + page.title() + " has external urls but not in expected place")
            # might have something usable..
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
        
    if (len(finnaid) >= 50):
        print("WARN: finna id in " + page.title() + " is unusually long? bug or garbage in url? ")
    if (len(finnaid) <= 5):
        print("WARN: finna id in " + page.title() + " is unusually short? bug or garbage in url? ")
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
    
    print("finna record ok: " + finnaid)
    
    # note: if there are no collections, don't remove from commons as they may have manual additions
    collectionqcodes = list()
    if "collections" not in finna_record['records'][0]:
        print("WARN: 'collections' not found in finna record: " + finnaid)
    else:
        # collections: expecting ['Historian kuvakokoelma', 'Studio Kuvasiskojen kokoelma']
        finna_collections = finna_record['records'][0]['collections']

        #if ("Antellin kokoelma" in finna_collections):
            #print("Skipping collection (can't match by hash due similarities): " + finnaid)
            #continue

        # lookup qcode by label TODO: fetch from wikidata 
        for coll in finna_collections:
            if coll in d_labeltoqcode:
                collectionqcodes.append(d_labeltoqcode[coll])

    # TODO: add caption to sdc?
    #finna_title = finna_record['records'][0]['title']
    #addSdcCaption(commonssite, file_media_identifier, "fi", finna_title)

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

    # use helper to check that it is correctly formed
    imagesExtended = getImagesExtended(finna_record)
    if (imagesExtended == None):
        print("WARN: 'imagesExtended' not found in finna record, skipping: " + finnaid)
        continue

    # TODO! Python throws error if image is larger than 178956970 pixels
    # so we can't handle really large images. Check for those and skip them..

    # 'images' can have array of multiple images, need to select correct one
    # -> loop through them (they should have just different &index= in them)
    # and compare with the image in commons
    imageList = finna_record['records'][0]['images']

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
        
        commonshash = getimagehash(commons_image)
        
        # same lengths for p and d hash, keep change time from commons
        cachedb.addorupdate(commons_image_url, 
                            commonshash[0], commonshash[1], commonshash[0], commonshash[2], 
                            filepage.latest_file_info.timestamp)

        print("Commons-image data added to cache for: " + page.title() )
        tpcom = cachedb.findfromcache(commons_image_url)
    else:
        # compare timestamp: if too old recheck the hash
        print("Commons-image cached data found for: " + page.title() + " timestamp: " + tpcom['timestamp'].isoformat())
        
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
            
            commonshash = getimagehash(commons_image)
            cachedb.addorupdate(commons_image_url, 
                                commonshash[0], commonshash[1], commonshash[0], commonshash[2], 
                                filepage.latest_file_info.timestamp)
            tpcom = cachedb.findfromcache(commons_image_url)

    # just sanity check: if cache is cutting url we might get wrong entry as result
    if (tpcom['url'] != commons_image_url):
        print("ERROR: commons url mismatch for: " + page.title() )
        exit(1)

    match_found = False
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
            
            finnahash = getimagehash(finna_image)
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
                    
                finnahash = getimagehash(finna_image)
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
            qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')  # Replace with the property ID for "operator"
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

        commonssite.addClaim(wditem, source_claim)
                

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
        #else:
            #print("license found in statements, OK")
            #if (checklicensesources(claims, copyrightlicense, sourceurl) == False):
                #print("license source not found in statements")
            #else:
                #print("license source found in statements, OK")

    # TODO: subjects / "kuvausaika 08.01.2016" -> inception
    inceptiondt = parseinceptionfromfinna(finna_record)
    if (inceptiondt != None):
        #print("DEBUG: found inception date for: " + finnaid + " " + inceptiondt.isoformat())
        if (isinceptioninstatements(claims, inceptiondt) == False):
            inc_claim = addinceptiontosdc(pywikibot, wikidata_site, inceptiondt)
            commonssite.addClaim(wditem, inc_claim)
        else:
            print("DEBUG: sdc already has inception date for: " + finnaid)
    else:
        print("DEBUG: could not parse inception date for: " + finnaid)


    # check SDC and try match with finna list collectionqcodes
    collectionstoadd = getcollectiontargetqcode(claims, collectionqcodes)
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
    if (isfinnaidinstatements(claims, finnaid) == False):
        print("adding finna id to statements: " + finnaid)
        
        finna_claim = addfinnaidtostatements(pywikibot, wikidata_site, finnaid)
        commonssite.addClaim(wditem, finna_claim)
    else:
        print("id found, not adding again")

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

