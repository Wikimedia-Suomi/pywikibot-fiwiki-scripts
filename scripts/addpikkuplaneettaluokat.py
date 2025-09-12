# Purpose: add numbered sorting with padding and alphabetical category
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen

import requests


def insertat(oldtext, pos, string):
    # just insert, otherwise no modification (don't skip or remove anything)
    return oldtext[:pos] + string + oldtext[pos:]

# replace text between given indices with new string
# "foobar" "bah" 2, 5 -> "fobahr"
# - old string between indices does not matter 
# - does not need to be same length
# 
def replacebetween(oldtext, newstring, begin, end):
    if (begin > end):
        print("BUG: beginning is after ending")
        exit(1)

    newtext = oldtext[:begin] + newstring + oldtext[end:]
    return newtext

def getsubstr(text, begin, end):
    return text[begin:end]

# try to catch if there is plain yyyy AA format in page name?
def istemporaryname(name):
    if (len(name) < 4):
        return False

    ispcn = name.find(" ")
    if (ispcn < 0):
        
        # no space, is it a number?
        if (name.isnumeric() == False):
            # not a number, just a normal name -> proper nmae?
            return False
        else:
            print("Just a number as name ? might be malformed", name)
            return True


    # has space, might be a name or a temporary name
    tempnum = name[:ispcn].lstrip().rstrip()
    if (tempnum.isnumeric() == False):
        # not a number, just a normal name -> proper name?
        return False
    
    # if number is between 1900 and 2100 might be a year.. (yyyy AA format)
    itemp = int(tempnum)
    if (itemp > 1900 and itemp < 2100):
        print("Year found most likely ", tempnum)
        #return True

    istempname = False
    tempal = name[ispcn:].lstrip().rstrip()

    #print("DEBUG: date-month in alphabetical ? ", tempal)
    
    # two letters ?
    if (tempal[0].isalpha() == True and tempal[1].isalpha() == True):

        # not a name but uppercase identifier?
        #if (tempal[2].lower() != tempal[2]):
        #    istempname = True

        # there is a number
        #if (tempal[2].isnumeric() == False):
        #    istempname = True

        # only two characters? 
        #if (len(tempal) < 3):
            # if both are uppercase ?
        #    istempname = True

            
        # if there is third character and it is a digit -> temporary name
        if (len(tempal) > 2):
            if (tempal[2].isnumeric() == True):
                #print("DEBUG: index digit after date-month ? ", tempal)
                istempname = True

    return istempname

