## Script uploads the Kuvasiskot photos to Wikimedia Commons. 
# - script will ask confirmation before uploads
# - script tries to check if there is existing photos using phash/dhash
#
## Install
# python3 -m venv ./venv
# source venv/bin/activate
# pip install pywikibot imagehash requests urllib Pillow
#
## Running the script
# python upload_kuvasiskot.py


import mwparserfromhell
import requests
import urllib
import json
import imagehash
import time
import pywikibot
import tempfile
import os
from PIL import Image

# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

def calculate_dhash(im):
    hash = imagehash.dhash(im)
    hash_int=int(str(hash),16)
    return hash_int

# Perceptual hashing 
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

def calculate_phash(im):
    hash = imagehash.phash(im)
    hash_int=int(str(hash),16)
    return hash_int

def check_imagehash(url):
    # Open the image1 with Pillow
    im = Image.open(urllib.request.urlopen(url))
    phash=calculate_phash(im)
    dhash=calculate_dhash(im)

    # Format the URL with the provided dhash and phash values
    url = f"https://imagehash.toolforge.org/search?dhash={dhash}&phash={phash}"

    # Make a GET request to the URL
    response = requests.get(url)

    # Check the status of the response
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Check if the response contains any rows
        if data and isinstance(data, list) and len(data) > 0:
            return True

    # If the response status is not 200 or the response doesn't contain any rows,
    # return False
    return False

