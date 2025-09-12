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

def is_existing_page(site, title):

    # note: what to do with redirect page?
    # 
    try:
        # What happens if page does not exist yet?
        page = pywikibot.Page(site, title)
        
        # is None returned?
        if (page != None):
            # might throw exception if page does not exist in wikidata?
            pageqid = page.data_item().getID()
            print("DEBUG: Page " + page.title() + " has id: ", pageqid)
            return True
    except:
        print("Failed opening page: ", title ,".")
        return False
        

    if (page == None):
        print("Could not open page: ", title ,".")

    return False

# make page name for checking if article exists for the minor planet
def make_page_name(mpcnum, name, temporary):
    #
    if (len(name) > 0 and mpcnum > 0):
        return "" + str(mpcnum) + " " + name
    elif (mpcnum > 0 and len(temporary) > 0):
        return "(" + str(mpcnum) + ") " + temporary
    else:
        return temporary

# verify that we can get just plain number
def getplainnumber(basenum):
    
    isnumb = True
    l = len(basenum)
    i = 0
    while (i < l):
        #if (isalpha(basenum[i]) == True):
        if (basenum[i].isnumeric() == False):
            # not plain number
            isnumb = False
        
        i = i +1
        
    if (isnumb == True):
        return int(basenum)
    return 0

def processwikilines(oldtext, mpclist):
    pagelen = len(oldtext)

    #print("mpc list has:", len(mpclist))

    #print("DEBUG list: ", mpclist)

    # TODO: additional verifications for table-context (avoid potential templates) ?
        # could verify a line is within a table?
        #ixtablestart = oldtext.find("\n{|", ixline)
        #ixtableend = oldtext.find("\n|}", ixline)
        # verify line is within a table row to avoid confusion with other templates?
        # but row markers may be omitted at end of table.. -> need table parsing?
        #lenrowmarker = len("\n|-")
        #ixrowstart = oldtext.find("\n|-", ixline)
        #if (ixrowstart >= 0):
        #    ixrowend = oldtext.find("\n|-", ixrowstart+lenrowmarker)
    # table column separator checks , temporary name check and line-end check together may suffice ?

    
    ixline = 1
    while (ixline > 0):
       
        lenstart = len("\n| ")
        ixline = oldtext.find("\n| ", ixline)
        if (ixline < 0):
            #print("line start missing or end of file?")
            break
        
        ixlineend = oldtext.find("\n", ixline+2)
        if (ixlineend < 0):
            #print("line end missing or end of file?")
            break

        # should also check that line is within a table
        # and not in some other template? but the articles are simple..
        # skip line with table row
        #if (oldtext[ixline+1] == "-"):
        #    continue

        
        #print("Debug: parsing table line: ", getsubstr(oldtext, ixline+1, ixlineend))
        
        # between number and temporary name
        lenseparator = len("||")
        ixfirst = oldtext.find("||", ixline+2) 
        if (ixfirst < 0 or ixfirst > ixlineend):
            # no more or wrapped around -> bail out
            # might be a table row
            #print("name end separator missing?")
            ixline = ixlineend
            continue
        
        # after temporary name
        ixsecond = oldtext.find("||", ixfirst+2)
        if (ixsecond < 0 or ixsecond > ixlineend):
            # no more or wrapped around -> bail out
            # might be split over multiple lines?
            print("temporary name end separator missing?")
            ixline = ixlineend
            continue

        basename = getsubstr(oldtext, ixline+lenstart, ixfirst)
        tempname = getsubstr(oldtext, ixfirst+lenseparator, ixsecond)
        #print("DEBUG: table row has name: [", basename ,"] tempname::", tempname)

        if (basename.find("|") > 0):
            # wikilink? skip to end of line
            ixline = ixlineend
            #print("DEBUG: skipping line, already named entry")
            continue
        
        if (basename.find("[") > 0 or basename.find("]") > 0):
            # wikilink: just skip
            
            # is it a plain number linked ?
            # these were mostly fixed already?
            # -> no need for this any more
            #tablen = basename.replace("[", "").replace("]", "")
            #plain_base_num = getplainnumber(tablen)
            #if (plain_base_num > 0):
            #    print("DEBUG: plain number in a wikilink? [", tablen ,"] tempname::", tempname)
            #else:
                #print("DEBUG: not a plain number in a wikilink")
            
            # skip to end of line
            ixline = ixlineend
            #print("DEBUG: skipping line, already named entry")
            continue

       
        # might be plain number currently
        basename = basename.lstrip().rstrip()
        tempname = tempname.lstrip().rstrip()

        plain_base_num = getplainnumber(basename)
        if (plain_base_num == 0):
            # not a plain number in the field:
            # if is number with name see if should make a wikilink
            # if there is an article for it
            
            # skip to end of line
            ixline = ixlineend
            continue

        tup_mpc = mpclist.get(plain_base_num)
        if (tup_mpc != None):

            mpc_new_name = tup_mpc[0]
            mpc_temp_name = tup_mpc[1]

            if (mpc_temp_name != tempname):
                print("WARN: temporary name does not match for: [", basename ,"] tempname:", mpc_temp_name)

            # also double check with temporary from table and mpc list
            if (mpc_temp_name == tempname and len(mpc_new_name) > 0):
                print("DEBUG: new name found, temporary name match: [", basename ,"] tempname:", mpc_temp_name)

                # if there is already article with correct name:
                # add link while updating name for it (don't change if in a different name)
                #if (minorplanetexists == True):

                ixbaseend = oldtext.find(" ", ixline+lenstart+len(basename))
                if (ixbaseend > 0 and ixbaseend < ixsecond):
                    # add name if we have found one (parsed from list)
                    print("Adding name for: ", basename , " tempname::", tempname)

                    oldtext = insertat(oldtext, ixbaseend, " ")
                    oldtext = insertat(oldtext, ixbaseend+1, mpc_new_name)
        else:
            print("DEBUG: number not found in list for: [", basename ,"] tempname:", tempname)
                

        # skip to end of line
        ixline = ixlineend

    return oldtext

