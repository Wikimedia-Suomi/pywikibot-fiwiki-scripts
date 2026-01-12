# Purpose: add numbered sorting with padding and alphabetical category
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen

import requests


def hascategorytext(text, catname):
    if (text.find(catname) > 0):
        return True
    return False

def endswithnewline(text):
    if (text[len(text)-1] == "\n"):
        return True
    return False

def getcategoryfortno(tnoqcode):
    d_tnocat = dict()
    d_tnocat["Q645924"] = "Cubewanot"
    d_tnocat["Q6599"] = "Plutinot"
    d_tnocat["Q2517684"] = "Twotinot"
    
    d_tnocat["Q2447669"] = "Haumea-ryhmä"
    d_tnocat["Q180380"] = "Hajanaisen kiekon kohteet"
    d_tnocat["Q10734"] = "Kentaurit (pikkuplaneetat)"
    d_tnocat["Q1621992"] = "Damocloidit"
    d_tnocat["Q17148298"] = "Sednoidit"
    
    # huomaa, ylempi luokka (älä lisää jos on jo tarkemmassa)
    #d_tnocat["Q6592"] = "Transneptuniset kohteet"

    # resonantit kohteet?

    if (tnoqcode == None):
        return ""

    if (len(tnoqcode) == 0):
        return ""
    
    if tnoqcode in d_tnocat: # skip unknown tags
        return d_tnocat[tnoqcode]

    return ""

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

def parsenameaddcats(oldtext, wdmpcnumber, wdtnoqid, speccats, title):
    
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
        
    # TODO: this is bugging in some characters in names like "O'Keefe"
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

    # huom: wikidatan ryhmä voi olla virheellinen,
    # jos ollaan luokiteltu aliryhmään (plutino, cubewano, twotino)
    # älä lisää toista ryhmää wikidatan perusteella
    tnocat = getcategoryfortno(wdtnoqid)
    if (len(tnocat) > 0):
        # don't add second time for same group,
        # haumea-group might need to be a sub-group -> don't add per article cat for those
        if (oldtext.find(":"+ tnocat +"") < 0 and oldtext.find("Luokka:Haumea-ryhmä") < 0):
            tnocat = "[[Luokka:" + tnocat+ "]]"
            oldtext = oldtext + "\n" + tnocat + "\n"
        else:
            print("DEBUG: already in TNO sub-category for:", tnocat)

    #cattoadd = list()
    for sc in speccats:
        print("DEBUG: check for category", sc)
        if (hascategorytext(oldtext, sc) == False):
            #cattoadd.append(sc)
            if (endswithnewline(oldtext) == True):
                oldtext = oldtext + "[[" + sc + "]]\n"
            else:
                oldtext = oldtext + "\n[[" + sc + "]]\n"

    return oldtext


def hassorting(oldtext):
    if (oldtext.find("{{AAKKOSTUS") >= 0):
        return True
    return False


def isincategory(oldtext):
    if (oldtext.find(":Nimetyt pikkuplaneetat") >= 0):
        return True
    return False
    
def getitembyqcode(repo, itemqcode):

    item = pywikibot.ItemPage(repo, itemqcode)
    if (item.isRedirectPage() == True):
        return None
    return item

def getlabelbylangfromitem(item, lang):

    for li in item.labels:
        label = item.labels[li]
        if (li == lang):
            print("DEBUG: found label for ", item.getID() ," in lang ", lang ,": ", label)
            return label
    return None

def getqidsfromprop(item, prop):
    qids = list()
    prop = item.claims.get(prop, [])
    for claim in prop:
        target = claim.getTarget()
        if (target != None):
            qid = claim.getTarget().id
            if qid not in qids:
                qids.append(qid)
    return qids

def getRankValue(rankname):
    rank_order = {'preferred': 3, 'normal': 2, 'deprecated': 1}
    if rankname in rank_order:
        return rank_order[rankname]
    return 0

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

def getspectraltypeswd(item):
    
    qids = list()
    
    spectype = item.claims.get('P720', [])
    for claim in spectype:

        ranktmp = claim.getRank()
        print("DEBUG: found rank ", ranktmp," for item")
        ranknro = getRankValue(ranktmp)
        if (ranknro < 2):
            # ignore lowest ranks (deprecated)
            print("DEBUG: skipping low rank")
            continue
        
        target = claim.getTarget()
        if (target != None):
            qid = claim.getTarget().id
            if qid not in qids:
                qids.append(qid)
    return qids

