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

def getlinkourceid(oldsource):
    strlen = len("id=")
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return ""
    indexend = oldsource.find("&", indexid)
    if (indexend < 0):
        indexend = oldsource.find(" ", indexid)
        if (indexend < 0):
            indexend = len(oldsource)-1
        
    return oldsource[indexid+strlen:indexend]

def getrecordid(oldsource):
    strlen = len("/Record/")
    indexid = oldsource.find("/Record/")
    if (indexid < 0):
        return ""
    indexend = oldsource.find(" ", indexid)
    if (indexend < 0):
        indexend = len(oldsource)-1
        
    return oldsource[indexid+strlen:indexend]
    
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

# parse claims or statements from commons SDC
def getcollectiontargetqcode(statements):
    if "P195" not in statements:
        return ""
    claimlist = statements["P195"]    
    for claim in claimlist:
        # target is expected to be like: [[wikidata:Q118976025]]
        target = claim.getTarget()

        # TODO: finish comparison to wikidata:
        # -might belong to multiple collections -> multiple entries
        # -might have something that isn't in finna list
        # -might be missing something that is in finna list -> should add to commons SDC

        #dataitem = pywikibot.ItemPage(wikidata_site, "Q118976025")
        # check item, might belong to multiple collections -> compare to list from finna

# fetch metapage from finna and try to parse current ID from the page
# since we might have obsolete ID.
# new ID is needed API query.
def parsemetaidfromfinnapage(finnaurl):

    finnapage = ""

    try:
        #finnapage = urllib2.urlopen(finnaurl)
        #finnapage = urllib3.request("GET", finnaurl)
        #finnapage = urllib.request.urlopen(finnaurl).read()
        
        request = urllib.request.Request(finnaurl)
        print("request done: " + finnaurl)

        response = urllib.request.urlopen(request)
        if (response.readable() == False):
            print("response not readable")

        #print("decoding ")
        #response.encoding = "utf-8-sig"
        
        # no decode_content()
        #finnapage = response.decode_content()
 
        htmlbytes = response.read()
        #if ((htmlbytes[0] == 0xFE or htmlbytes[0] == 0xFF) and 
        #(htmlbytes[1] == 0xFE or htmlbytes[1] == 0xFF)):
        #print("html read, decoding ")
        finnapage = htmlbytes.decode("utf8")

        # no text member
        #finnapage = response.text        
        
        print("page: " + finnapage)
        
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
cat = pywikibot.Category(commonssite, "Category:Kuvasiskot")
pages = commonssite.categorymembers(cat)

#repository = site.data_repository()

rowcount = 1
rowlimit = 10

for page in pages:
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

    finnaid = ""
    finnasource = ""
    for template in wikicode.filter_templates():
        # at least three different templates have been used..
        if template.name.matches("Information") or template.name.matches("Photograph") or template.name.matches("Artwork"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                finnasource = srcvalue
                finnaid = getlinkourceid(srcvalue)
                if (finnaid == ""):
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        print("no id and no record found")
                    break

            if template.has("source"):
                par = template.get("source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                finnasource = srcvalue
                finnaid = getlinkourceid(srcvalue)
                if (finnaid == ""):
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        print("no id and no record found")
                    break
 
    # kuvasiskot has "musketti" as part of identier, alternatively "museovirasto" may be used in some cases
    if (finnaid.find("musketti") < 0 and finnaid.find("museovirasto") < 0):
        print("Skipping. " + page.title() + " - not appropriate id: " + finnaid)
        continue
        
    if (len(finnaid) >= 50):
        print("WARN: finna id in " + page.title() + " is unusually long? bug or garbage in url? ")
    if (len(finnaid) <= 5):
        print("WARN: finna id in " + page.title() + " is unusually short? bug or garbage in url? ")
    if (finnaid.find("?") > 0 or finnaid.find("&") > 0):
        print("WARN: finna id in " + page.title() + " has unexpected characters, bug or garbage in url? ")
        
    if (finnaid.endswith("\n")):
        print("WARN: finna id in " + page.title() + " ends with newline ")
        finnaid = finnaid[:len(finnaid)-1]

    print("finna ID found: " + finnaid)
    sourceurl = "https://www.finna.fi/Record/" + finnaid

    if (finnaid.find("musketti") >= 0):
        # check if the source has something other than url in it as well..
        # if it has some human-readable things try to parse real url
        finnaurl = geturlfromsource(finnasource)
        if (finnaurl == ""):
            print("WARN: could not parse finna url from source in " + page.title() + " , skipping, source: " + finnasource)
            break
    
        # obsolete id -> try to fetch page and locate current ID
        finnaid = parsemetaidfromfinnapage(sourceurl)
        if (finnaid == ""):
            print("WARN: could not parse current finna id in " + page.title() + " , skipping, url: " + sourceurl)
            break
            
        print("new finna ID found: " + finnaid)
        sourceurl = "https://www.finna.fi/Record/" + finnaid

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

    # check SDC and try match with finna list collectionqcodes
    #getcollectiontargetqcode(claims)

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

    claim_collp = 'P195'  # property ID for "collection"
    if claim_collp not in claims:
        # P195 "collection"
        coll_claim = pywikibot.Claim(wikidata_site, claim_collp)

        # Q118976025 "Studio Kuvasiskojen kokoelma"
        qualifier_targetcoll = pywikibot.ItemPage(wikidata_site, 'Q118976025')  # Studio Kuvasiskojen kokoelma
        coll_claim.setTarget(qualifier_targetcoll)

        flag_add_collection = True

    claim_finnaidp = 'P9478'  # property ID for "finna ID"
    if claim_finnaidp not in claims:
        # P9478 "Finna ID"
        finna_claim = pywikibot.Claim(wikidata_site, claim_finnaidp)
        finnaunquoted = urllib.parse.unquote(finnaid)
        finna_claim.setTarget(finnaunquoted)

        flag_add_finna = True


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