# / processwikilines()

def addnavtemplateforluettelopage(oldtext, impcnum):
    
    if (impcnum <= 1001):
        # skip
        return oldtext

    if (oldtext.find("{{Edeltäjä-seuraaja") > 0):
        # don't re-add the template
        #print("DEBUG: already had navtemplate")
        return oldtext

    ixfirstcat = oldtext.find("[[Luokka:")
    if (ixfirstcat < 0):
        # no category? -> skip
        return oldtext

    iPrevstart = impcnum-1000
    iPrevend = iPrevstart+999

    iNextstart = impcnum+1000
    iNextend = iNextstart+999
        
    newtemplate = "{{Edeltäjä-seuraaja\n | Edeltäjä = [[Luettelo pikkuplaneetoista: "+ str(iPrevstart) +"–"+ str(iPrevend) +"]]\n | Titteli = [[Luettelo pikkuplaneetoista]]\n | Seuraaja = [[Luettelo pikkuplaneetoista: "+ str(iNextstart) +"–"+ str(iNextend) +"]]\n}}\n"


    return insertat(oldtext, ixfirstcat, newtemplate)

    #return oldtext

# / addnavtemplateforluettelopage()    

def isluettelopage(pagename):
    ix = pagename.find(":")
    if (ix < 0):
        print("no semicolon in name")
        return False

    namepart = pagename[:ix].lower()
    if (namepart.find("luettelo pikkuplaneetoista") < 0):
        print("no basepart in name")
        return False
    return True

def getfirstmpcnumfromluettelotitle(pagename):
    ix = pagename.find(":")
    if (ix < 0):
        print("no semicolon in name")
        return 0
    ixdash = pagename.find("–", ix+1)
    if (ix < 0):
        print("no dash found in name")
        return 0

    mpcnum = getsubstr(pagename, ix+1, ixdash)
    mpcnum = mpcnum.lstrip().rstrip()
    inum = int(mpcnum)
    return inum


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

def getpagebyname(pywikibot, site, name):
    pages = list()
    
    p = pywikibot.Page(site, name)

    pages.append(p)
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

