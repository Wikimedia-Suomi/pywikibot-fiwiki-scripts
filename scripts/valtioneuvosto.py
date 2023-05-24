import datetime
import pywikibot
import hashlib
import imagehash
import requests
import json
import time
import urllib
import os
from PIL import Image
from io import BytesIO
from pywikibot import config

# Get subalbums

def getFolderChilds(headers, folderName=""):
    ret={}
    # Define the API URL
    api_url = "https://kuvapankki.valtioneuvosto.fi/api/GetFolderChilds"

    post_body=json.dumps([folderName])

    # Send a GET request to the API URL
    response = session.post(api_url, post_body,headers=headers)


    # Check the response
    if response.status_code != 200:
        print("Failed to get data from the API.")
        print(response)
        print(response.request.headers)
        exit(1)

    # Parse the response as JSON
    data = response.json()
    
    for row in data:
        id=row[0]
        name=row[2]
        ret[id]=name

    return ret

def getUploadedDescriptions():
    site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
    user = pywikibot.User(site, 'Zache')       # The user whose edits we want to check

    contribs = user.contributions(total=2000)  # Get the user's last 1000 contributions

    uploads=''
    for contrib in contribs:
        uploads+=str(contrib) +"\n"

    return uploads


# Get files in albums

def searchFiles(headers, folderName=""):
    ret=[]
    # Define the API URL
    api_url = "https://kuvapankki.valtioneuvosto.fi/api/SearchFiles"


    # Params are read from web browser request from page https://kuvapankki.valtioneuvosto.fi/f/Wzpf
    # It is unknown what params actually means except the folder name

#    post_params = [[[9,0,[ folderName ],0,0]],0,[15,2,20,21,6,-14,-15,-16,-23,-24,-26],None]
    post_params =  [[[-15,1,["CC-"]     ,0,0]],0,[15,2,20,21,6,-14,-15,-16,-23,-24,-26],None]
#    post_params =  [[[0,6,  ["0E4A8666"],0,0]],0,[15,2,20,21,6,-14,-15,-16,-23,-24,-26],None]

    post_body=json.dumps(post_params)

    # Send a GET request to the API URL
    response = session.post(api_url, post_body,headers=headers)

    # Check the response
    if response.status_code != 200:
        print("Failed to get data from the API.")
        print(response)
        print(response.request.headers)
        exit(1)

    # Parse the response as JSON
    data = response.json()
    
    for row in data:
        # Skip if not creative commons
        if not 'creativecommons' in json.dumps(row):
            if not 'CC-' in json.dumps(row):
                if not 'cc-' in json.dumps(row):
                    continue          
        file=parseImageRow(row)
        ret.append(file)
    return ret

# imagedata parser

def parseImageRow(row):
    print(row)
    r={}
    r['id']=row[0]
    if row[1]!=1:
        exit("1")
    r['filename']=row[2]
    r['assetcreationtime']=row[3]
    r['assetmodificationtime']=row[4]

    if row[5]!=0:
        exit("5")
    if row[6]!=1:
        exit("6")
    if row[7] not in [1,2,3,4]:
        exit("7")

    r['download_id']=row[8]
    r['unknown_num2']=row[9]

    if row[10]!=1:
        exit("10")

    r['unknown_list1']=row[11]
    r['id_str']=row[12]
    r['mimetype']=row[13]
    r['unknown_list2']=row[14]

    if row[15]!=0:
        exit("15")
    if row[16]!=0:
        exit("16")
    if row[17]!=0:
        exit("17")
    if row[18]!="":
        exit("18")
    if row[19] not in [1,2,3,4]:
        exit("19")

    subrow=row[20]

    r['filename2']=subrow[0]
    r['sub_id']=subrow[1]

    if subrow[2]!="":
        exit("s2")
    if subrow[3]!="":
        exit("s3")

    r['asiasanasto']=subrow[4]
    r['author']=subrow[5]
    r['copyright']=subrow[6]
    r['pose']=subrow[7]        
    r['filemodificationtime']=subrow[8]
    r['keywords']=subrow[9]

    if r['keywords']=='' and len(str(subrow[10]))>4:
        r['keywords']=subrow[10]

    if r['keywords']=='':
        print(subrow)
        if len(str(subrow[10]))>2:
            time.sleep(5)

    if row[21]!=False:
        exit("21")

    return r