def parsenameaddcat(oldtext, wdmpcnumber, title):
    
    hasname = False
    if (title.find("(") >= 0 or title.find(")") >= 0 ):
        # not named when number is in parentheses?
        # (french wikipedia uses parentheses though)
        hasname = False
    
    ispc = title.find(" ")
    if (ispc < 0):
        print("DEBUG: no space in title:", title)
        return oldtext

    number = title[:ispc]
    
    # without name -> uses parentheses 
    # (also french wiki preferes parentheses?)
    number = number.replace("(", "")
    number = number.replace(")", "")
    number = number.lstrip().rstrip()
    

    #num = tonumber(number)
    if (number.isnumeric() == False):
        # not a valid number at beginning?
        print("WARNING: not beginning with a valid number:", number)
        return oldtext

    if (number != wdmpcnumber):
        print("WARNING: number in page name ", number ," does not match in wikidata: ", wdmpcnumber)
        return oldtext
    
    print("DEBUG: number is:", number)
    
    name = title[ispc:].lstrip().rstrip()
    if (len(name) < 2):
        # not long enough for a name?
        hasname = False
        return oldtext

    print("DEBUG: name is:", name)
    
    # try to catch if there is plain yyyy AA format in page name?
    # if number is between 1900 and 2100 might be a year.. (yyyy AA format)
    if (istemporaryname(name) == True):
        print("Only a temporary name ? ", name)
        #hasname = False
        

    # at least two letters? 
    # try to catch if there is plain yyyy AA format in page name?
    if (name[0].isalpha() == True and name[1].isalpha() == True):

        # not a name but uppercase identifier? (two letter identifier instead of two letter name)
        if (name[1].lower() != name[1] and len(name) < 3):
            hasname = False

        # defaulting to "no name" so if it is a letter may be a name
        if (name[1].isnumeric() == False):
            hasname = True
            
        # if there is third character it should not be a digit
        if (len(name) > 2):
            if (name[2].isnumeric() == False):
                hasname = True
    else:
        print("DEBUG: not valid name:", name)

    if (hasname == False):
        print("DEBUG: no valid name, maybe temporary name? ")
        #return oldtext

    paddinglen = 6-(len(number))
    paddednum = ""
    i = 0
    while (i < paddinglen):
        paddednum = paddednum + "0"
        i += 1
    paddednum = paddednum + number
    sort = "{{AAKKOSTUS:" + paddednum + "}}\n"
    
   
    if (oldtext.find("{{AAKKOSTUS") < 0):
        firstcat = oldtext.find("[[Luokka:")
        if (firstcat > 0):
            oldtext = insertat(oldtext, firstcat, sort)
    else:
        print("DEBUG: already has sorting")
    
    namedcat = ""
    if (hasname == True and oldtext.find(":Nimetyt pikkuplaneetat") < 0):
        namedcat = "[[Luokka:Nimetyt pikkuplaneetat|" + name + "]]"
        oldtext = oldtext + "\n" + namedcat + "\n"
    else:
        print("DEBUG: already in named category or not named yet")

    return oldtext


def hassorting(oldtext):
    if (oldtext.find("{{AAKKOSTUS") >= 0):
        return True
    return False


def isincategory(oldtext):
    if (oldtext.find(":Nimetyt pikkuplaneetat") >= 0):
        return True
    return False
    

# just debug
def checkqcode(itemfound, lang='fi'):
    print("item id, ", itemfound.getID())
    for li in itemfound.labels:
        label = itemfound.labels[li]
        if (li == lang):
            print("DEBUG: found label with lang: ", label)
            return True
        else:
            print("DEBUG: found label: ", label)
    return False

def getmpcnumber(itemfound):
    #P5736
    mpc_entity = itemfound.claims.get('P5736', [])

    for claim in mpc_entity:
        target = claim.getTarget()
        if (target != None):
            #print("target: ", str(target))
            # check type: is it string or number?
            return target
            #return target.lstrip().rstrip()
    return None
    