# parse text file from MPC
#
def read_mpc_numberedlist(filename):
    f = open(filename, "r")

    dlist = dict()
    line = f.readline()
    while (line):
        lenline = len(line)
        
        num = getsubstr(line, 0, 8)
        name = getsubstr(line, 8, 32)
        tempname = getsubstr(line, 32, 44)
        ddate = getsubstr(line, 44, 56)
        #dplace = getsubstr(line, 56, 81)
        dplace = getsubstr(line, 56, 75) # there is some number in between, skip it for now
        discoverer = getsubstr(line, 81, lenline-1)
        
        plainnum = num.replace("(", "").replace(")", "")
        plainnum = plainnum.lstrip().rstrip()
        
        imultispaceplace = dplace.rfind("   ")
        if (imultispaceplace > 0):
            dplace = dplace[:imultispaceplace].lstrip().rstrip()
        
        name = name.lstrip().rstrip()
        tempname = tempname.lstrip().rstrip()
        ddate = ddate.lstrip().rstrip()
        dplace = dplace.lstrip().rstrip()
        discoverer = discoverer.lstrip().rstrip()
        
        # make iso-order
        #dplace.replace(" ", "-")

        # must have a name
        #if (len(name) > 0):
            #print("name found for num: [",num,"] name:[",name,"] temp:[",tempname,"]")
            
        mpc_num = getplainnumber(plainnum)
        if (mpc_num > 0):
            dlist[mpc_num] = tuple((name, tempname, ddate, dplace, discoverer))
        #else:
        #    print("no name for num: [",num,"]  temp:[",tempname,"]")
            

        
        line = f.readline()

    f.close()
    return dlist

def mpc_date_to_wiki_date(entry):
    daymons = ["tammikuuta",
              "helmikuuta",
              "maaliskuuta",
              "huhtikuuta",
              "toukokuuta",
              "kesäkuuta",
              "heinäkuuta",
              "elokuuta",
              "syyskuuta",
              "lokakuuta",
              "marraskuuta",
              "joulukuuta"]
    mons = ["tammikuu",
              "helmikuu",
              "maaliskuu",
              "huhtikuu",
              "toukokuu",
              "kesäkuu",
              "heinäkuu",
              "elokuu",
              "syyskuu",
              "lokakuu",
              "marraskuu",
              "joulukuu"]
    
    stryear = ""
    strmon = ""
    strday = ""
    
    ixyearend = entry.find(" ")
    if (ixyearend > 0):
        stryear = getsubstr(entry, 0, ixyearend).lstrip().rstrip()
        ixmonend = entry.find(" ", ixyearend+1)
        if (ixmonend > 0):
            strmon = getsubstr(entry, ixyearend, ixmonend).lstrip().rstrip()
            strday = entry[ixmonend:]
            strday = strday.replace("*", "") # ends with asterisk?
            strday = strday.lstrip().rstrip()
    else:
        stryear = entry.lstrip().rstrip()
    
    if (len(stryear) > 0 and len(strmon) > 0 and len(strday) > 0):
        # strip zero if first character in day
        if (strday[0] == "0"):
            iday = int(strday)
            strday = str(iday)
        imon = int(strmon)-1
        return "" + strday + ". " + daymons[imon] + " " + stryear
    elif (len(stryear) > 0 and len(strmon) > 0):
        imon = int(strmon)-1
        return "" + mons[imon] + " " + stryear
    else:
        return stryear

def get_page_heading_text(istartnum):
    return "Tämä on '''luettelo''' [[Aurinkokunta|Aurinkokunnan]] numeroiduista '''[[pikkuplaneetta|pikkuplaneetoista]]''' numerojärjestyksessä alkaen "+ str(istartnum) +":stä ja päättyen "+ str(istartnum+999) +":een. Kokonaisen luettelon löytää katsomalla [[Luettelo pikkuplaneetoista]].\n\n"

def get_page_ending_text():
    return "==Lähteet==\n*[http://www.minorplanetcenter.org/iau/lists/NumberedMPs.html Discovery Circumstances: Numbered Minor Planets: IAU Minor Planet Center] {{en}}\n\n[[Luokka:Luettelot pikkuplaneetoista]]\n\n"


