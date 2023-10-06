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

def get_finna_record(finnaid):

    url="https://api.finna.fi/v1/record?id=" +  urllib.parse.quote_plus(finnaid)
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
    return tuple((hashlen, phash, dhash))
    
# convert string to base 16 integer for calculating difference
def converthashtoint(h, base=16):
    return int(str(h), base)

# Compares if the image is same using similarity hashing
# method is to convert images to 64bit integers and then
# calculate hamming distance. 
#
def is_same_image(imghash1, imghash2, hashlen=8):
    
    # check that hash lengths are same
    if (imghash1[1] != imghash2[1] or imghash1[3] != imghash2[3]):
        print("Hash length mismatch")
        return False

    phash_int1 = converthashtoint(imghash1[2])
    dhash_int1 = converthashtoint(imghash1[4])

    phash_int2 = converthashtoint(imghash2[2])
    dhash_int2 = converthashtoint(imghash2[4])

    # Hamming distance difference (from integers)
    phash_diff = bin(phash_int1 ^ phash_int2).count('1')
    dhash_diff = bin(dhash_int2 ^ dhash_int2).count('1') 

    # print hamming distance
    if (phash_diff == 0 and dhash_diff == 0):
        print("Both hashes are equal")
    else:
        print("Phash diff: " + str(phash_diff) + ", image1: " + str(imghash1[2]) + ", image2: " + str(imghash2[2]))
        print("Dhash diff: " + str(dhash_diff) + ", image1: " + str(imghash1[4]) + ", image2: " + str(imghash2[4]))

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
                            
    return Image.open(io.BytesIO(response.content))

# ----- CachedImageData
class CachedImageData:
    def opencachedb(self):
        # created if it doesn't yet exist
        self.conn = sqlite3.connect("pwbimagedatacache.db")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS imagecache(url, phashlen, phashval, dhashlen, dhashval, timestamp)")

    def addtocache(self, url, plen, pval, dlen, dval, ts):

        sqlq = "INSERT INTO imagecache VALUES ('"+ url + "', "+ str(plen) + ", '"+ str(pval) + "', "+ str(dlen) + ", '"+ str(dval) + "', '" + ts.isoformat() + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def updatecache(self, url, plen, pval, dlen, dval, ts):

        sqlq = "UPDATE imagecache SET phashlen "+ str(plen) + ", phashval = '"+ str(pval) + "', dhashlen = "+ str(dlen) + ", dhashval '"+ str(dval) + "', timestamp = '" + ts.isoformat() + "' WHERE url = '"+ url + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findfromcache(self, url):
        sqlq = "SELECT * FROM imagecache WHERE url = '" + url + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = res.fetchall()
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            return tuple((row[0], row[1], row[2], row[3], row[4], datetime.fromisoformat(row[5])))

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

# link might have "show?id=<id>" which we handle here
# if it has "Record/<id>" handle it separately
def getlinksourceid(oldsource):
    strlen = len("id=")
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return ""
    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)

def getrecordid(oldsource):
    strlen = len("/Record/")
    indexid = oldsource.find("/Record/")
    if (indexid < 0):
        return ""
    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)
    
# commons source may have human readable stuff in it
# parse to plain url
def geturlfromsource(source):
    #print("DEBUG: source url is: " + source)

    protolen = len("http://")
    index = source.find("http://")
    if (index < 0):
        protolen = len("https://")
        index = source.find("https://")
        if (index < 0):
            # no url in string
            return ""

    indexproto = index+protolen

    # try to find space or something
    indexend = source.find(" ", indexproto)
    if (indexend > 0):
        source = source[:indexend]

    # wiki-markup end of url
    indexend = source.find("]", indexproto)
    if (indexend > 0):
        source = source[:indexend]
    indexend = source.find("|", indexproto)
    if (indexend > 0):
        source = source[:indexend]
    indexend = source.find("}", indexproto)
    if (indexend > 0):
        source = source[:indexend]
    indexend = source.find("\n", indexproto)
    if (indexend > 0):
        source = source[:indexend]

    if (index > 0):
        # finally, if there was anything before start of url
        # -> strip to just url 
        #indexend = len(source)-1 # just use string length
        source = source[index:]

    #print("DEBUG: found source url: " + source)
    return source

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