# ideally spectral type would have one category only..
def getcategoryforspectraltypewd(repo, qids):
    if (qids == None):
        return None
    if (len(qids) < 1):
        return None

    cats = list()

    for qid in qids:
        item = getitembyqcode(repo, qid)
        if (item == None):
            continue
        
        catqids = getqidsfromprop(item, 'P910')

        for q in catqids:
            catitem = getitembyqcode(repo, q)
            if (catitem != None):
                catlabel = getlabelbylangfromitem(catitem, 'fi')
                if catlabel not in cats:
                    cats.append(catlabel)

    return cats
    

def getmpcnumber(item):
    #P5736
    mpc_entity = item.claims.get('P5736', [])

    for claim in mpc_entity:
        target = claim.getTarget()
        if (target != None):
            #print("target: ", str(target))
            # check type: is it string or number?
            return target
            #return target.lstrip().rstrip()
    return None

# get type of transneptunian object (tno):
# cubewano, plutino or twotino
def gettnotypewd(itemfound):

    if (itemfound.isRedirectPage() == True):
        return ""
    
    target = ""

    instance_of = itemfound.claims.get('P31', [])
    for claim in instance_of:
        if (claim.getTarget().id == 'Q645924'):
            print("instance ok, found cubewano id: ", claim.getTarget().id)
            target = claim.getTarget().id
            break

        if (claim.getTarget().id == 'Q6599'):
            print("instance ok, found plutino id: ", claim.getTarget().id)
            target = claim.getTarget().id
            break

        if (claim.getTarget().id == 'Q2517684'):
            print("instance ok, found twotino id: ", claim.getTarget().id)
            target = claim.getTarget().id
            break
        
        # Q6592 == transneptuninen kohde

    # if asteroidiperhe P744 == Haumea-ryhmä Q2447669
    # if asteroidiperhe P744 == hajanainen kiekko Q180380
    # -> ei lisätä muuta alaluokkaa?

    asteroidfamily = itemfound.claims.get('P744', [])
    for family in asteroidfamily:
        if (family.getTarget().id == 'Q2447669'):
            print("found Haumea-group qid: ", family.getTarget().id)
            return family.getTarget().id
        if (family.getTarget().id == 'Q180380'):
            print("found scattered disc group qid: ", family.getTarget().id)
            return family.getTarget().id

    return target
    #if (len(target) > 0):
    #    return target
    #return None

    
# check item is acceptable minor planet,
# return minor planet number (if any)
def checkminorplanetwd(itemfound):

    # redirect-entity in wikidata?
    if (itemfound.isRedirectPage() == True):
        return None

    #dictionary = itemfound.get()

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
        
        
        if (claim.getTarget().id == 'Q6592'):
            print("instance ok, found transneptunian object id: ", claim.getTarget().id)
            knowntype = True

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

        if (claim.getTarget().id == 'Q23978241'):
            # "threetino"
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

# for testing
def getpagebyname(pywikibot, site, name):
    return pywikibot.Page(site, name)

def getnamedpages(pywikibot, site):
    pages = list()
    
    fp = getpagebyname(pywikibot, site, "2056 Nancy")

    pages.append(fp)
    return pages


## main()

site = pywikibot.Site("fi", "wikipedia")
site.login()

wdsite = pywikibot.Site('wikidata', 'wikidata')
wdsite.login()

# for testing
#pages = getnamedpages(pywikibot, site)

pages = getnewestpagesfromcategory(pywikibot, site, "Päävyöhykkeen asteroidit", 20)
#pages = getpagesrecurse(pywikibot, site, "Päävyöhykkeen asteroidit", 0)


#pages = getnewestpagesfromcategory(pywikibot, site, "Jupiterin troijalaiset", 10)
#pages = getpagesrecurse(pywikibot, site, "Jupiterin troijalaiset", 0)

