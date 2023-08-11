import pywikibot
import re
import urllib
import requests
import imagehash
from PIL import Image
import json
import sqlite3
import io
import os
import tempfile
from SPARQLWrapper import SPARQLWrapper, JSON

def add_claim_if_not_exists(site, page, property_id, value_id):
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    
    item = page.data_item() 
    data=item.get() # Fetch the item data
    claims = data['statements'] 

    # Check if the property already exists in the item's claims
    if property_id in claims:
        # Check if the value already exists for the property
        for claim in claims[property_id]:
            if claim.getTarget().getID() == value_id:
                print(f'Value {value_id} already exists for property {property_id} in {page.title()}.')
                return

    # Create a new claim
    new_claim = pywikibot.Claim(wikidata_site, property_id)
    target_item = pywikibot.ItemPage(wikidata_site, value_id)
    new_claim.setTarget(target_item)

    value_title = get_wikidata_title(wikidata_id)
    pywikibot.output(f'Adding value {value_id} ({value_title}) to property {property_id} in item {page.title()}.')
    question='Do you want to accept these changes?'

    choice = pywikibot.input_choice(
            question,
            [('Yes', 'y'), ('No', 'N')],
            default='N',
            automatic_quit=False
         )

    # Save
    if choice != 'y':
        return

    # Add the claim to the item
    site.addClaim(item, new_claim)
    pywikibot.output('OK')
    return True


def get_wikidata_item_by_property_value(property_id, value):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
        SELECT ?item WHERE {{
            ?item wdt:{property_id} "{value}".
        }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    # Extracting the Wikidata item IDs from the results
    item_ids = [result['item']['value'].split('/')[-1] for result in results['results']['bindings']]

    return item_ids



### SQLITE Database ###

def create_table():
    c.execute('''CREATE TABLE IF NOT EXISTS urls (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 url1 TEXT NOT NULL,
                 url2 TEXT NOT NULL,
                 hash_size INTEGER NOT NULL,
                 phash_diff INTEGER NOT NULL,
                 dhash_diff INTEGER NOT NULL)''')

    conn.commit()

def store_cached_diff(url1, url2, hash_size, phash_diff, dhash_diff):
    c.execute("INSERT INTO urls (url1, url2, hash_size, phash_diff, dhash_diff) VALUES (?, ?, ?, ?, ?)", (url1, url2, hash_size, phash_diff, dhash_diff))

    conn.commit()

def get_cached_diff(url1, url2, hash_size=8):
    c.execute("SELECT * FROM urls WHERE url1 = ? AND url2 = ? AND hash_size = ? LIMIT 1", (url1, url2, hash_size) )
    data = c.fetchall()
    if len(data)==1:
        return data[0]
    elif len(data)>0:
        print("Error: Multiple rows")
        exit(1)
    return False

### PERCEPTUAL HASHING ###

# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

def calculate_phash(im, hash_size=8):
    hash = imagehash.phash(im, hash_size)
    hash_int=int(str(hash),16)
    return hash_int

# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

def calculate_dhash(im, hash_size=8):
    hash = imagehash.dhash(im, hash_size)
    hash_int=int(str(hash),16)
    return hash_int

# Compares if the image is same using similarity hashing
# method is to convert images to 64bit integers and then
# calculate hamming distance. 

# url1 = Finna small thubmnail
# url2 = Commons thumbnail
# url3 = Finna large thumbnail

def is_same_image(url1, url2, url3, hash_size=8):

    cached_diff = get_cached_diff(url1, url2, hash_size)
    im1 = False
    im2 = False
    im3 = False

    if cached_diff: 
    #    print("cached")
        phash_diff=cached_diff['phash_diff']
        dhash_diff=cached_diff['dhash_diff']
    else:
        # Open the image1 with Pillow
        im1 = Image.open(urllib.request.urlopen(url1))
        phash1_int=calculate_phash(im1, hash_size)
        dhash1_int=calculate_dhash(im1, hash_size)

        # Open the image2 with Pillow
        im2 = Image.open(urllib.request.urlopen(url2))
        phash2_int=calculate_phash(im2, hash_size)
        dhash2_int=calculate_dhash(im2, hash_size)

        # Hamming distance difference
        phash_diff = bin(phash1_int ^ phash2_int).count('1')
        dhash_diff = bin(dhash1_int ^ dhash2_int).count('1') 
        store_cached_diff(url1,url2, hash_size, phash_diff, dhash_diff)

    # If hashes are near, then confirm with longer hash and higher resolution images

    if phash_diff < 11 and dhash_diff < 11:
        hash_size=24
        cached_diff = get_cached_diff(url3, url2, hash_size)
        if cached_diff:
            #    print("cached")
            phash_diff=cached_diff['phash_diff']
            dhash_diff=cached_diff['dhash_diff']
        else:

            if not im2:
                # Open the image2 with Pillow
                im2 = Image.open(urllib.request.urlopen(url2))
                phash2_int=calculate_phash(im2, hash_size)
                dhash2_int=calculate_dhash(im2, hash_size)

            im3 = Image.open(urllib.request.urlopen(url3))
            phash1_int=calculate_phash(im3, hash_size)
            dhash1_int=calculate_dhash(im3, hash_size)

            phash_diff = bin(phash1_int ^ phash2_int).count('1')
            dhash_diff = bin(dhash1_int ^ dhash2_int).count('1') 
            store_cached_diff(url3,url2, hash_size, phash_diff, dhash_diff)


    ## print hamming distance
    # print("Phash diff: " + str(phash_diff))
    # print("Dhash diff: " + str(dhash_diff))

    # max distance for same is that least one is 0 and second is max 3

    if phash_diff == 0 and dhash_diff < 10:
        return True
    elif phash_diff < 10 and dhash_diff == 0:
        return True
    elif phash_diff < 9 and dhash_diff < 9:
        return True
    else:
        return False

### FINNA Requests ###

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
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'openUrl')
    url+= finna_api_parameter('field[]', 'nonPresenterAuthors')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'subjects')
    url+= finna_api_parameter('field[]', 'subjectsExtendet')
    url+= finna_api_parameter('field[]', 'subjectPlaces')
    url+= finna_api_parameter('field[]', 'subjectActors')
    url+= finna_api_parameter('field[]', 'subjectDetails')
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
    url+= finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url+= finna_api_parameter('field[]', 'formats')
    url+= finna_api_parameter('field[]', 'physicalDescriptions')
    url+= finna_api_parameter('field[]', 'measurements')
    url+= finna_api_parameter('limit','100')
    url+= finna_api_parameter('page',str(page))

    try:
        response = requests.get(url)
        return response.json()
    except e:
        print(e)
        print("Finna API query failed: " + url)
        exit(1)