def generate_wikitable(mpclist, filename=""):

    print("count: ", len(mpclist))
    
    f = None
    if (len(filename) > 0):
        f = open(filename, "w")

    strheaderrow ='! Nimi !! Tilapäinen nimi !! Löytöaika !! Löytöpaikka !! Löytäjä(t)'
    strrowseparator = '|-'
    count = 0
    totals = 0

    it_entry = iter(mpclist)
    k_entry = next(it_entry)
    while (k_entry):
        impcnumber = int(k_entry)
        val_entry = mpclist[k_entry]
        
        #print(val_entry)
        isodate = val_entry[2].replace(" ", "-") # add separator
        isodate = isodate.replace("*", "") # ends with asterisk?
        wikidate = mpc_date_to_wiki_date(val_entry[2])
        
        entryname = ""
        if (len(val_entry[0]) > 0): 
            # has name in addition to mpc number
            entryname = str(k_entry) + " " + val_entry[0]
        else:
            # just mpc number
            entryname = str(k_entry)

        # in some cases there are vertical lines, wikify them
        entryname = entryname.replace('|', '{{!}}')
        temporaryname = val_entry[1].replace('|', '{{!}}')
        location = val_entry[3].replace('|', '{{!}}')
        discoverer = val_entry[4].replace('|', '{{!}}')

        strrowdata = "| "+ entryname +" || "+ temporaryname +" || "+ wikidate +" || "+ location +" || "+ discoverer
        
        print(strrowdata)

        if (f != None):
            if (totals == 0):
                f.write(get_page_heading_text(impcnumber))

            if (count == 0):
                f.write('== ' + str(impcnumber) + '-' + str(impcnumber + 99)  + ' ==\n')
                f.write('{| class="wikitable" \n')
                f.write(strrowseparator + "\n")
                f.write(strheaderrow + "\n")
            
            f.write(strrowseparator + "\n")
            f.write(strrowdata + "\n")

            if (count == 99):
                f.write('|}\n\n')
                count = 0
            else:
                count = count + 1

            if (totals == 999):
                f.write(get_page_ending_text())
                f.write("\n\n ---------------- cut here -------------------- \n\n")
                totals = 0
            else:
                totals = totals + 1


        #it_entry = next(mpclist)
        k_entry = next(it_entry, None)
        if not k_entry:
            break

    #for k, v in mpclist.items():

    if (f != None):
        f.close()

# / generate_wikitable()


def ask_page_save(site):

    choice = ""

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

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

    return choice


def is_restrictions_in_page(pagetext, page):
    if (pagetext.find("#OHJAUS") >= 0 or pagetext.find("#REDIRECT") >= 0):
        print("Skipping ", page.title() ," - redirect-page.")
        return True
    if (pagetext.find("{{bots") > 0 or pagetext.find("{{nobots") > 0):
        print("Skipping ", page.title() ," - bot-restricted.")
        return True
    return False

def get_existing_page(site, title):

    # note: what to do with redirect page?
    # 
    try:
        # What happens if page does not exist yet?
        page = pywikibot.Page(site, title)
        
        # is None returned?
        if (page != None):
            # might throw exception if page does not exist in wikidata?
            pageqid = page.data_item().getID() 
            print("DEBUG: Page " + page.title() + " has id: ", pageqid)
            return page
    except:
        print("Failed opening page: ", title ,".")
        return None
        

    if (page == None):
        print("Could not open page: ", title ,".")

    return None


