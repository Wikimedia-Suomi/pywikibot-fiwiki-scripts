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

import urllib3


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

def get_finna_record(id):

    url="https://api.finna.fi/v1/record?id=" +  urllib.parse.quote_plus(id)
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
        exit(1)

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

# Compares if the image is same using similarity hashing
# method is to convert images to 64bit integers and then
# calculate hamming distance. 

def is_same_image(url1, url2):

    # Open the image1 with Pillow
    im1 = Image.open(urllib.request.urlopen(url1))
    phash1_int=calculate_phash(im1)
    dhash1_int=calculate_dhash(im1)

    # Open the image2 with Pillow
    im2 = Image.open(urllib.request.urlopen(url2))
    phash2_int=calculate_phash(im2)
    dhash2_int=calculate_dhash(im2)

    # Hamming distance difference
    phash_diff = bin(phash1_int ^ phash2_int).count('1')
    dhash_diff = bin(dhash1_int ^ dhash2_int).count('1') 

    # print hamming distance
    print("Phash diff: " + str(phash_diff))
    print("Dhash diff: " + str(dhash_diff))

    # max distance for same is that least one is 0 and second is max 3

    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    else:
        return False

def download_and_convert_tiff_to_jpg(url):
    response = requests.get(url, stream=True)
    response.raise_for_status()
                            
    tiff_image = Image.open(io.BytesIO(response.content))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fp:
        tiff_image.convert('RGB').save(fp, "JPEG", quality=95)
    return fp.name    

# ----- /FinnaData

# strip id from other things that may be after it:
# there might be part of url or some html in same field..
def stripid(oldsource):
    # space after url?
    indexend = oldsource.find(" ")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # html tag after url?
    indexend = oldsource.find("<")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("&")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("?")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

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
    protolen = len("http://")
    index = source.find("http://")
    if (index < 0):
        protolen = len("https://")
        index = source.find("https://")
        if (index < 0):
            # no url in string
            return ""

    # try to find space or something            
    indexend = source.find(" ", index+protolen)
    if (indexend < 0):
        # no space or other clear separator -> just use string length
        indexend = len(source)-1
        
    return source[index:indexend]

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
    if (kkid.startswith("HK") == False):
        print("does not start appropriately: " + kkid)
        return ""

    index = kkid.find("_")
    if (index < 0):
        print("no underscores: " + kkid)
        return ""
    # one underscore to colon
    # underscores to dash
    # add prefix
    kkid = kkid[:index] + ":" + kkid[index+1:]
    kkid = kkid.replace("_", "-")
    musketti = "musketti.M012:" + kkid
    return musketti

# if there's garbage in id, strip to where it ends
def leftfrom(string, char):
    index = string.find(char)
    if (index > 0):
        return string[:index]

    return string
    
# parse claims or statements from commons SDC
def getcollectiontargetqcode(statements, collections):
    if "P195" not in statements:
        return collections
    
    claimlist = statements["P195"]
    for claim in claimlist:
        # target is expected to be like: [[wikidata:Q118976025]]
        target = claim.getTarget()

        targetqcode = str(target)        
        index = targetqcode.find(":")
        if (index > 0):
            indexend = targetqcode.find("]", index)
            targetqcode = targetqcode[index+1:indexend]

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


# fetch metapage from finna and try to parse current ID from the page
# since we might have obsolete ID.
# new ID is needed API query.
def parsemetaidfromfinnapage(finnaurl):

    finnapage = ""

    try:
        request = urllib.request.Request(finnaurl)
        print("request done: " + finnaurl)

        response = urllib.request.urlopen(request)
        if (response.readable() == False):
            print("response not readable")

        htmlbytes = response.read()
        finnapage = htmlbytes.decode("utf8")

        #print("page: " + finnapage)
        
    except urllib.error.HTTPError as e:
        print(e.__dict__)
        return ""
    except urllib.error.URLError as e:
        print(e.__dict__)
        return ""
    #except:
        #print("failed to retrieve finna page")
        #return ""
        
    attrlen = len('data-record-id="')
    indexid = finnapage.find('data-record-id="')
    if (indexid < 0):
        return ""
        
    indexid = indexid+attrlen
    indexend = finnapage.find('"', indexid)
    if (indexend < 0):
        return ""

    return finnapage[indexid:indexend]