def getCommonsThumbnailUrl(filename, thumbnail_width=250):
    site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
    page = pywikibot.FilePage(site, 'File:' + str(filename))  # Replace with your file name

    # Get the file info
    file_info = page.latest_file_info

    # Get the file URL
    file_url = page.get_file_url()

    # if image width is much wider than thumbnail width then use thumnail width
 
    if file_info.width > thumbnail_width*2:
        # Generate the thumbnail URL
        file_url = file_url.replace('/commons/', f'/commons/thumb/') + f'/{thumbnail_width}px-' + file_url.split('/')[-1]

    return file_url    
   
def searchPhotographer(photo, firstName, lastName):
    haystack=json.dumps(photo)
    if firstName in haystack \
       and lastName in haystack:
       return True
    else:
       return False


def getCommonsFilenameBySha1(sha1_hash):
    url="https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aiprop=sha1&format=json&aisha1=" + sha1_hash
    response = session.get(url)
    if response.status_code == 200:
        data = response.json()
        if data and "query" in data and "allimages" in data["query"] and len(data["query"]["allimages"]):
            return data["query"]["allimages"][0]["name"]
           

def calculatePhash(im):
    hash = imagehash.phash(im)
    hash_int=int(str(hash),16)
    return hash_int

def calculateDhash(im):
    hash = imagehash.dhash(im)
    hash_int=int(str(hash),16)
    return hash_int

def uploadFileToCommons(response, filename, wikitext, comment):
    # Save the file locally
    with open('temp.jpg', 'wb') as f:
        f.write(response.content)

    file_obj = BytesIO(response.content)
    commonsfilename = "File:" + filename

    # Prepare for upload
    site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons

    filepage = pywikibot.FilePage(site, filename) 
    filepage.text = wikitext

    choice = 'y'
#    question='Do you want to accept these changes?'
#    choice = pywikibot.input_choice(
#            question,
#            [('Yes', 'y'), ('No', 'N')],
#            default='N',
#            automatic_quit=False
#         )

    # Save
    if choice == 'y':
       if site.userinfo['messages']:
           print("Warning: You have received a talk page message. Exiting.")
           exit()


    filepage.upload( source='temp.jpg', comment=comment, ignore_warnings=True,asynchronous=True)
    time.sleep(1)
    os.remove('temp.jpg')


def getValtioneuvostoImagefile(headers, id, wikitext, uploadfilename,comment):

    # URL of the JPEG file
    url="https://kuvapankki.valtioneuvosto.fi/download?coid=1&dl=0&fv=" + str(id)
    print(url)

    # Fetch the file as binary data
    response = session.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Compute the SHA1 hash of the file
        sha1_hash = hashlib.sha1(response.content).hexdigest()

        # Print the SHA1 hash
        print(f"SHA1 hash: {sha1_hash}")
        
        # Print filename if exists
        commons_filename=getCommonsFilenameBySha1(sha1_hash)
        if not commons_filename:
            if uploadfilename == "m-7521_(29714).jpg":
                uploadfilename = "Aino-Kaisa_Pekonen_(29714).jpg"
            elif not "linden-aki" in uploadfilename:
                exit(1)

            uploadfilename=uploadfilename.replace("linden-aki", "Aki_Linden")
            uploadFileToCommons(response, uploadfilename, wikitext, comment)

        elif commons_filename:
            print(commons_filename)
            commons_url=getCommonsThumbnailUrl(commons_filename)
            print(commons_url)

            # Open the image with Pillow
            commons_im = Image.open(urllib.request.urlopen(commons_url))

            # Calculate hash
            commons_phash_int=calculatePhash(commons_im)
            commons_dhash_int=calculateDhash(commons_im)


            # Create a BytesIO object from the response content
            image_data = BytesIO(response.content)

            # Open the image with Pillow
            valtioneuvosto_im = Image.open(image_data)

            # Calculate phash
            valtioneuvosto_phash_int=calculatePhash(valtioneuvosto_im)
            valtioneuvosto_dhash_int=calculateDhash(valtioneuvosto_im)

            print("Phash diff: " + str(bin(valtioneuvosto_phash_int ^ commons_phash_int).count('1')))
            print("Dhash diff: " + str(bin(valtioneuvosto_dhash_int ^ commons_dhash_int).count('1')))


