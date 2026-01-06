# Purpose: add categories per person according to wikidata
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen


import requests

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from datetime import date


# try to support partial dates
class SimpleTimestamp:
    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0
        self.precision = 0

    def isValidDay(self, iday):
        if (iday < 1 or iday > 31):
            # not a valid day
            return False
        return True

    def isValidMonth(self, imon):
        if (imon < 1 or imon > 12):
            # not a valid month
            return False
        return True

    def isValidYear(self, iyr):
        if (iyr < 1 or iyr > 9999):
            # not a valid year
            return False
        return True
    
    def isValid(self):
        if (self.isValidDay(self.day) == True
            and self.isValidMonth(self.month) == True
            and self.isValidYear(self.year) == True):
            return True
        return False

    def setDate(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day



def getsubstr(text, begin, end):
    if (end < begin):
        return -1
    return text[begin:end]

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

# Function to check if the Wikidata item is a human
def is_human(item):
    human_qid = 'Q5'  # QID for human
    instance_of = item.claims.get('P31', [])
    
    for claim in instance_of:
        #qid = claim.getTarget().id
        if (claim.getTarget().id == human_qid):
            return True
    return False

def getitembyqcode(repo, itemqcode):

    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return None
    return itemfound


def findnonzeroch(text, begin, end):
    #begin = 0
    #end = len(text)

    if (end < begin):
        return -1

    i = begin
    while (i < end):
        ch = text[i]
        
        if (ch != "0"):
            #print("DEBUG: non-zero ch")
            return i
        #else:
            #print("DEBUG: skipping zero")
        i += 1
    return -1

def getprecision(jsonstr):
    ix = jsonstr.find("precision")
    if (ix < 0):
        return 0
    ixcol = jsonstr.find(":", ix)
    if (ixcol < 0):
        return 0
    ixend = jsonstr.find(",", ixcol)
    if (ixend < 0):
        return 0
    if ((ixend-ixcol) < 1):
        print("DEBUG: not enough characters for precision")
        return 0

    tstr = getsubstr(jsonstr, ixcol+1, ixend)
    #tstr = tstr.replace('"', "")
    tstr = tstr.strip()

    print("DEBUG: found precision", tstr)
    
    return int(tstr)

#
#DEBUG: found birth date {
#    "after": 0,
#    "before": 0,
#    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
#    "precision": 9,
#    "time": "+00000001775-01-01T00:00:00Z",
#    "timezone": 0
#}  for item
def parsewikibasetime(wikibasestr):
    print("DEBUG: parsing", wikibasestr, "")
    
    jsonstr = str(wikibasestr)
    #d_time = json.loads(wikibasestr)
    
    iprec = getprecision(jsonstr)
    #if (iprec <= 7):
    if (iprec < 7): # at least decade should be needed?
        print("WARN: not enough precision for timestamp")
        return None
    
    ix = jsonstr.find("time")
    if (ix < 0):
        return None
    ixcol = jsonstr.find(":", ix)
    if (ixcol < 0):
        return None
    ixend = jsonstr.find(",", ixcol)
    if (ixend < 0):
        return None
    if ((ixend-ixcol) < 5):
        print("DEBUG: not enough characters for timestamp")
        return None
    
    tstr = getsubstr(jsonstr, ixcol+1, ixend)
    tstr = tstr.replace('"', "")
    tstr = tstr.strip()

    print("DEBUG: found", tstr, "")
    
    if (tstr[0] != "+"):
        print("WARN: unexpected beginning")
        #return None

    ixt = tstr.find("T")
    if (ixt > 0):
        tstr = tstr[:ixt]
        
    tstr = tstr.replace("+", "")
    ixnz = findnonzeroch(tstr, 0, len(tstr)-1)
    if (ixnz > 0):
        tstr = tstr[ixnz:]
        print("DEBUG: stripped to", tstr, "")
    #else:
        #print("DEBUG: no leading zeroes?")

    # TODO: 
    # also check for precision?
    # precision=7 and 1950-00-00T00:00:00 -> 20. century 

    tstr = tstr.strip()
    print("DEBUG: converting", tstr, "")
    
    
    tsl = tstr.split("-")
    tss = SimpleTimestamp()
    tss.year = tsl[0]
    tss.month = tsl[1]
    tss.day = tsl[2]
    
    tss.precision = iprec
    
    # this throws exception when day and month are zero
    #dt = datetime.strptime(tstr, '%Y-%m-%d')
    #if (tstr.find("00-00") > 0):
        # mssing month and day?
        # python throws exception..
        #dt = date.fromisoformat(tstr)
    return tss


#def getWbdate():
#    return pywikibot.WbTime(dt.year, dt.month, dt.day)


def getRankValue(rankname):
    rank_order = {'preferred': 3, 'normal': 2, 'deprecated': 1}
    if rankname in rank_order:
        return rank_order[rankname]
    return 0

#def getBestRankedClaim(item):

def getBirthdates(item):
    ldates = list()

    # try to use best rank available
    rank = 0
    dt = None

    days = item.claims.get('P569', [])
    for claim in days:
        
        # sort by rank
        ranktmp = claim.getRank()
        print("DEBUG: found rank ", ranktmp," for item")
        ranknro = getRankValue(ranktmp)
        if (ranknro < 2):
            # ignore lowest ranks
            print("DEBUG: skipping low rank")
            continue
        if (ranknro < rank):
            #print("DEBUG: skipping lower rank")
            continue
        if (ranknro > rank):
            ldates.clear()

        rank = ranknro
        
        target = claim.getTarget()
        print("DEBUG: found birth date", target," for item")
        
        #sources = claim.getSources()

        dt = parsewikibasetime(target)
        ldates.append(dt)

    return dt

def getDeathdates(item):
    ldates = list()
    
    # try to use best rank available
    rank = 0
    dt = None

    days = item.claims.get('P570', [])
    for claim in days:
        
        # sort by rank
        ranktmp = claim.getRank()
        print("DEBUG: found rank ", ranktmp," for item")
        ranknro = getRankValue(ranktmp)
        if (ranknro < 2):
            # ignore lowest ranks
            print("DEBUG: skipping low rank")
            continue
        if (ranknro < rank):
            #print("DEBUG: skipping lower rank")
            continue
        if (ranknro > rank):
            ldates.clear()

        rank = ranknro
        
        target = claim.getTarget()
        print("DEBUG: found death date", target," for item")

        #sources = claim.getSources()
        
        dt = parsewikibasetime(target)
        ldates.append(dt)

    return dt


# get existing categories from page
def getpagecategories(text):
    
    categories = list()
    i = 0
    end = len(text)
    while (i < end):
        noupper = False
        nolower = False
        ibegin = text.find("[[Luokka:", i)
        if (ibegin > 0):
            iend = text.find("]]", ibegin)
            if (iend > 0 ):
                ibegin = ibegin + len("[[Luokka:")
                cat = getsubstr(text, ibegin, iend)
                ipipe = cat.find("|")
                if (ipipe > 0):
                    cat = cat[:ipipe]
                categories.append(cat.strip())
                i = iend
        else:
            noupper = True

        ibegin = text.find("[[luokka:", i)
        if (ibegin > 0):
            iend = text.find("]]", ibegin)
            if (iend > 0 ):
                ibegin = ibegin + len("[[luokka:")
                cat = getsubstr(text, ibegin, iend)
                ipipe = cat.find("|")
                if (ipipe > 0):
                    cat = cat[:ipipe]
                categories.append(cat.strip())
                i = iend
        else:
            nolower = True
            
        if (noupper == True and nolower == True):
            break
    return categories


def checkmissingcategories(page, item, text):
    if (is_human(item) == False):
        # not human, skip item
        return None
    
    # note: if there are more than one year, check if they are the same
    bdt = getBirthdates(item)
    ddt = getDeathdates(item)
    
    existingcats = getpagecategories(text)
    print("DEBUG: found categories", existingcats)
    
    hasbday = False
    hasdday = False
    for cat in existingcats:
        # vuonna xxx syntyneet
        if (cat.find("syntyneet") > 0 and (cat.find("Vuonna") >= 0 or cat.find("luvulla") >= 0)):
            hasbday = True
        # vuonna xxx kuolleet, there are categories with "kuolleet" too
        if (cat.find("kuolleet") > 0 and (cat.find("Vuonna") >= 0 or cat.find("luvulla") >= 0)):
            hasdday = True
        if (cat.find("Syntymävuosi puuttuu") > 0):
            hasbday = True
        if (cat.find("Kuolinvuosi puuttuu") > 0):
            hasdday = True

    catstoadd = list()
    if (hasbday == False and bdt != None):
        # we should add birthday category:
        # get date from list, parse to year
        syear = str(bdt.year)
        
        if (bdt.precision == 7):
            newcat = ""+syear+"-luvulla syntyneet"
        if (bdt.precision > 7):
            newcat = "Vuonna "+syear+" syntyneet"

        # don't add if there is no source: has mark as missing
        if ("Syntymävuosi puuttuu" not in existingcats and "Syntymävuosi tuntematon" not in existingcats):
            catstoadd.append(newcat)

    if (hasbday == False and bdt == None):
        if ("Syntymävuosi puuttuu" not in existingcats and "Syntymävuosi tuntematon" not in existingcats):
            catstoadd.append("Syntymävuosi puuttuu")

    if (hasdday == False and ddt != None):
        # we should add birthday category
        # get date from list, parse to year
        syear = str(ddt.year)
        if (ddt.precision == 7):
            newcat = ""+syear+"-luvulla kuolleet"
        if (ddt.precision > 7):
            newcat = "Vuonna "+syear+" kuolleet"
        
        # don't add if there is no source: has mark as missing
        if ("Kuolinvuosi puuttuu" not in existingcats 
            and "Kuolinvuosi tuntematon" not in existingcats
            and "Elävät henkilöt" not in existingcats): 
            catstoadd.append(newcat)

    if (hasdday == False and ddt == None):
        if ("Elävät henkilöt" not in existingcats 
            and "Kuolinvuosi tuntematon" not in existingcats 
            and "Kuolinvuosi puuttuu" not in existingcats):
            catstoadd.append("Elävät henkilöt") 

    return catstoadd


def endswithnewline(text):
    if (text[len(text)-1] == "\n"):
        return True
    return False

# double-check before adding: might have missed earlier
#
def iscategoryalreadyinpagetext(oldtext, catname):
    variations = list()
    
    # might have sort key after class name?
    # also upper or lower case, with or without space
    variations.append("[[Luokka:" + catname + "]]")
    variations.append("[[luokka:" + catname + "]]")
    variations.append("[[Luokka: " + catname + "]]")
    variations.append("[[luokka: " + catname + "]]")
    variations.append("[[Luokka:" + catname + "|")
    variations.append("[[luokka:" + catname + "|")
    variations.append("[[Luokka: " + catname + "|")
    variations.append("[[luokka: " + catname + "|")
    
    for var in variations:
        #print("DBEUG: searching category: ", var)
        ix = oldtext.find(var)
        if (ix > 0):
            #print("DBEUG: found category: ", var)
            return True
    return False


def addlistedcatstopage(oldtext, cats):

    for cn in cats:
        
        # must not have class yet, try lower-case search as well
        if (iscategoryalreadyinpagetext(oldtext, cn) == False):
            if (endswithnewline(oldtext) == False):
                oldtext = oldtext + "\n[[Luokka:" + cn + "]]\n"
            else:
                oldtext = oldtext + "[[Luokka:" + cn + "]]\n"
        else:
            print("already has category ", cn, " - skipping")

    return oldtext


def getpagebyname(pywikibot, site, name):
    return pywikibot.Page(site, name)

def getnamedpages(pywikibot, site):
    pages = list()
    
    
    #fp = getpagebyname(pywikibot, site, "Michael Gold")


    pages.append(fp)
    return pages


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


#pages = getpagesfrompetscan(pywikibot, site, 26153859, 30000)

#pages = getnewestpagesfromcategory(pywikibot, site, "", 20)
#pages = getpagesrecurse(pywikibot, site, "Yhdysvaltalaiset toimittajat", 0)

#pages = getpagesrecurse(pywikibot, site, "Uzbekistanilaiset henkilöt", 0)
#pages = getpagesrecurse(pywikibot, site, "Turkmenistanilaiset henkilöt", 0)


#pages = getpagesrecurse(pywikibot, site, "Kiinalaiset kirjailijat", 0)

#pages = getpagesrecurse(pywikibot, site, "Turkmenistanilaiset henkilöt", 2)
#pages = getpagesrecurse(pywikibot, site, "Uzbekistanilaiset henkilöt", 2)

pages = getpagesrecurse(pywikibot, site, "Stalinin vainoissa kuolleet", 0)


# for testing
#pages = getnamedpages(pywikibot, site)

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

    # get entity id of page
    pageqid = page.data_item().getID()
    print("Page " + page.title() + " has id: ", pageqid)

    repo = wdsite.data_repository()
    wditem = pywikibot.ItemPage(repo, pageqid)

    temptext = oldtext
    
    newcats = checkmissingcategories(page, wditem, oldtext)
    if (newcats == None):
        print("Skipping. ", page.title() ," - not suitable type.")
        continue
    if (len(newcats) == 0):
        print("Skipping. ", page.title() ," - no categories needed.")
        continue

    summary = 'Lisätään puuttuvia luokkia'
    temptext = addlistedcatstopage(temptext, newcats)
    
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