def getnewsourceforfinna(finnarecord):
    return "<br>Image record page in Finna: [https://finna.fi/Record/" + finnarecord + " " + finnarecord + "]\n"

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
pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)

rowcount = 1
rowlimit = 500

for page in pages:
    # 14 is category -> recurse into subcategories
    #
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    filepage = pywikibot.FilePage(page)
    if filepage.isRedirectPage():
        continue
    file_info = filepage.latest_file_info

    oldtext=page.text

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")
    rowcount += 1

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
        if template.name.matches("Information") or template.name.matches("Photograph") or template.name.matches("Artwork"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                if (srcvalue.find("kuvakokoelmat.fi") > 0):
                    kkid = getkuvakokoelmatidfromurl(srcvalue)
                if (srcvalue.find("finna.fi") > 0):
                    finnasource = srcvalue
                    finnaid = getlinksourceid(srcvalue)
                    if (finnaid == ""):
                        finnaid = getrecordid(srcvalue)
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
                    finnaid = getlinksourceid(srcvalue)
                    if (finnaid == ""):
                        finnaid = getrecordid(srcvalue)
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
 
    # kuvasiskot has "musketti" as part of identier, alternatively "museovirasto" may be used in some cases
    if (finnaid.find("musketti") < 0 and finnaid.find("museovirasto") < 0):
        print("Skipping. " + page.title() + " - not appropriate id: " + finnaid)
        continue
        
    if (len(finnaid) >= 50):
        print("WARN: finna id in " + page.title() + " is unusually long? bug or garbage in url? ")
    if (len(finnaid) <= 5):
        print("WARN: finna id in " + page.title() + " is unusually short? bug or garbage in url? ")
    if (finnaid.find("?") > 0 or finnaid.find("&") > 0 or finnaid.find("<") > 0):
        print("WARN: finna id in " + page.title() + " has unexpected characters, bug or garbage in url? ")
        
        # strip pointless parts if any
        finnaid = leftfrom(finnaid, "<")
        finnaid = leftfrom(finnaid, "?")
        finnaid = leftfrom(finnaid, "&")
        print("note: finna id in " + page.title() + " is " + finnaid)
        
    if (finnaid.endswith("\n")):
        print("WARN: finna id in " + page.title() + " ends with newline ")
        finnaid = finnaid[:len(finnaid)-1]

    print("finna ID found: " + finnaid)
    sourceurl = "https://www.finna.fi/Record/" + finnaid

    if (finnaid.find("musketti") >= 0):
        # check if the source has something other than url in it as well..
        # if it has some human-readable things try to parse real url
        if (len(finnasource) > 0):
            finnaurl = geturlfromsource(finnasource)
            if (finnaurl == ""):
                print("WARN: could not parse finna url from source in " + page.title() + " , skipping, source: " + finnasource)
                continue
    
        # obsolete id -> try to fetch page and locate current ID
        finnaid = parsemetaidfromfinnapage(sourceurl)
        if (finnaid == ""):
            print("WARN: could not parse current finna id in " + page.title() + " , skipping, url: " + sourceurl)
            continue
        if (finnaid.find("museovirasto.") == 0):
            print("new finna ID found: " + finnaid)
            sourceurl = "https://www.finna.fi/Record/" + finnaid
        else:
            print("WARN: unexpected finna id in " + page.title() + " , skipping, id from finna: " + finnaid)
            continue

    finna_record = get_finna_record(finnaid)
    if (finna_record['status'] != 'OK'):
        print("Skipping (status not OK): " + finnaid + " status: " + finna_record['status'])
        continue

    if (finna_record['resultCount'] != 1):
        print("Skipping (result not 1): " + finnaid + " count: " + str(finna_record['resultCount']))
        continue

    print("finna record ok: " + finnaid)
        
    # collections: expecting ['Historian kuvakokoelma', 'Studio Kuvasiskojen kokoelma']
    finna_collections = finna_record['records'][0]['collections']
    
    collectionqcodes = list()
    # lookup qcode by label TODO: fetch from wikidata 
    for coll in finna_collections:
        if coll in d_labeltoqcode:
            collectionqcodes.append(d_labeltoqcode[coll])

    # Test copyright
    imagesExtended = finna_record['records'][0]['imagesExtended'][0]
    if (imagesExtended['rights']['copyright'] != "CC BY 4.0"):
        print("Incorrect copyright: " + imagesExtended['rights']['copyright'])
        continue

    # Confirm that images are same using imagehash
    finna_thumbnail_url = "https://finna.fi" + imagesExtended['urls']['small']
    commons_thumbnail_url = filepage.get_file_url(url_width=500)

    # Test if image is same using similarity hashing
    if not is_same_image(finna_thumbnail_url, commons_thumbnail_url):
        print("Not same image, skipping: " + finnaid)
        continue

    #item = pywikibot.ItemPage.fromPage(page) # can't use in commons, no related wikidata item
    # note: this causes exception if page isn't made yet, see alternative
    wditem = page.data_item()  # Get the data item associated with the page
    data = wditem.get() # all the properties in json-format
    
    if "statements" not in data:
        print("No statements found for claims: " + finnaid)
        continue
    claims = data['statements']  # claims are just one step from dataproperties down

    flag_add_source = False
    flag_add_collection = False
    flag_add_finna = False

    claim_sourcep = 'P7482'  # property ID for "source of file"
    if claim_sourcep not in claims:
        # P7482 "source of file" 
        item_internet = pywikibot.ItemPage(wikidata_site, 'Q74228490')  # file available on the internet
        source_claim = pywikibot.Claim(wikidata_site, claim_sourcep)
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

        # P123 "publisher"
        # Q3029524 Finnish Heritage Agency (Museovirasto)
        qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')  # property ID for "publisher"
        qualifier_targetpub = pywikibot.ItemPage(wikidata_site, 'Q3029524')  # Finnish Heritage Agency (Museovirasto)
        qualifier_publisher.setTarget(qualifier_targetpub)
        source_claim.addQualifier(qualifier_publisher, summary='Adding publisher qualifier')

        flag_add_source = True

    # check SDC and try match with finna list collectionqcodes
    collectionstoadd = getcollectiontargetqcode(claims, collectionqcodes)
    if (len(collectionstoadd) > 0):
        claim_collp = 'P195'  # property ID for "collection"
        # P195 "collection"
        coll_claim = pywikibot.Claim(wikidata_site, claim_collp)

        # Q118976025 "Studio Kuvasiskojen kokoelma"
        for collection in collectionstoadd:
            qualifier_targetcoll = pywikibot.ItemPage(wikidata_site, collection)
            coll_claim.setTarget(qualifier_targetcoll)

        flag_add_collection = True

    # if the stored ID is not same (new ID) -> add new
    if (isidinstatements(claims, finnaid) == False):
        print("adding finna id to statements: " + finnaid)
        # 
        claim_finnaidp = 'P9478'  # property ID for "finna ID"
        finna_claim = pywikibot.Claim(wikidata_site, claim_finnaidp)
        # url might have old style id as quoted -> no need with new id
        finnaunquoted = urllib.parse.unquote(finnaid)
        finna_claim.setTarget(finnaunquoted)

        flag_add_finna = True
    else:
        print("id found, not adding again")

    if (flag_add_source == False and flag_add_collection == False and flag_add_finna == False):
        print("Nothing to add, skipping.")
        continue

    #pywikibot.info('----')
    #pywikibot.showDiff(oldtext, newtext,2)
    summary='Adding structured data to file'
    pywikibot.info('Edit summary: {}'.format(summary))

    question='Do you want to accept these changes?'
    choice = pywikibot.input_choice(
                question,
                [('Yes', 'y'),('No', 'N'),('Quit', 'q')],
                default='N',
                automatic_quit=False
            )

    pywikibot.info(choice)
    if choice == 'q':
        print("Asked to exit. Exiting.")
        exit()

    if choice == 'y':
        # script setfinnasource is used for this
        #if (addFinnaIdForKuvakokoelmatSource == True):
            #page.text=newtext
            #page.save(summary)
            
        if (flag_add_source == True):
            commonssite.addClaim(wditem, source_claim)
        if (flag_add_collection == True):
            commonssite.addClaim(wditem, coll_claim)
        if (flag_add_finna == True):
            commonssite.addClaim(wditem, finna_claim)

    # don't try too many at once
    if (rowcount >= rowlimit):
        print("Limit reached")
        exit(1)
        break