#            exit(1)
        

    else:
        print(f"Error: {response.status_code} - {response.text}")

#    exit(1)
#    im = Image.open(urllib.request.urlopen(image_url))


def createFilename2(photograph):
    site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
#    filename = photograph['filename'].strip().replace(photograph['keywords'].replace(" ", "-"), photograph['keywords']).replace(" ", "_") + ".jpg"    
    filename = photograph['filename'].strip().replace(photograph['keywords'].replace(" ", "-"), photograph['keywords']).replace(" ", "_") + "_(" + str(photograph['download_id']) + ").jpg"

    filepage = pywikibot.FilePage(site, filename) 
    if filepage.exists():
        print("ERROR: " + filename)
        #exit(1)

    return filename
     


def createFilename(photograph):

    site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
    filename = flipName(photograph['albumName']) + " (" + photograph['filename'].strip() +").jpg"    

    filepage = pywikibot.FilePage(site, filename) 
    if filepage.exists():
        filename = flipName(photograph['albumName']) + " (" + str(photograph['download_id']) + ").jpg"    
        

    return filename

def createCommentLine(photograph):
    url="https://kuvapankki.valtioneuvosto.fi/download?coid=1&dl=0&fv=" + str(photograph['download_id'])

    ret = "Uploading \'" + photograph['filename'] +"\'"
    ret = ret + " by '" + photograph['author'] +"\'"

    if "CC-BY-4.0" in photograph['copyright']:
        copyrighttemplate="CC-BY-4.0"
    elif "https://creativecommons.org/licenses/by/4.0/deed.fi" in photograph['copyright']:
        copyrighttemplate="CC-BY-4.0"
    else:
        print("Copyright error")
        print( photograph['copyright'])
        exit(1)

    ret = ret + " with licence " + copyrighttemplate
    ret = ret + " from " + url
    return ret


def flipName(name):
    names= {
      'Andersson Li': 'Li Andersson',
      'Kiuru Krista': 'Krista Kiuru',
      'Blomqvist Thomas': 'Thomas Blomqvist',
      'Haavisto Pekka': 'Pekka Haavisto',
      'Harakka Timo': 'Timo Harakka',
      'Henriksson Anna-Maja': 'Anna-Maja Henriksson',
      'Honkonen Petri': 'Petri Honkonen',
      'Kaikkonen Antti': 'Antti Kaikkonen',
      'Kurvinen Antti': 'Antti Kurvinen',
      'Lintilä Mika': 'Mika Lintilä',
      'Marin Sanna': 'Sanna Marin',
      'Mikkonen Krista': 'Krista Mikkonen',
      'Ohisalo Maria': 'Maria Ohisalo',
      'Paatero Sirpa': 'Sirpa Paatero',
      'Skinnari Ville': 'Ville Skinnari',
      'Tuppurainen Tytti':'Tytti Tuppurainen',
      'Vimpari Anna-Mari': 'Anna-Mari Vimpari',
      'Lehtonen Terhi': 'Terhi Lehtonen',
      'Sarkkinen Hanna': 'Hanna Sarkkinen',
      'Brander Nina': 'Nina Brander',
      'Hovi Heikki': 'Heikki Hovi',
      'Rotkirch Anna': 'Anna Rotkirch',
      'Vuorenkoski Vesa': 'Vesa Vuorenkoski',
      'Haatainen Tuula': 'Tuula Haatainen',
      'Saarikko Annika': 'Annika Saarikko'
      
      
    }
    name=name.strip()

    if name in names:
        return names[name]
    elif name == "Viisikko":
        return name
    elif name == "Government plenary session":
        return name
    elif name == "Prime Minister's official residence":
        return name
    else:
        print(name)
        exit(1)