def checkwikidata(wdsite, itemqcode):

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return False
    
    dictionary = itemfound.get()
    
    # debug print
    #checkqcode(itemfound)
    
    knowntype = False
    
    # check entity type (instance of)
    instance_of = itemfound.claims.get('P31', [])
    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page, skipping")
            return False # skip for now

        # asteroidi (voi olla myös komeetta)
        if (claim.getTarget().id == 'Q3863'):
            print("instance ok, found asteroid id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q2199'):
            print("instance ok, found dwarf planet id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q29370670'):
            print("instance ok, found potential dwarf planet id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q59423687'):
            print("instance ok, found potentially dangerous asteroid id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q217526'):
            print("instance ok, found near earth asteroid id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q6635'):
            print("instance ok, found resonant transneptune object id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q645924'):
            print("instance ok, found cubewano id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q6599'):
            print("instance ok, found plutino id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q2517684'):
            print("instance ok, found twotino id: ", claim.getTarget().id)
            knowntype = True

        if (claim.getTarget().id == 'Q1621992'):
            print("instance ok, found damocloid id: ", claim.getTarget().id)
            knowntype = True

        #resonantti transneptuninen kohde ()
        # Q2199 kääpiöplaneetta
        # Q645924 cubewano 
        #Maan lähelle tuleva kappale (Q265392)
        #mahdollisesti vaarallinen asteroidi (Q59423687)
        #Maan lähelle tuleva kappale (Q265392)
        #Maan lähelle tuleva asteroidi (Q217526)
        #mahdollinen kääpiöplaneetta (Q29370670)
        #else:
        #    print("DEBUG: instance id: ", claim.getTarget().id)
    
    # TODO: jos sivunimessä on väliaikainen tunniste (P490) -> ohitetaan
    
    # haetaan MPC-tunniste (P5736), tarkistetaan täsmäävyys
    if (knowntype == True):
        mpcnum = getmpcnumber(itemfound)
        if (mpcnum != None):
            print("MPC number:", mpcnum)
            return mpcnum
    
    return None


# ei rivinvaihtoa viitemallineen perässä? -> lisätään puuttuva
def addnewline(oldtext):
    reftup = findrefs(oldtext)
    if (reftup[0] < 0):
        # not found or some other form of making the refs list..
        return oldtext

    index = reftup[0]
    strlen = len(reftup[1])
    
    # verify we can find string with newline at end
    tmpstr = oldtext[index:index+strlen+1]
    if tmpstr.endswith("\n"):
        # at least one newline there, ok
        return oldtext
    else:
        # add one linefeed (beginning .. newline .. rest)
        return oldtext[:index+strlen] + "\n" + oldtext[index+strlen:]

def getpagesrecurse(pywikibot, site, maincat, depth=1):
    #final_pages = list()
    cat = pywikibot.Category(site, maincat)
    pages = list(cat.articles(recurse=depth))
    return pages

# list of newest pages in given category
def getnewestpagesfromcategory(pywikibot, site, maincat, limit=100):

    cat = pywikibot.Category(site, maincat)
    newest = cat.newest_pages(limit)
    
    pages = list()
    for page in newest:
        #print("name: ", page.title())
        # skip if not in file namespace?
        #if (page.namespace() != 6):  # 6 is the namespace ID for files
        if (page.namespace() != 0):  
            continue
        
        #fp = pywikibot.FilePage(site, page.title())
        fp = pywikibot.Page(site, page.title())
        if (fp not in pages):
            pages.append(fp)
    return pages

def getpagesfrompetscan(pywikibot, site, psid, limit=6000):

    pages = list()

    # property: takso, artikkelissa taksonomiamalline (/kasvit, /eläimet)
    #url = "https://petscan.wmflabs.org/?psid=26259099"
    url = "https://petscan.wmflabs.org/?psid=" + str(psid)
    url += "&format=json"
    url += "&output_limit=" + str(limit)
    response = urlopen(url)
    data_json = json.loads(response.read())
    if (data_json == None):
        print("No data")
        return None
    if (len(data_json) == 0):
        print("empty data")
        return None

    for row in data_json['*'][0]['a']['*']:
        page = pywikibot.Page(site, row['title'])
        pages.append(page)

    return pages

# try using mediawiki API for searching pages
# https://www.mediawiki.org/wiki/API:Search
def getsearchpages(pywikibot, site, searchstring):
    pages = list()
    
    URL = "https://fi.wikipedia.org/w/api.php"

    hasMoreItems = True
    contfrom = 0

    while (hasMoreItems == True):
        PARAMS = {}

        if (hasMoreItems == True):
            PARAMS = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srlimit": "500",
                "srsort": "create_timestamp_desc",
                "sroffset": contfrom,
                "srsearch": searchstring
            }
        else:
            PARAMS = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srlimit": "500",
                "srsort": "create_timestamp_desc",
                "srsearch": searchstring
            }

        S = requests.Session()
        S.headers.update({'User-Agent': 'pywikibot'}) # noqa
        R = S.get(url=URL, params=PARAMS)
        DATA = R.json()
        
        if "continue" in DATA:
            print("continue search from: ", DATA['continue']['sroffset'])
            contfrom = DATA['continue']['sroffset']
        else:
            hasMoreItems = False
        
        #print(str(DATA))
        for p in DATA['query']['search']:
            #print(str(p))

            title = p['title']
            pid = p['pageid']

            #print("res: ", title, "", pid)
            page = pywikibot.Page(site, title)
            pages.append(page)

    return pages 

## main()

site = pywikibot.Site("fi", "wikipedia")
site.login()

wdsite = pywikibot.Site('wikidata', 'wikidata')
wdsite.login()


#pages = getnewestpagesfromcategory(pywikibot, site, "Päävyöhykkeen asteroidit", 10)

#pages = getpagesrecurse(pywikibot, site, "Päävyöhykkeen asteroidit", 0)

#pages = getpagesrecurse(pywikibot, site, "Marsin radan leikkaaja-asteroidit", 1)

#pages = getnewestpagesfromcategory(pywikibot, site, "Marsin radan leikkaaja-asteroidit", 10)

#pages = getpagesrecurse(pywikibot, site, "Maan lähelle tulevat asteroidit", 1)

#pages = getpagesrecurse(pywikibot, site, "Asteroidiryhmät", 1)

#pages = getpagesrecurse(pywikibot, site, "Jupiterin troijalaiset", 0)

#pages = getnewestpagesfromcategory(pywikibot, site, "Jupiterin troijalaiset", 10)

#pages = getpagesrecurse(pywikibot, site, "Troijalaiset pikkuplaneetat", 1)

#pages = getpagesrecurse(pywikibot, site, "Asteroidit", 0)


pages = getpagesrecurse(pywikibot, site, "Hajanaisen kiekon kohteet", 0)

#pages = getnewestpagesfromcategory(pywikibot, site, "Transneptuniset kohteet", 10)

#pages = getpagesrecurse(pywikibot, site, "Transneptuniset kohteet", 1)
#pages = getpagesrecurse(pywikibot, site, "Cubewanot", 0)
#pages = getpagesrecurse(pywikibot, site, "Plutinot", 0)
#pages = getpagesrecurse(pywikibot, site, "Twotinot", 0)

#pages = getpagesrecurse(pywikibot, site, "Kentaurit (pikkuplaneetat)", 0)

#pages = getpagesrecurse(pywikibot, site, "Kaukaisten pikkuplaneettojen ryhmät", 1)

#pages = getpagesrecurse(pywikibot, site, "Mahdolliset kääpiöplaneetat", 0)



rivinro = 1
commitall = False

for page in pages:
    # skip user-pages, only main article namespace
    if (page.namespace() != 0):  
        print("Skipping " + page.title() + " - wrong namespace.")
        continue
    
    
    #page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" ////////", rivinro, "/", len(pages), ": [ " + page.title() + " ] ////////")
    rivinro += 1

    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping " + page.title() + " - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + page.title() + " - bot-restricted.")
        continue

    if (hassorting(oldtext) == True and isincategory(oldtext) == True):
        print("Skipping " + page.title() + " - has sorting and category.")
        continue
    
    # get entity id of page
    pageqid = page.data_item().getID()
    print("Page " + page.title() + " has id: ", pageqid)

    # try to get MPC number from wikidata:
    # if it does not have one -> only temporary identification 
    mpcnumber = checkwikidata(wdsite, pageqid)
    if (mpcnumber == None):
        print("Skipping page: " + page.title() + " - not suitable type or no MPC number.")
        continue

    temptext = oldtext

    summary='Lisätään luokittelu ja aakkostus'
    temptext = parsenameaddcat(temptext, mpcnumber, page.title())

    
    if oldtext == temptext:
        print("Skipping. " + page.title() + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

    if (commitall == True):
        page.text=temptext
        page.save(summary)
    else:
        question='Do you want to accept these changes?'
        choice = pywikibot.input_choice(
                    question,
                    [('Yes', 'y'),('No', 'N'),('All', 'a'),('Quit', 'q')],
                    default='N',
                    automatic_quit=False
                )

        pywikibot.info(choice)
        if choice == 'q':
            print("Asked to exit. Exiting.")
            exit()

        if choice == 'a':
            commitall = True

        if choice == 'y' or choice == 'a':
            page.text=temptext
            page.save(summary)