# check if publisher exists in data
def ispublisherinstatements(statements, publisherqcode):
    if "P7482" not in statements: # P7482 is source of file
        #print("source of file not found")
        return False
    claimlist = statements["P7482"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q74228490"): # file available on internet
            #print("not available on internet") # DEBUG
            continue
    
        if "P123" in claim.qualifiers:
            foiquali = claim.qualifiers["P123"]
            for fclaim in foiquali:
                ftarget = fclaim.getTarget()
                fqcode = getqcodefromwikidatalink(ftarget)
                if (fqcode == publisherqcode):
                    #print("publisher qcode found: " + fqcode)
                    return True

    #print("did not find publisherqcode: " + str(publisherqcode))
    return False

# is license in statements
#P275, "CC BY 4.0" is Q20007257
def islicenseinstatements(statements, license):
    if (license != "CC BY 4.0"):
        # bug? we only support one license currently
        return False
    if "P275" not in statements:
        return False
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode == "Q20007257"):
            return True
        #else:
            # may have multiple licenses, just ignore (cc by sa/nc..)
            #print("License is NOT as expected, Q-code: " + targetqcode)

    return False

# check if 'P275' is missing 'P854' with reference url
def checklicensesources(statements, sourceurl):
    if "P275" not in statements:
        print("license property not in statements")
        return False

    # note: there may be more than on license per item (not equal)
    # so check source is under appropriate license..
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q20007257"): # not our license
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
def addlicensetostatements(pywikibot, wikidata_site, license, sourceurl):
    if (license != "CC BY 4.0"):
        # bug? we only support one license currently
        return False

    licqcode = "Q20007257"
    lic_claim = pywikibot.Claim(wikidata_site, "P275") # property ID for "license"
    qualifier_targetlic = pywikibot.ItemPage(wikidata_site, licqcode)
    lic_claim.setTarget(qualifier_targetlic)
    
    # note: this add qualifer but we want "reference" type
    qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
    qualifier_url.setTarget(sourceurl)
    lic_claim.addSource(qualifier_url, summary='Adding reference URL qualifier')
    # is there "addreference()"?
    
    return lic_claim

def addreferencetolicense(pywikibot, wikidata_site, license, sourceurl):
    if (license != "CC BY 4.0"):
        # bug? we only support one license currently
        return False

    # if there are multiple licenses, check that we add source to right one
    claimlist = statements["P275"]    
    for claim in claimlist:
        target = claim.getTarget()
        targetqcode = getqcodefromwikidatalink(target)
        if (targetqcode != "Q20007257"): # not our license
            #print("DEBUG: unsupported license: " + targetqcode)
            continue

        # note: this add qualifer but we want "reference" type
        #qualifier_url = pywikibot.Claim(wikidata_site, 'P854')  # property ID for source URL (reference url)
        #qualifier_url.setTarget(sourceurl)
        #claim.addSource(qualifier_url, summary='Adding reference URL qualifier')
        # is there "addreference()"?
    
    return True

def isidinstatements(statements, newid):
    if "P9478" not in statements:
        return False
    claimlist = statements["P9478"]    
    for claim in claimlist:
        # target is expected to be like: "musketti." or "museovirasto."
        target = claim.getTarget()
        if (target == newid):
            # match found: no need to add same ID again
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

def getnewsourceforfinna(finnarecord):
    return "<br>Image record page in Finna: [https://finna.fi/Record/" + finnarecord + " " + finnarecord + "]\n"

def getqcodeforfinnapublisher(finna_record):
    if "records" not in finna_record:
        print("ERROR: no records in finna record")
        return ""

    records = finna_record['records'][0]
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

    qpublisher = ""
    for key, val in finnainstitutions.items():
        #print("val is: " + val)
        if (val == "Museovirasto"):
            qpublisher = "Q3029524"
            break
        if (val == "Sotamuseo"):
            qpublisher = "Q283140"
            break
    if (len(qpublisher) > 0):
        print("found qcode for publisher: " + qpublisher)
    return qpublisher