def createPhotographTemplate(photograph):
    datestr = ''
    creationtime=""
    if photograph['assetcreationtime']:
        date = datetime.datetime.fromtimestamp(photograph['assetcreationtime'])
        creationtime = date.strftime('%Y-%d-%m')
        datestr = "creation time: " + creationtime

    modificationtime=""
    if photograph['assetmodificationtime']:
        date = datetime.datetime.fromtimestamp(photograph['assetmodificationtime'])
        modificationtime = date.strftime('%Y-%d-%m')
        if creationtime!=modificationtime:
            datestr = datestr + "; modification time: " + modificationtime

    filemodificationtime=""
    if photograph['filemodificationtime']:
        date = datetime.datetime.fromtimestamp(int(photograph['filemodificationtime']))
        filemodificationtime = date.strftime('%Y-%d-%m')
        if creationtime!=filemodificationtime and filemodificationtime != modificationtime:
            datestr = datestr + "; file modification time: " + filemodificationtime

    if not datestr:
        print("Date error")
        exit(1)

    if "CC-BY-4.0" in photograph['copyright']:
        copyrighttemplate="{{CC-BY-4.0}}"
    elif "https://creativecommons.org/licenses/by/4.0/deed.fi" in photograph['copyright']:
        copyrighttemplate="{{CC-BY-4.0}}"
    else:
        print("Copyright error")
        print( photograph['copyright'])
        exit(1)

    creator = "{{Creator:Unknown}}"
    institution = "{{Institution:Prime Minister's Office, Finland}}"

    posestr=""
    if photograph['pose']:
       posestr="; " + photograph['pose']      

    if 0:
        template='''\
{{{{Photograph
 |photographer       = {creator}
 |title              = 
 |description        = {topAlbumName} / {albumNameFlipped} / {filename} {posestr}
 |depicted people    = {keywords}
 |depicted place     = 
 |date               = {datestr} 
 |medium             = 
 |dimensions         = 
 |institution        = {institution}
 |department         = 
 |references         = 
 |object history     = 
 |exhibition history = 
 |credit line        = 
 |inscriptions       = 
 |notes              = 
 |accession number   = {download_id}
 |source             = [https://kuvapankki.valtioneuvosto.fi/f/{albumId} {topAlbumName} / {albumName} / {filename}]
 |permission         = {copyright} 
 |other_versions     = 
 |wikidata           = 
 |camera coord       = 
}}}}
== Copyright ==
{copyrighttemplate}
{{{{review}}}}

[[Category: The album of {albumNameFlipped} in the image bank of the Prime Minister's Office, Finland]]
[[Category: Files uploaded by FinnaUploadBot]]
'''.format(datestr=datestr, 
             download_id=photograph['download_id'], 
             filename=photograph['filename'], 
             keywords=photograph['keywords'],
             copyright=photograph['copyright'],
             copyrighttemplate=copyrighttemplate,
             creator=creator,
             institution=institution,
             posestr=posestr)



    template='''\
{{{{Photograph
 |photographer       = {creator}
 |title              = 
 |description        = {filename} {posestr}
 |depicted people    = {keywords}
 |depicted place     = 
 |date               = {datestr} 
 |medium             = 
 |dimensions         = 
 |institution        = {institution}
 |department         = 
 |references         = 
 |object history     = 
 |exhibition history = 
 |credit line        = 
 |inscriptions       = 
 |notes              = 
 |accession number   = {download_id}
 |source             = https://kuvapankki.valtioneuvosto.fi filename: {filename}
 |permission         = {copyright} 
 |other_versions     = 
 |wikidata           = 
 |camera coord       = 
}}}}
== Copyright ==
{copyrighttemplate}
{{{{review}}}}

[[Category: Photos without album in the image bank of the Prime Minister's Office, Finland]]
[[Category: Files uploaded by FinnaUploadBot]]
'''.format(datestr=datestr, 
             download_id=photograph['download_id'], 
             filename=photograph['filename'], 
             keywords=photograph['keywords'],
             copyright=photograph['copyright'],
             copyrighttemplate=copyrighttemplate,
             creator=creator,
             institution=institution,
             posestr=posestr)

    return template