# update articles
def add_article_sorting_and_categories(mpclist):

    site = pywikibot.Site("fi", "wikipedia")
    site.login()

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    commitall = False

    it_entry = iter(mpclist)
    k_entry = next(it_entry)
    while (k_entry):
        impcnumber = int(k_entry)
        val_entry = mpclist[k_entry]

        entryname = ""
        if (len(val_entry[0]) > 0): 
            # has name in addition to mpc number
            entryname = str(k_entry) + " " + val_entry[0]
        else:
            # mpc number + temporary name
            entryname = "(" + str(k_entry) + ") " + val_entry[1]
        
        print("DEBUG: looking for article: ", entryname)
        
        # check if page exists
        page = get_existing_page(site, entryname)
        if (page == None):
            print("Could not open page: ", entryname ,".")

            k_entry = next(it_entry, None)
            continue
        
        oldtext = page.text
        
        if (is_restrictions_in_page(page.text, page) == True):
            print("Skipping ", page.title() ,".")

            k_entry = next(it_entry, None)
            continue

        if (hassorting(oldtext) == True and isincategory(oldtext) == True):
            print("Skipping ", page.title() ," - has sorting and category.")

            k_entry = next(it_entry, None)
            continue
        
        # get entity id of page
        pageqid = page.data_item().getID()
        print("Page " + page.title() + " has id: ", pageqid)

        # try to get MPC number from wikidata:
        # if it does not have one -> only temporary identification 
        mpcnumber = checkwikidata(wdsite, pageqid)
        if (mpcnumber == None):
            print("Skipping page: ", page.title() ," - not suitable type or no MPC number.")

            k_entry = next(it_entry, None)
            continue

        temptext = oldtext

        summary='Lisätään luokittelu ja aakkostus'
        temptext = parsenameaddcat(temptext, mpcnumber, page.title())
        
        if oldtext == temptext:
            print("Skipping. ", page.title() ," - old and new are equal.")

            k_entry = next(it_entry, None)
            continue

        pywikibot.info('----')
        pywikibot.showDiff(oldtext, temptext,2)
        pywikibot.info('Edit summary: {}'.format(summary))

        if (commitall == True):
            page.text = temptext
            page.save(summary)
        else:

            choice = ask_page_save(site)

            if choice == 'q':
                print("Asked to exit. Exiting.")
                exit()

            if choice == 'a':
                commitall = True

            if choice == 'y' or choice == 'a':
                page.text = temptext
                page.save(summary)


        k_entry = next(it_entry, None)
        if not k_entry:
            break

# / add_article_sorting_and_categories()

## main()

# sys.argv -> find --dump

# read numbered list from file:
# use local list to avoid overloading the mpc servers..
#
mpclist = read_mpc_numberedlist("NumberedMPs.txt")

print("mpc list has:", len(mpclist))

#generate_wikitable(mpclist, "002-Gen-Numbered-MPC-list-into-wikitable.text")
#exit(1)

# sys.argv -> find --catupdate
#add_article_sorting_and_categories(mpclist)
#exit(1)



# sys.argv -> find --listupdate

site = pywikibot.Site("fi", "wikipedia")
site.login()

#wdsite = pywikibot.Site('wikidata', 'wikidata')
#wdsite.login()



#pages = getpagesrecurse(pywikibot, site, "Luettelot pikkuplaneetoista", 0)

pages = getnewestpagesfromcategory(pywikibot, site, "Luettelot pikkuplaneetoista", 50)


rivinro = 1
commitall = False

for page in pages:
    # skip user-pages, only main article namespace
    if (page.namespace() != 0):  
        print("Skipping ", page.title() ," - wrong namespace.")
        continue

    oldtext = page.text

    print(" ////////", rivinro, "/", len(pages), ": [ " + page.title() + " ] ////////")
    rivinro += 1

    if (is_restrictions_in_page(page.text, page) == True):
        print("Skipping ", page.title() ,".")
        continue

    if (isluettelopage(page.title()) == False):
        print("Skipping ", page.title() ," - not listpage.")
        continue

    temptext = oldtext
    summary = ""

    # note: might be better to query potential articles to link with
    # earlier in case pywikibot confuses edit context?

    temptext = processwikilines(temptext, mpclist)
    if (temptext != oldtext):
        summary = 'Päivitetään luetteloa Minor Planet Centerin luettelon mukaan (ladattu: https://www.minorplanetcenter.net/iau/lists/NumberedMPs.html)'

    # these were fixed already, not needed
    #temptext = temptext.replace("{{en}}}", "{{en}}")
    #if (temptext != oldtext and len(summary) == 0):
    #    summary += 'Korjataan kielimalline'

    ipagempcnum = getfirstmpcnumfromluettelotitle(page.title())
    if (ipagempcnum == 0):
        print("Could not find first number in", page.title() ,".")
        #continue
    else:
        #print("DEBUG: First number is: ", ipagempcnum, " in: ", page.title() ,".")
        temptext = addnavtemplateforluettelopage(temptext, ipagempcnum)
        if (temptext != oldtext and len(summary) == 0):
            summary += 'Lisätään navigaatiomalline'

    
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
        #print("commitall not enabled currently.")
        page.text = temptext
        page.save(summary)
    else:

        choice = ask_page_save(site)

        if choice == 'q':
            print("Asked to exit. Exiting.")
            exit()

        if choice == 'a':
            commitall = True

        if choice == 'y' or choice == 'a':
            #print("saving not enabled currently.")
            page.text = temptext
            page.save(summary)