# Find Finna ids from page.externallinks()

def get_finna_ids(page):
    finna_ids=[]

    for url in page.extlinks():
        if "finna.fi" in url:
            id = None

            url = url.split('#')[0]
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

        if "kuvakokoelmat" in url:
            # Parse id from url
            patterns = [
                           r"kuvakokoelmat\.fi/pictures/view/HK7155_([^?]+)",
                           r"kuvakokoelmat\.fi/pictures/small/HK71/HK7155_([^?]+)\.jpg",
                       ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    id = 'musketti.M012:HK7155:' + str(match.group(1)).replace('_', '-')
                    if id not in finna_ids:
                        finna_ids.append(id)
                    break

    return finna_ids

# Find correct Finna id for Commons image from multiple Finna ids
def get_correct_finna_record(page, finna_ids):
    # Skip if there is no known ids
    if not finna_ids:
        print("SKIP: No finna ids found " + str(page))
        return False

    for finna_id in finna_ids:
        finna_record = get_finna_record(finna_id)

        if finna_record['status']!='OK':
            print("SKIP: Finna result not OK: " + finna_id)
            return False

        if finna_record['resultCount']!=1:
            print("FAILED: Multiple results: " + finna_id)
            exit(1)

        imagesExtended=finna_record['records'][0]['imagesExtended']
        for imageExtended in imagesExtended:
            finna_thumbnail_url="https://finna.fi" + imageExtended['urls']['small']
            finna_thumbnail_url2="https://finna.fi" + imageExtended['urls']['large']
            commons_thumbnail_url=page.get_file_url(url_width=1024)

            if is_same_image(finna_thumbnail_url, commons_thumbnail_url, finna_thumbnail_url2):
                return finna_record['records'][0]

    return False    

### Finto ###

def finto_search(keyword,vocab='finaf'):
    keyword=keyword.replace(' ', '*') +'*'
    url='http://api.finto.fi/rest/v1/search?vocab='+vocab+'&query=' + urllib.parse.quote_plus(str(keyword))
    try:
        response = requests.get(url)
        data=response.json()
    except e:
        print(e)
        print("Finna API query failed: " + url)
        exit(1)
    for term in data['results']:
#        print(term)
        get_finto_term_information(vocab, term['uri'])

# Search detailed information for the term
def get_finto_term_information(vocab, term_url):
    url='http://api.finto.fi/rest/v1/' + vocab + '/data?format=application/json&uri=' + urllib.parse.quote_plus(term_url);
    try:
        response = requests.get(url)
        data=response.json()
    except e:
        print(e)
        print("Finna API query failed: " + url)
        exit(1)


    name_keys=['http://rdaregistry.info/Elements/a/P50103','http://rdaregistry.info/Elements/a/P50115','http://rdaregistry.info/Elements/a/P50411','altLabel','prefLabel']
    names=set()
    birthdate=''
    deathdate=''

    for graph_values in data['graph']:
        if term_url==graph_values['uri']:
            for value_key in graph_values:
                if value_key in name_keys:
                    if 'value' in graph_values[value_key]:
                        names.add(graph_values[value_key]['value'])
                    else:
                        for graph_value_name in graph_values[value_key]:
                            names.add(graph_value_name['value'])

                elif 'http://rdaregistry.info/Elements/a/P50120' == value_key:
                    deathdate=graph_values[value_key]
                elif 'http://rdaregistry.info/Elements/a/P50121' == value_key:
                    birthdate=graph_values[value_key]

    kanto_id=term_url.replace('http://urn.fi/URN:NBN:fi:au:finaf:', '')
    wikidata_ids=get_wikidata_item_by_property_value('P8980', kanto_id)
    if len(wikidata_ids)==1:
        wikidata_id=wikidata_ids[0]
    elif len(wikidata_ids)>1:
        print("Getting wikidata id failed")
        print(wikidata_ids)
        exit(1)
    else:
        wikidata_id='not-found'

    ret=[]
    ret.append('* Kanto-tietokanta')
    ret.append(wikidata_id)
    ret.append("; ".join(names))
    years=format_years(birthdate, deathdate)
    if years:
        ret.append(years)
    ret.append(str(kanto_id))
        
    out='\t'.join(ret)

    print(out)            



### INFO FOR MANUAL CONFIRMATION ###

def get_lead_image(page):
    # Fetching page_props
    page_props = page.properties()
    # Returning the lead image if it exists
    return page_props.get('page_image_free') if 'page_image_free' in page_props else None

def get_wikidata_item_qid(page):

    # If we are alread checking wikidata item just return page_title()
    if page.site.code == 'wikidata':
        if page.namespace()==0:
            return page.title()
        else:
            return None

    # Get the linked Wikidata item
    wikidata_item = page.data_item()

    return wikidata_item.getID() if wikidata_item.exists() else None

def get_wikidata_properties(wikidata_id):
    wdsite = pywikibot.Site('wikidata', 'wikidata')
    repo = wdsite.data_repository()

    item = pywikibot.ItemPage(repo, wikidata_id)
    item.get()

    def get_property(prop_id):
        prop = item.claims.get(prop_id)
        return [claim.getTarget() for claim in prop] if prop else None

    # Retrieve instance of (P31) property
    instance_of = item.claims.get('P31')
    instance_of_values = [claim.getTarget().labels['en'] for claim in instance_of] if instance_of else None

    # Retrieve date of birth (P569) property and convert to year
    birthdate = item.claims.get('P569')
    birthyear = int(birthdate[0].getTarget().year) if birthdate else None

    # Retrieve date of death (P570) property and convert to year
    deathdate = item.claims.get('P570')
    deathyear = int(deathdate[0].getTarget().year) if deathdate else None

    isni = get_property('P213')
    kanto = get_property('P8980')

    return instance_of_values, birthyear, deathyear, isni, kanto

def format_years(birthyear, deathyear):
    years=''
    if birthyear:
        years = 's. ' +str(birthyear)
    if deathyear:
        years += ' - k. ' + str(deathyear)

    if years:
       years = '(' + years + ')'

    return years


def get_wikidata_title(wikidata_id):
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    item = pywikibot.ItemPage(wikidata_site, wikidata_id)
    # Fetch details
    item.get()

    label=''
    description=''

    langs=['fi', 'sv', 'en', 'de', 'es', 'fr']
    for lang in langs:
        if lang in item.labels:
            return item.labels[lang]
    return "Unknown"

def get_wikidata_summary(wikidata_id):
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    item = pywikibot.ItemPage(wikidata_site, wikidata_id)
    # Fetch details
    item.get()

    label=''
    description=''

    langs=['fi', 'sv', 'en', 'de', 'es', 'fr']
    for lang in langs:
        if lang in item.labels:
            label=item.labels[lang]
            break

    for lang in langs:
        if lang in item.descriptions:
            description=item.descriptions[lang]
            break

    p31, birthyear, deathyear, isni, kanto =  get_wikidata_properties(wikidata_id) 

    ret=[]
    ret.append('wikidata')
    ret.append('d')
    ret.append(wikidata_id)
    ret.append(label)
    ret.append(description)

    years=format_years(birthyear, deathyear)
    if years:
       ret.append(years)

    return '\t'.join(ret)

def get_wikipedia_summary(page, wikidata_id):
    url = f'https://{page.site.lang}.wikipedia.org/api/rest_v1/page/summary/{page.title()}'
    response = requests.get(url)
    ret=[]
    ret.append('wikipedia')
    ret.append(page.site.lang)
    ret.append(wikidata_id)
   
    if response.status_code == 200:
        extract=response.json().get('extract')
        ret.append(extract)

    return '\t'.join(ret)

def create_article_summary(page, wikidata_id):
    if page.title() == wikidata_id:
        return get_wikidata_summary(wikidata_id)
    elif page.site.family == 'wikipedia':
        return get_wikipedia_summary(page, wikidata_id)
    


conn = sqlite3.connect('musketti.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
create_table()

site = pywikibot.Site('commons', 'commons')  # The site we're working on
pywikibot.config.socket_timeout = 120
site.login()

seek='File:Gunnar-Landtman-1900.jpg'
#seek=False
# Get all linked pages from the page
#category = pywikibot.Category(site, 'Category:Files from the Antellin kokoelma')

#for linked_page in category.articles(namespaces=6):



page = pywikibot.Page(site, 'user:FinnaUploadBot/filelist')  # The page you're interested in
for linked_page in page.linkedPages():
    title=linked_page.title()

    if seek and title != seek:
        continue
    seek=False

    file_info = linked_page.latest_file_info
       
    if "cropped" in title:
        continue

    finna_ids=get_finna_ids(linked_page)
    finna_record=get_correct_finna_record(linked_page, finna_ids)
    if not finna_record:
        continue

    print('\n----')
    print("Found " + finna_record['id'])
    print(title)
    subjectActors=finna_record['subjectActors']

    usage = linked_page.globalusage()
    wikidata_ids={}

    for link in usage:
#        print(link.site, link.title())
         lead_image = get_lead_image(link)

         if lead_image:
#              print(f'Lead image for {link.title()}: {lead_image}')

              # Convert lead_image to Page() to get normalized name
              tmp_image = pywikibot.Page(site, 'File:' + lead_image)

              # Test if the lead_image is same as current page 
              if tmp_image.title() == linked_page.title():
                  # Get target wikidata_id
                  wikidata_id = get_wikidata_item_qid(link)
                  if wikidata_id:
                      if not wikidata_id in wikidata_ids:
                          wikidata_ids[wikidata_id] = set()
                      
                      wikidata_ids[wikidata_id].add(create_article_summary(link, wikidata_id))

    print('')                              
    print("Finna title: " + str(finna_record['title']))
    print("Finna summary: " + str(finna_record['summary']))
    print('')
    print("Finna subjectActors: " + str(subjectActors))
    for subjectActor in subjectActors:
        finto_terms=finto_search(subjectActor,'finaf')


    print('')
    print("Commons globalusage: ")# + str(wikidata_ids))
    for wikidata_id in wikidata_ids:
        for article_title in wikidata_ids[wikidata_id]:
            if article_title:
                print("* " + article_title)
            else:
                print("* article title missing " + wikidata_id)

    print('')
    for wikidata_id in wikidata_ids:
        t=add_claim_if_not_exists(site, linked_page, 'P180', wikidata_id)

conn.close()