############ MAIN ###############


config.socket_timeout = 120 
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()

# Create a session
session = requests.Session()

# Define the login URL
login_url = "http://kuvapankki.valtioneuvosto.fi/avoin_en"

# Send a GET request to the login URL
response = session.get(login_url)

# Check the response
if response.status_code == 200:
    print("Successfully connected to the site!")
else:
    print("Failed to connect to the site.")

# Get the emmisid cookie
emmisid = session.cookies.get('emmisid')

if emmisid is None:
    print("Failed to get the 'emmisid' cookie.")
    exit(1)

# Create the headers with the 'authorization' header
headers = {
    'Authorization': 'EMMi ' + emmisid,
    'Content-type': 'application/json; charset=utf-8',
    'Host': 'kuvapankki.valtioneuvosto.fi',
    'Origin': 'https://kuvapankki.valtioneuvosto.fi',
    'Referer': 'https://kuvapankki.valtioneuvosto.fi/',
    'Accept-language': 'en-GB,en;q=0.9'
}

# Get parentalbums
topalbums=getFolderChilds(headers, folderName="")

# Uploaded urls
already_uploaded = getUploadedDescriptions()

seek=None


files = searchFiles(headers, "")
for f in files:
    if f['author'].strip()!="": 
        continue

#    if not searchPhotographer(f, "Markku", "Lempinen"):
#        continue
    print(json.dumps(f, indent=2))
    download_url=url="https://kuvapankki.valtioneuvosto.fi/download?coid=1&dl=0&fv=" + str(f['download_id'])
    wikitext=createPhotographTemplate(f)
    filename=createFilename2(f)
    comment=createCommentLine(f)

    if download_url in already_uploaded:
        continue

    if seek and seek!=filename:
        continue
    seek=None


    if "m-7229" in filename:
        continue
    if "pekonen-" in filename:
        continue
    if "m-7235" in filename:
        continue
    if "koski-7_(37443).jpg" in filename:
        continue
    if "koski-6_(37444).jpg" in filename:
        continue
    if "koski-8_(37445).jpg" in filename:
        continue
    if "koski-5_(37446).jpg" in filename:
        continue
    if "koski-4_(37447).jpg" in filename:
        continue
    if "koski-3_(37448).jpg" in filename:
        continue
    if "koski-2_(37449).jpg" in filename:
        continue
    if "koski-1_(37450).jpg" in filename:
        continue
    if "Kesäranta" in filename:
        continue
    

    print(wikitext)
    print(filename)

    imgfile=getValtioneuvostoImagefile(headers, f['download_id'], wikitext, filename, comment)       
    time.sleep(3)


    time.sleep(5)

if 1:
    exit(1)

# Get topic albums
for topalbum in topalbums:
   print(topalbum + "\t" + str(topalbums[topalbum]))
   albums=getFolderChilds(headers, topalbum)

   # handle album files
   for album in albums:
       print(album)
       files = searchFiles(headers, album)
       for f in files:
           if seek and seek!=albums[album]:
               continue
           seek=None

           if albums[album] == "Prime Minister's official residence":
               continue
           
           f['topAlbumId']=topalbum
           f['topAlbumName']=topalbums[topalbum]

           f['albumId']=album
           f['albumName']=albums[album]
#           if f['author'].strip()!="": 
#               continue

           if not searchPhotographer(f, "Markku", "Lempinen"):
               continue
           handleFile(f)


def handleFile(f):
    print(json.dumps(f, indent=2))
    wikitext=createPhotographTemplate(f)
    filename=createFilename(f)
    comment=createCommentLine(f)
    print(wikitext)
    print(filename)
    print(comment)

    imgfile=getValtioneuvostoImagefile(headers, f['download_id'], wikitext, filename, comment)       
    time.sleep(3)