def create_photographer_template(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the template
    template = mwparserfromhell.nodes.Template(name='Photograph')

    # Add the parameters to the template
    template.add('photographer', r['creator_template'])
    template.add('title', '\n'.join(r['template_titles']))
    template.add('description', '\n'.join(r['template_descriptions']))
    template.add('depicted people', r['subjectActors'])
    template.add('depicted place', r['subjectPlaces'])
    template.add('date', r['date'])
    template.add('medium', '')
    template.add('dimensions', "\n".join(r['measurements']))
    template.add('institution', r['institution_template'])
    template.add('department', "; ".join(r['collections']))
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', r['identifierString'])
    template.add('source', r['source'])
    template.add('permission',  "\n".join([r['copyright'], r['copyright_description']]))
    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')

    # Add the template to the WikiCode object
    wikicode.append(template)
    flatten_wikitext=str(wikicode) 

    # Add newlines before parameter name
    params = ['photographer', 'title', 'description', 'depicted people', 'depicted place', 'date', 'medium', 'dimensions', 
              'institution', 'department', 'references', 'object history', 'exhibition history', 'credit line', 'inscriptions', 
              'notes', 'accession number', 'source', 'permission', 'other_versions', 'wikidata', 'camera coord']

    for param in params:
        flatten_wikitext=flatten_wikitext.replace('|' + param +'=', '\n|' +param +' = ')

    # return the wikitext
    return flatten_wikitext

def create_categories(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    if r['creator_template'] == '{{Creator:Kuvasiskot}}':
        categories.add('Kuvasiskot')
    else:
        print('Unknown creator template')
        exit(1)   

    subject_categories = {
        'muotokuvat':'Portrait photographs',
        'henkilökuvat':'Portrait photographs',
        'professorit':'Professors from Finland',
        'miesten puvut':'Lounge suits'
    }

    for subject_category in subject_categories.keys():
        if subject_category in str(r['subjects']):
            categories.add(subject_categories[subject_category])
    

    if 'year' in r:
        if 'Category:Portrait photographs' in categories:
            categories.add('People of Finland in ' + r['year'])
        else:
            categories.add(r['year'] + ' in Finland')

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # Create the Wikilink
        wikilink = mwparserfromhell.nodes.Wikilink(title='Category:' + category)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    
    flatten_wikicode=str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode


# urlencode Finna parameters
def finna_api_parameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)

# Finnan Swagger dokumentaation recordin example outputista mahdolliset kentät 
# https://api.finna.fi/swagger-ui/?url=%2Fapi%2Fv1%3Fswagger#/List/get_list
def get_finna_by_filter(page):
    data = None
    url="https://api.finna.fi/v1/search?" 
    url+= finna_api_parameter('filter[]', '~format_ext_str_mv:"0/Image/"') 
    url+= finna_api_parameter('filter[]', 'free_online_boolean:"1"') 
    url+= finna_api_parameter('filter[]', '~hierarchy_parent_title:"Studio Kuvasiskojen kokoelma"')  
    url+= finna_api_parameter('filter[]', '~usage_rights_str_mv:"usage_B"') 
    url+= finna_api_parameter('lookfor','"professorit"+"miesten+puvut"')      # Searchkey
    url+= finna_api_parameter('type','Subjects')                              # Search only from subjects
#    url+= finna_api_parameter('type','AllFields')
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


    with urllib.request.urlopen(url) as file:
        try:
            data = json.loads(file.read().decode())
        except Exception as e:
            print(e)
            data = None
    return data

def get_author(nonPresenterAuthors):
    for nonPresenterAuthor in nonPresenterAuthors:
        if nonPresenterAuthor['name'] == "Kuvasiskot":
            return "{{Creator:Kuvasiskot}}"
    print("Unknown author")
    print(nonPresenterAuthors)
    exit(1)

# Filter out duplicate placenames
def get_subject_place(subjectPlaces):
    parts = [part.strip() for part in subjectPlaces.split("; ")]

    # Sort the parts by length in descending order
    parts.sort(key=len, reverse=True)
    # Iterate over the parts and check for each part if it's included in any of the parts that come after it
    final_parts = []
    for i in range(len(parts)):
        if not parts[i] in "; ".join(final_parts):
            final_parts.append(parts[i])    
    return "; ".join(final_parts)

# Get institution template
def get_institution(institutions):
    for institution in institutions:
        if institution['value'] == "Museovirasto":
            ret="{{institution:Museovirasto}}"
        else:
            print("Unknown institution: " + str(institutions))
            exit(1)
    return ret

# get edit summaries of last 5000 edits for checking which files were already uploaded
def get_upload_summary():
    site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
    user = pywikibot.User(site, 'FinnaUploadBot')       # The user whose edits we want to check

    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions

    uploadsummary=''
    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"

    return uploadsummary

def upload_file_to_commons(source_file_url, file_name, wikitext, comment):
    commons_file_name = "File:" + file_name
    file_page = pywikibot.FilePage(site, commons_file_name) 
    file_page.text = wikitext

    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists.")
        exit()

    # Load file from url
    response = requests.get(source_file_url,  timeout=30)

    # Create a temporary file and save the downloaded file into this temp file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name

    file_page.upload(temp_file_path, comment=comment,asynchronous=True)

    # Delete the temporary file
    os.unlink(temp_file_path)

def get_comment_text(r):
    author="unknown"
    if r['creator_template'] == '{{Creator:Kuvasiskot}}':
        author='Kuvasiskot'
    else:
        print("unknown author")
        exit(1)

    ret = "Uploading \'" + r['shortTitle'] +"\'"
    ret = ret + " by \'" + author +"\'"

    if "CC BY 4.0" in r['copyright']:
        copyrighttemplate="CC-BY-4.0"
    else:
        print("Copyright error")
        print(r['copyright'])
        exit(1)

    ret = ret + " with licence " + copyrighttemplate
    ret = ret + " from " + r['source']
    return ret



# Login to commons
pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()

print("Loading 5000 most recent edit summaries for skipping already uploaded photos")
uploadsummary=get_upload_summary()
images=[]
for page in range(1,101):
    # Prevent looping too fast for Finna server
    time.sleep(0.2)
    data=get_finna_by_filter(page)
    if not data or not 'records' in data:
        break

    for record in data['records']:
        # Not photo
        if not 'imagesExtended' in record:
            continue

        if record['id'] in uploadsummary:
            print("Skipping: " + record['id'] + " already uploaded")
            continue

        r={}
        r['id']=record['id']
        r['title']=record['title']
        r['shortTitle']=record['shortTitle']
        r['copyright']=record['imageRights']['copyright']
        r['thumbnail']="https://finna.fi" + record['imagesExtended'][0]['urls']['small']
        r['image_url']= record['imagesExtended'][0]['highResolution']['original'][0]['url']
        r['image_format']= record['imagesExtended'][0]['highResolution']['original'][0]['format']
        r['collections']=record['collections']
        r['institutions']=record['institutions']
        r['institution_template']=get_institution(record['institutions'])
        r['identifierString']=record['identifierString']
        r['subjectPlaces']=get_subject_place("; ".join(record['subjectPlaces']))
        r['subjectActors']="; ".join(record['subjectActors'])
        r['date']=record['events']['valmistus'][0]['date']
        r['source']='https://finna.fi/Record/' + r['id']
        r['subjects']=record['subjects']
        r['measurements']=record['measurements']

        if 'year' in record:
            r['year']=record['year']

        # Check copyright
        if r['copyright'] == "CC BY 4.0":
            r['copyright_template']="{{CC-BY-4.0}}\n{{FinnaReview}}"
            r['copyright_description']=record['imagesExtended'][0]['rights']['description'][0]
        else:
            print("Unknown copyright: " + r['copyright'])
            exit(1)

        # Check format
        if r['image_format'] == 'tif':
           # Filename format is "tohtori,_varatuomari_Reino_Erma_(647F28).tif"
#           r['file_name'] = r['shortTitle'].replace(" ", "_") + '_(' + r['id'][-6:] +  ').tif'
           r['file_name'] = r['shortTitle'].replace(" ", "_") + '_(' + r['identifierString'] +  ').tif'
        else:
            print("Unknown format: " + r['image_format'])
            exit(1)

        # Skip image already exits in Wikimedia Commons 
        if check_imagehash(r['thumbnail']):
            print("Skipping (already exists based on imagehash) : " + r['id'])
            continue

        r['creator_template']=get_author(record['nonPresenterAuthors'])

        # titles and descriptions wrapped in language template
        r['template_titles']=['{{fi|' + r['title'] + '}}']
        r['template_descriptions']={}
        
#        print(json.dumps(r, indent=3))
#        print(record)

        wikitext_parts=[]
        wikitext_parts.append("== {{int:filedesc}} ==")
        wikitext_parts.append(create_photographer_template(r) + '\n')
        wikitext_parts.append("== {{int:license-header}} ==")
        wikitext_parts.append(r['copyright_template']) 
        wikitext_parts.append(create_categories(r))

        wikitext = "\n".join(wikitext_parts)
        comment=get_comment_text(r)
        pywikibot.info('')
        pywikibot.info(wikitext)
        pywikibot.info('')
        pywikibot.info(comment)
        print(r['image_url'])
        question='Do you want to upload this file?'
        choice = pywikibot.input_choice(
            question,
            [('Yes', 'y'), ('No', 'N')],
            default='N',
            automatic_quit=False
        )

        # Save
        if choice == 'y':
            upload_file_to_commons(r['image_url'], r['file_name'], wikitext, comment)