# filter blocked images that can't be updated for some reason
def isblockedimage(page):
    pagename = str(page)

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

# TODO: check wikidata for correct qcodes
# 
# qcode of collections -> label
d_qcodetolabel = dict()
d_qcodetolabel["Q118976025"] = "Studio Kuvasiskojen kokoelma"
d_qcodetolabel["Q107388072"] = "Historian kuvakokoelma" # /Museovirasto/Historian kuvakokoelma/
d_labeltoqcode = dict()
d_labeltoqcode["Studio Kuvasiskojen kokoelma"] = "Q118976025"
d_labeltoqcode["Historian kuvakokoelma"] = "Q107388072" # /Museovirasto/Historian kuvakokoelma/

# Accessing wikidata properties and items
wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)
#pages = getcatpages(pywikibot, commonssite, "Archaeologists from Finland", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Charles Riis", True)
pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Daniel Nyblin")
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Archaeology in Finland")

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by photographer from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:People of Finland by year", True)

#pages = getcatpages(pywikibot, commonssite, "Category:History of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Aviation Museum")

#pages = getcatpages(pywikibot, commonssite, "Files uploaded by FinnaUploadBot")

#pages = getcatpages(pywikibot, commonssite, "Category:Vyborg in the 1930s")
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Vyborg", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Miss Finland winners", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Architects from Finland", True)

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist2')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/sakuvat')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/europeana-kuvat')

cachedb = CachedImageData() 
cachedb.opencachedb()

rowcount = 1
#rowlimit = 10

print("Pages found: " + str(len(pages)))