#pages = getpagesrecurse(pywikibot, site, "Neptunuksen troijalaiset", 0)
#pages = getpagesrecurse(pywikibot, site, "Marsin troijalaiset", 0)
#pages = getpagesrecurse(pywikibot, site, "Maan troijalaiset", 0)

#pages = getpagesrecurse(pywikibot, site, "Troijalaiset pikkuplaneetat", 1)

#pages = getnewestpagesfromcategory(pywikibot, site, "Marsin radan leikkaaja-asteroidit", 10)
#pages = getpagesrecurse(pywikibot, site, "Marsin radan leikkaaja-asteroidit", 0)

#pages = getnewestpagesfromcategory(pywikibot, site, "Amor-asteroidit", 10)
#pages = getnewestpagesfromcategory(pywikibot, site, "Aten-asteroidit", 10)
#pages = getnewestpagesfromcategory(pywikibot, site, "Apollo-asteroidit", 10)

#pages = getpagesrecurse(pywikibot, site, "Maan lähelle tulevat asteroidit", 1)
#pages = getpagesrecurse(pywikibot, site, "Apollo-asteroidit", 0)
#pages = getpagesrecurse(pywikibot, site, "Amor-asteroidit", 0)
#pages = getpagesrecurse(pywikibot, site, "Aten-asteroidit", 0)
#pages = getpagesrecurse(pywikibot, site, "Atira-asteroidit", 0)

#pages = getpagesrecurse(pywikibot, site, "Asteroidiryhmät", 1)

#pages = getpagesrecurse(pywikibot, site, "Asteroidit", 0)


#pages = getpagesrecurse(pywikibot, site, "Hajanaisen kiekon kohteet", 0)

#pages = getnewestpagesfromcategory(pywikibot, site, "Transneptuniset kohteet", 10)
#pages = getnewestpagesfromcategory(pywikibot, site, "Transneptuniset kohteet", 20)

#pages = getpagesrecurse(pywikibot, site, "Transneptuniset kohteet", 1)
#pages = getpagesrecurse(pywikibot, site, "Cubewanot", 0)
#pages = getpagesrecurse(pywikibot, site, "Plutinot", 0)
#pages = getpagesrecurse(pywikibot, site, "Twotinot", 0)

#pages = getpagesrecurse(pywikibot, site, "Haumea-ryhmä", 0)

#pages = getpagesrecurse(pywikibot, site, "Kentaurit (pikkuplaneetat)", 0)

#pages = getpagesrecurse(pywikibot, site, "Kaukaisten pikkuplaneettojen ryhmät", 1)

#pages = getpagesrecurse(pywikibot, site, "Mahdolliset kääpiöplaneetat", 0)

#pages = getpagesrecurse(pywikibot, site, "Nimetyt pikkuplaneetat", 0)


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
        print("Skipping ", page.title() ," - bot-restricted.")
        continue

    # skip for testing
    if (hassorting(oldtext) == True and isincategory(oldtext) == True):
        print("Skipping ", page.title() ," - has sorting and category.")
        continue
    
    # get entity id of page
    pageqid = page.data_item().getID()
    print("Page " + page.title() + " has id: ", pageqid)

    repo = wdsite.data_repository()
    wditem = pywikibot.ItemPage(repo, pageqid)

    # try to get MPC number from wikidata:
    # if it does not have one -> only temporary identification 
    mpcnumber = checkminorplanetwd(wditem)
    if (mpcnumber == None):
        print("Skipping page: ", page.title() ," - not suitable type or no MPC number.")
        continue
    
    # try to see if it is known supported TNO sub-type (we have cats for it)
    tnoqid = gettnotypewd(wditem)
    if (tnoqid != None and len(tnoqid) > 0):
        print("Found TNO qid: ", tnoqid, "for:", page.title() ," - might add extra category")
        
    speccats = list()
    spectypes = getspectraltypeswd(wditem)
    if (spectypes != None and len(spectypes) > 0):
        print("Found spectral types", spectypes)
        speccats += getcategoryforspectraltypewd(repo, spectypes)

    temptext = oldtext
    summary='Lisätään luokittelu ja aakkostus'
    temptext = parsenameaddcats(temptext, mpcnumber, tnoqid, speccats, page.title())

    
    if oldtext == temptext:
        print("Skipping. ", page.title() ," - old and new are equal.")
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