for page in pages:
    # 14 is category -> recurse into subcategories
    #
    if page.namespace() != 6:  # 6 is the namespace ID for files
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

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")
    rowcount += 1

    #item = pywikibot.ItemPage.fromPage(page) # can't use in commons, no related wikidata item
    # note: data_item() causes exception if wikibase page isn't made yet, see for an alternative
    # repo == site == commonssite
    #testitem = pywikibot.ItemPage(commonssite, 'Q1') # test something like this?
    if (doessdcbaseexist(page) == False):
        print("Wikibase item does not yet exist for: " + page.title() )
        #file_info.mime == 'image/jpeg'
        #addSdcCaption(commonssite, file_media_identifier, "fi", "testing")
        
        ## TODO: add something like P1163 (mime-type) to force creation of sdc-data ?
        #print("adding mime-type: " + str(file_info.mime))
        
        # error: invalid snak-data -> need something else to force creation
        #addSdcMimetype(commonssite, file_media_identifier, str(file_info.mime))

        #if (doessdcbaseexist(page) == False):
            #print("ERROR: Failed adding Wikibase item for: " + page.title() )
        continue

    wditem = page.data_item()  # Get the data item associated with the page
    sdcdata = wditem.get() # all the properties in json-format
    
    if "statements" not in sdcdata:
        print("No statements found for claims: " + page.title())
        continue
    claims = sdcdata['statements']  # claims are just one step from dataproperties down

    print("Wikibase statements found for: " + page.title() )

    #site = pywikibot.Site("wikidata", "wikidata")
    #repo = site.data_repository()
    #item = pywikibot.ItemPage(repo, "Q2225")    
    
    wikicode = mwparserfromhell.parse(page.text)
    templatelist = wikicode.filter_templates()

    # should store new format id to picture source
    # -> use setfinnasource.py for these for now
    #addFinnaIdForKuvakokoelmatSource = False

    kkid = ""
    finnaid = ""
    finnasource = ""
    for template in wikicode.filter_templates():
        # at least three different templates have been used..
        if template.name.matches("Information") or template.name.matches("Photograph") or template.name.matches("Artwork") or template.name.matches("Art Photo"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                
                if (srcvalue.find("kuvakokoelmat.fi") > 0):
                    kkid = getkuvakokoelmatidfromurl(srcvalue)
                if (srcvalue.find("finna.fi") > 0):
                    finnasource = srcvalue
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        finnaid = getlinksourceid(srcvalue)
                        if (finnaid == ""):
                            print("no id and no record found")
                        break

            if template.has("source"):
                par = template.get("source")
                srcvalue = str(par.value)
                
                if (srcvalue.find("kuvakokoelmat.fi") > 0):
                    kkid = getkuvakokoelmatidfromurl(srcvalue)
                if (srcvalue.find("finna.fi") > 0):
                    finnasource = srcvalue
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        finnaid = getlinksourceid(srcvalue)
                        if (finnaid == ""):
                            print("no id and no record found")
                        break

    if (len(finnaid) == 0 and len(kkid) > 0):
        finnaid = convertkuvakokoelmatid(kkid)
        finnaid = urllib.parse.quote(finnaid) # quote for url
        print("Converted old id in: " + page.title() + " from: " + kkid + " to: " + finnaid)
        # TODO: update source information to include new id
        # -> use setfinnasource.py for now
        #addFinnaIdForKuvakokoelmatSource = True

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
    if (finnaid.find("musketti") < 0 and finnaid.find("museovirasto") < 0 and finnaid.find("hkm") < 0):
        print("WARN: unexpected id in: " + page.title() + ", id: " + finnaid)
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
    sourceurl = "https://www.finna.fi/Record/" + finnaid

    if (finnaid.find("musketti") >= 0 or finnaid.find("hkm.HKM") >= 0):
        # check if the source has something other than url in it as well..
        # if it has some human-readable things try to parse real url
        if (len(finnasource) > 0):
            finnaurl = geturlfromsource(finnasource)
            if (finnaurl == ""):
                print("WARN: could not parse finna url from source in " + page.title() + ", source: " + finnasource)
                #continue
    
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
    if (finna_record == None):
        print("WARN: failed to retrieve finna record for: " + finnaid)
        continue
    if (finna_record['status'] != 'OK'):
        print("Skipping (status not OK): " + finnaid + " status: " + finna_record['status'])
        continue

    if (finna_record['resultCount'] != 1):
        print("Skipping (result not 1): " + finnaid + " count: " + str(finna_record['resultCount']))
        continue

    print("finna record ok: " + finnaid)

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
    finna_collections = finna_record['records'][0]['collections']

    #if ("Antellin kokoelma" in finna_collections):
        #print("Skipping collection (can't match by hash due similarities): " + finnaid)
        #continue

    # TODO: add caption to sdc?
    #finna_title = finna_record['records'][0]['title']
    #addSdcCaption(commonssite, file_media_identifier, "fi", finna_title)
    
    collectionqcodes = list()
    # lookup qcode by label TODO: fetch from wikidata 
    for coll in finna_collections:
        if coll in d_labeltoqcode:
            collectionqcodes.append(d_labeltoqcode[coll])

    publisherqcode = getqcodeforfinnapublisher(finna_record)
    if (len(publisherqcode) == 0):
        print("WARN: failed to find a publisher in finna for: " + finnaid)
    else:
        print("found publisher " + publisherqcode + " in finna for: " + finnaid)
        if (ispublisherinstatements(claims, publisherqcode) == False):
            print("publisher " + publisherqcode + " not found in commons for: " + finnaid)
        else:
            print("publisher " + publisherqcode + " found in commons for: " + finnaid)

    if "imagesExtended" not in finna_record['records'][0]:
        print("WARN: 'imagesExtended' not found in finna record, skipping: " + finnaid)
        continue

    # Test copyright (old field: rights, but request has imageRights?)
    # imageRights = finna_record['records'][0]['imageRights']
    imagesExtended = finna_record['records'][0]['imagesExtended'][0]
    # should be CC BY 4.0 or Public domain
    copyrightlicense = imagesExtended['rights']['copyright']
    if (copyrightlicense != "CC BY 4.0" and copyrightlicense != "PDM"):
        print("Incorrect copyright: " + copyrightlicense)
        continue

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
        commonshash = getimagehash(commons_image)
        # same lengths for p and d hash
        cachedb.addorupdate(commons_image_url, commonshash[0], commonshash[1], commonshash[0], commonshash[2], datetime.now())
        tpcom = cachedb.findfromcache(commons_image_url)
    #else:
        # compare timestamp: if too old recheck the hash


    match_found = False
    if (len(imageList) == 1):
    
        finna_image_url = "https://finna.fi" + imagesExtended['urls']['large']

        tpfinna = cachedb.findfromcache(finna_image_url)
        if (tpfinna == None):
            # get image from finnafor comparison:
            # try to use same size
            finna_image = downloadimage(finna_image_url)
            finnahash = getimagehash(finna_image)
            # same lengths for p and d hash
            cachedb.addorupdate(finna_image_url, finnahash[0], finnahash[1], finnahash[0], finnahash[2], datetime.now())
            tpfinna = cachedb.findfromcache(finna_image_url)
        #else:
            # compare timestamp: if too old recheck the hash
        
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
                finnahash = getimagehash(finna_image)
                # same lengths for p and d hash
                cachedb.addorupdate(finna_image_url, finnahash[0], finnahash[1], finnahash[0], finnahash[2], datetime.now())
                tpfinna = cachedb.findfromcache(finna_image_url)
            #else:
                # compare timestamp: if too old recheck the hash


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
    
    #continue # TESTING

    flag_add_source = False
    flag_add_collection = False
    flag_add_finna = False

    if "P7482" not in claims:
        # P7482 "source of file" 
        item_internet = pywikibot.ItemPage(wikidata_site, 'Q74228490')  # file available on the internet
        source_claim = pywikibot.Claim(wikidata_site, "P7482") # property ID for "source of file"
        source_claim.setTarget(item_internet)

        # P973 "described at URL"
        qualifier_url = pywikibot.Claim(wikidata_site, 'P973')  # property ID for "described at URL"
        qualifier_url.setTarget(sourceurl)
        source_claim.addQualifier(qualifier_url, summary='Adding described at URL qualifier')

        # P137 "operator"
        qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')  # Replace with the property ID for "operator"
        qualifier_targetop = pywikibot.ItemPage(wikidata_site, 'Q420747')  # National Library of Finland (Kansalliskirjasto)
        qualifier_operator.setTarget(qualifier_targetop)
        source_claim.addQualifier(qualifier_operator, summary='Adding operator qualifier')

        if (len(publisherqcode) > 0):
            if (ispublisherinstatements(claims, publisherqcode) == False):
                # P123 "publisher"
                # Q3029524 Finnish Heritage Agency (Museovirasto)
                qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')  # property ID for "publisher"
                qualifier_targetpub = pywikibot.ItemPage(wikidata_site, publisherqcode)  # Finnish Heritage Agency (Museovirasto)
                qualifier_publisher.setTarget(qualifier_targetpub)
                source_claim.addQualifier(qualifier_publisher, summary='Adding publisher qualifier')

        commonssite.addClaim(wditem, source_claim)
        flag_add_source = True
    else:
        print("no need to add source")

    # is license in statements
    #P275, "CC BY 4.0" is Q20007257
    #P854, sourceurl
    #if (copyrightlicense == "CC BY 4.0"): # maybe be PDM
    #if (islicenseinstatements(claims, "CC BY 4.0") == False):
        #print("NOTE: license missing or not same in statements")
        #lic_claim = addlicensetostatements(pywikibot, wikidata_site, "CC BY 4.0", sourceurl)
        #commonssite.addClaim(wditem, lic_claim)
    #else:
        #print("license found in statements, OK")
        #if (checklicensesources(claims, sourceurl) == False):
            #print("license source not found in statements")
        #else:
            #print("license source found in statements, OK")

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
            
        flag_add_collection = True
    else:
        print("no need to add collections")

    # if the stored ID is not same (new ID) -> add new
    if (isidinstatements(claims, finnaid) == False):
        print("adding finna id to statements: " + finnaid)
        
        finna_claim = addfinnaidtostatements(pywikibot, wikidata_site, finnaid)
        commonssite.addClaim(wditem, finna_claim)
        flag_add_finna = True
    else:
        print("id found, not adding again")

    if (flag_add_source == False and flag_add_collection == False and flag_add_finna == False):
        print("Nothing to add, skipping.")
        continue

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

