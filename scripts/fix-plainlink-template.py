# Purpose: fix plain wikilink to use a template for a reference
#
#
# Running script: 
#

import pywikibot
import json
from urllib.request import urlopen

from datetime import datetime


def findch(text, char, begin, end):
    if (end < begin):
        return -1

    i = begin
    while (i < end):
        ch = text[i]
        
        if (ch == char):
            return i
        i += 1
    return -1

def rfindch(text, char, begin, end):
    if (end < begin):
        return -1

    i = end-1
    while (i >= begin):
        ch = text[i]
        
        if (ch == char):
            return i
        i -= 1
    return -1

def getsubstr(text, begin, end):
    if (end < begin):
        return -1 # terminate with forced error on bug
    return text[begin:end]


# python has bizarre syntax, avoid it
def joinliststr(l):
    if (len(l) < 1):
        return ""

    s = ""
    for i in l:
        s += i
    return s

# check if there is a template within given block:
# skip changes to avoid mistakes if there is
#
# we don't want to parse if there is reference template,
# but we can handle language templates
#
def hastemplatewithin(text, reftagopen, reftagclose):

    #print("DEBUG: searching for template in ref, begin", reftagopen, "end", reftagclose)

    # note: there could be multiple templates
    hasunkowntemplate = False

    inextindex = reftagopen
    while (inextindex < reftagclose and inextindex >= 0):
        iprevindex = inextindex

        # there may be multiple templates
        #index = text.find("{{", previndex)
        iopenbrace = findch(text, "{", inextindex, reftagclose)
        if (iopenbrace < 0):
            # no more templates? skip to end
            #print("DEBUG: no more template(s) in ref")
            return hasunkowntemplate
        if (getsubstr(text, iopenbrace, iopenbrace+1) != "{{"):
            #print("DEBUG: not double open brace, not template")
            return hasunkowntemplate
        
        #indexend = text.find("}}", index)
        iclosebrace = findch(text, "}", iopenbrace, reftagclose)
        if (iclosebrace < 1):
            # malformed?
            print("DEBUG: no ending braces in ref?")
            return hasunkowntemplate
        if (getsubstr(text, iclosebrace, iclosebrace+1) != "}}"):
            print("DEBUG: not double close brace, not correctly formed template?")
            return hasunkowntemplate

        if (iclosebrace < iopenbrace):
            print("DEBUG: template ending before beginning?")
            return hasunkowntemplate
            
        # if there is a space, try to parse template name
        ispace = findch(text, " ", iopenbrace+2, iclosebrace)
        # if there is a pipe, try to parse template name
        ipipe = findch(text, "|", iopenbrace+2, iclosebrace)
        
        # no paramters, could be simple language template
        # -> we can use this
        if (ispace < 1 and ipipe < 1):
            tmpname = getsubstr(text, iopenbrace+2, iclosebrace)
            # note: could be short like {{lähde}} -> check
            #if (tmpname == "en" or tmpname == "sv" or tmpname == "de" or tmpname == "fr"):
            if (issupportedlangsymbol(tmpname) == True):
                hasunkowntemplate = False
            print("DEBUG: short template in ref?", tmpname)

            inextindex = iclosebrace
        elif (ispace > 1 and ispace < ipipe):
            tmpname = getsubstr(text, iopenbrace+2, ispace)
            print("DEBUG: template in ref (space)", tmpname)
            return True
        elif (ipipe > 1 and ipipe < ispace):
            tmpname = getsubstr(text, iopenbrace+2, ipipe)
            print("DEBUG: template in ref (pipe)", tmpname)
            return True
        else:
            # full template? (no space or pipe after name?)
            tmpname = getsubstr(text, iopenbrace+2, indexend)
            print("DEBUG: template in ref", tmpname)
            return True

    # maybe found a template, or maybe it was a supported one
    if (hasunkowntemplate == True):
        print("DEBUG: still unparsed template in reference")
    #else:
        #print("DEBUG: all templates parsed in reference")
    return hasunkowntemplate


# check for valid protocl
def checkforurlprotocol(text, begin, end):
    
    iproto = begin
    while (iproto < end):
        ch = text[iproto]
        
        if (ch == ":"):
            sproto = text[begin:iproto]
            if (sproto == "http" or sproto == "https"):
                #print("DEBUG: found valid protocol in url", sproto)
                return True
            if (sproto != "http" and sproto != "https"):
                # not a valid protocol
                print("DEBUG: not a valid protocol in url, skipping", sproto)
                return False

        iproto += 1
        
    #if (iproto >= end):
        # did not find protocol
    return False

# check that there is an url and find end (space)
def checkforurl(text, begin, end):
    
    if (checkforurlprotocol(text, begin, end) == False):
        print("DEBUG: could not find protocol")
        return -1
    
    ispace = begin
    while (ispace < end):
        ch = text[ispace]

        # something is wrong? unexpected charater in the link?
        # some websites may use these on search parameters..
        #if (ch == "|" or ch == "]" or ch == "<"):
        #if (ch == "|"):
            #return -1
        
        # search for newline or tabulator as well, whichever comes first:
        # if there are other characters not allowed in an url could stop there
        #if (ch == " "):
        if (ch == " " or ch == "\n" or ch == "\t"):
            #print("DEBUG: found url", getsubtr(text, begin, ispace))
            return ispace

        ispace += 1

    print("DEBUG: no space to separate url from text in link?")
    return -1

# get plain domain from url for further checks
def getdomainfromurl(text, begin, end):
    ixsep = text.find("://", begin)
    if (ixsep < 0 or ixsep > end):
        return ""
    ixsep = ixsep + len("://")
    idomend = findch(text, "/", ixsep, end)
    if (idomend < 0 or idomend > end):
        return ""
    
    domain = getsubstr(text, ixsep, idomend)
    print("DEBUG: domain from url", domain)
    if (domain[:4] == "www."):
        domain = domain[:4]
    return domain
    

# remove pre- and post-whitespaces when mwparser leaves them
def trimlr(string):
    if (len(string) < 1):
        return string
    string = string.lstrip()
    string = string.rstrip()
    return string

def beginswithcommaordot(text):
    if (len(text) < 1):
        return False
    ch = text[0]
    if (ch == ","):
        return True
    if (ch == "."):
        return True
    return False

def endswithcommaordot(text):
    if (len(text) < 1):
        return False
    ch = text[len(text)-1]
    if (ch == ","):
        return True
    if (ch == "."):
        return True
    return False

def removefirstchar(text):
    if (len(text) > 0):
        return text[1:]
    return text

def removelastchar(text):
    if (len(text) > 0):
        return text[:len(text)-1]
    return text

def removeprepostslash(text):
    if (len(text) < 1):
        return text

    ch = text[len(text)-1]
    if (ch == "/"):
        text = removelastchar(text)
        
    ch = text[0]
    if (ch == "/"):
        text = removefirstchar(text)
    return text


# note: only to be used for changing "1. tammikuuta 2025" into "1.1.2025"
def numerizemonth(timestring):
    # only modify if known plain text
    if (timestring.find("tammikuuta") > 0):
        timestring = timestring.replace("tammikuuta", "1.")
        return timestring.replace(" ", "")
    if (timestring.find("helmikuuta") > 0):
        timestring = timestring.replace("helmikuuta", "2.")
        return timestring.replace(" ", "")
    if (timestring.find("maaliskuuta") > 0):
        timestring = timestring.replace("maaliskuuta", "3.")
        return timestring.replace(" ", "")
    if (timestring.find("huhtikuuta") > 0):
        timestring = timestring.replace("huhtikuuta", "4.")
        return timestring.replace(" ", "")
    if (timestring.find("toukokuuta") > 0):
        timestring = timestring.replace("toukokuuta", "5.")
        return timestring.replace(" ", "")
    if (timestring.find("kesäkuuta") > 0):
        timestring = timestring.replace("kesäkuuta", "6.")
        return timestring.replace(" ", "")
    if (timestring.find("heinäkuuta") > 0):
        timestring = timestring.replace("heinäkuuta", "7.")
        return timestring.replace(" ", "")
    if (timestring.find("elokuuta") > 0):
        timestring = timestring.replace("elokuuta", "8.")
        return timestring.replace(" ", "")
    if (timestring.find("syyskuuta") > 0):
        timestring = timestring.replace("syyskuuta", "9.")
        return timestring.replace(" ", "")
    if (timestring.find("lokakuuta") > 0):
        timestring = timestring.replace("lokakuuta", "10.")
        return timestring.replace(" ", "")
    if (timestring.find("marraskuuta") > 0):
        timestring = timestring.replace("marraskuuta", "11.")
        return timestring.replace(" ", "")
    if (timestring.find("joulukuuta") > 0):
        timestring = timestring.replace("joulukuuta", "12.")
        return timestring.replace(" ", "")
    
    return timestring

# check if given text is a valid date
def isvaliddate(timestring):
    if (len(timestring) < 2):
        return False

    # remove dot at end if any
    #if (timestring.endswith(".")):
    #    timestring = timestring[:len(timestring)-1]
    #timestring = trimlr(timestring)

    if (endswithcommaordot(timestring) == True):
        timestring = removelastchar(timestring)

    print("DEBUG: parsing timestamp", timestring)

    try:
        # month in plain text instead of number?
        if (timestring.find('.') > 0): 
            timestring = numerizemonth(timestring)
            print("DEBUG: numerized timestamp", timestring)
        
        if (timestring.find('.') > 0): 
            dt = datetime.strptime(timestring, '%d.%m.%Y')
            return True

        # ISO-format might be acceptable as well
        if (timestring.find('-') > 0): 
            dt = datetime.strptime(timestring, '%Y-%m-%d')
            return True
    except:
        print("failed to parse timestamp")
        return False

    print("DEBUG: cannot use timestamp", timestring)
    return False

# is it a known keyword for access date:
# people have been using different strings in free-form
def isaccesskeyword(text):
    if (len(text) < 1):
        return False

    text = text.strip()
    if (text == "Haettu" or text == "haettu" 
        or text =="Luettu" or text =="luettu" 
        or text == "Viitattu" or text == "viitattu"):
        return True
    return False

# check text after link if there is an access date
# if something else return error or nothing
def parseaccessdateafterlink(text):
    
    # preceding spaces? nothing but spaces remining?
    text = trimlr(text)
    if (len(text) < 1):
        return ""

    # sulut ennen ja jälkeen?
    if (text[0] == "(" and text[len(text)-1] == ")"):
        print("DEBUG: removing parentheses from", text)
        text = getsubstr(text, 1, len(text)-1)
        

    # should have at least one space for a keyword
    ispace = text.find(" ")
    if (ispace < 0):
        return ""

    # get keyword only to verify it is known
    s = text[:ispace]

    # "Haettu", "Luettu" or "Viitattu":
    # returns nothing if not formatted as expected,
    # only if all after link is for this (nothing extra)

    # is there a valid timestamp after this?
    # must be known word immediately
    if (isaccesskeyword(s) == True):
        print("DEBUG: accessdate after link?", text)

        sdate = text[ispace+1:] # only after space

        # if string ends with a dot -> remove it
        if (sdate[len(sdate)-1] == "."):
            sdate = sdate[:len(sdate)-1]
        sdate = trimlr(sdate)
            
        # also check it is a valid date, otherwise don't use it:
        # might have something else there
        if (isvaliddate(sdate) == True):
            print("DEBUG: found accessdate ", sdate)
            return sdate
    else:
        print("DEBUG: something unkown after link? can't parse", text)
        
    return ""


def issupportedlangtemplate(langtemp):
    if (len(langtemp) < 1):
        return False
    
    if (beginswithcommaordot(langtemp) == True):
        langtemp = removefirstchar(langtemp)
    if (endswithcommaordot(langtemp) == True):
        langtemp = removelastchar(langtemp)
    
    langtemp = langtemp.lower()
    if (langtemp == "{{en}}" 
        or langtemp == "{{sv}}" 
        or langtemp == "{{fi}}" 
        or langtemp == "{{de}}" 
        or langtemp == "{{fr}}"
        or langtemp == "{{es}}" 
        or langtemp == "{{no}}" 
        or langtemp == "{{da}}" 
        or langtemp == "{{nl}}"
        or langtemp == "{{pt}}"
        or langtemp == "{{pl}}"
        or langtemp == "{{ko}}"
        or langtemp == "{{ja}}"):
        return True
    return False

def cleanuplangtemplate(temp):
    if (len(langtemp) < 1):
        return ""

    if (beginswithcommaordot(temp) == True):
        temp = removefirstchar(temp)
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)

    # get symbol without braces
    if (len(temp) > 4):
        if (temp[:2] == "{{" and temp[len(temp)-2:] == "}}"):
            temp = getsubstr(temp, 2, len(temp)-2)
    return temp.lower()

def issupportedlangsymbol(langtemp):

    # simplify to just symbol without braces
    lsymbol = cleanuplangtemplate()
    if (langtemp == "en" 
        or langtemp == "sv" 
        or langtemp == "fi" 
        or langtemp == "de" 
        or langtemp == "fr"
        or langtemp == "es" 
        or langtemp == "no"
        or langtemp == "da"
        or langtemp == "nl"
        or langtemp == "pt"
        or langtemp == "pl"
        or langtemp == "ko"
        or langtemp == "ja"):
        return True
    return False

# cleanup these and convert to symbols
def getsymbolfromplaintextlanguage(langtemp):
    if (len(langtemp) < 2):
        return ""

    #print("DEBUG: parsing lang symbol from text", langtemp)
    
    if (endswithcommaordot(langtemp) == True):
        langtemp = removelastchar(langtemp)

    if (langtemp[0] == "(" and langtemp[len(langtemp)-1] == ")"):
        #print("DEBUG: removing parentheses from", langtemp)
        langtemp = getsubstr(langtemp, 1, len(langtemp)-1)
    else:
        # something else there? part of some explanation?
        # if so, skip this, it might not be meant as language indication
        return ""
    
    if (langtemp == "englanniksi"):
        return "en"
    if (langtemp == "ruotsiksi"):
        return "sv"
    if (langtemp == "ruots."):
        return "sv"
    if (langtemp == "hollanniksi"):
        return "nl"
    if (langtemp == "saksaksi"):
        return "de"
    if (langtemp == "espanjaksi"):
        return "es"
    if (langtemp == "ranskaksi"):
        return "fr"
    if (langtemp == "norjaksi"):
        return "no"
    if (langtemp == "tanskaksi"):
        return "da"
    if (langtemp == "portugaliksi"):
        return "pt"
    if (langtemp == "puolaksi"):
        return "pl"
    if (langtemp == "koreaksi"):
        return "ko"
    if (langtemp == "japaniksi"):
        return "ja"
    return ""


def isplaintextlanguagetext(langtemp):
    #print("DEBUG: testing lang symbol from text", langtemp)

    symbol = getsymbolfromplaintextlanguage(langtemp)
    if (symbol != ""):
        print("DEBUG: found lang symbol ", symbol ," from text", langtemp)
        return True
    return False
    

def isdeadlinktemplate(temp):
    
    # skip
    #if (temp == "{{Wayback".. ): 

    # note: may be : {{vanhentunut linkki | IntenetArchiveBot }}
    #{{Vanhentunut linkki|bot=InternetArchiveBot }}
    #if (temp == "{{Vanhentunut linkki|bot=InternetArchiveBot }}" or temp == "{{Vanhentunut linkki|bot=InternetArchiveBot}}"):
    #    return True

    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)

    temp = temp.lower()
    
    if (temp == "{{404}}" or temp == "{{vanhentunut linkki}}"  or temp == "{{kuollut linkki}}" 
        or temp == "{{dead link}}"  or temp == "{{deadlink}}" ):
        return True
    return False

def iswaybacktemplate(temp):
    #if (temp.find("{{Wayback") == 0 or temp.find("{{wayback") == 0):
    if (temp.find("{{Wayback") == 0):
        return True
    return False

def getarclinkfromwaybacktemplate(temp, begin, end):
    if (len(temp) < 4):
        return ""

    print("DEBUG: parsing wayback template", getsubstr(temp, begin, end))

    #begin = 0
    #end = len(temp)
    #if (temp[len(temp)-2:] != "}}"):
        # seek backwards to where template ends?
    if (temp[:2] == "{{"):
        begin = begin+2
    if (temp[len(temp)-2:] == "}}"):
        end = end-2

    # TODO: check if there are more braces between
    # since having other templates would mess up the parsing below
        
    parsedpars = dict()
    i = begin
    iparpos = 0
    while (i < end):
        #prevpos = i
        
        # start of one par
        ipipe = findch(temp, "|", i, end)
        if (ipipe < 0):
            # no more pars
            #print("DEBUG: no more pipes")
            break

        # start of next par or end
        inextpipe = findch(temp, "|", ipipe+1, end)
        if (inextpipe < ipipe or inextpipe > end):
            # no more pars, end at end of template
            inextpipe = end
        
        # equal between:
        # make sure there is no pipe in between (keyed, not positional)
        iequal = findch(temp, "=", ipipe, inextpipe)
        if (iequal > 0 and iequal < inextpipe):
            keyword = getsubstr(temp, ipipe+1, iequal)
            value = getsubstr(temp, iequal+1, inextpipe)
            print("DEBUG: found key:", keyword, ";value:", value)
            
            # there may be spaces in between parameters/separators so remove them
            keyword = keyword.strip()
            value = value.strip()
            parsedpars[keyword] = value

            iparpos = iparpos+1
        else:
            print("DEBUG: no equal sign, positional parameter?", iparpos)
            # use position as key in this case?
            # template uses always first as url (1=)
            iparpos = iparpos+1

        i = ipipe +1

    print("DEBUG: parsed template to pars", parsedpars)

    oldlink = ""
    datum = ""
    if "1" in parsedpars and oldlink == "":
        oldlink = parsedpars["1"]
    if "osoite" in parsedpars and oldlink == "":
        oldlink = parsedpars["osoite"]
    if "URL" in parsedpars and oldlink == "":
        oldlink = parsedpars["URL"]

    if "päiväys" in parsedpars and datum == "":
        datum = parsedpars["päiväys"]

    #if "2" in parsedpars and datum == "":
    #    title = parsedpars["2"]
    #if "nimeke" in parsedpars and datum == "":
    #    title = parsedpars["nimeke"]
    #if "Arkistoitu" in parsedpars and datum == "":
    #    title = parsedpars["Arkistoitu"]

    if (oldlink != "" and datum != ""):
        
        #if (datum[len(datum)-1]) == "/"):
        #    arclink = "https://web.archive.org/web/" + datum + oldlink
        #else
        datum = removeprepostslash(datum)

        arclink = "https://web.archive.org/web/" + datum + "/" + oldlink

        print("DEBUG: generated arc link", arclink)
        return arclink

    print("DEBUG: could not parse wayback template")
    return ""
    

# template requesting for a fix to reference? leave it as-is
def isfixrequesttemplate(temp):
    
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)

    temp = temp.lower()

    #if tmp == "{{Lähde tarkemmin}}" or tmp == "{{Parempi lähde}}"
    
    if (temp == "{{lähde tarkemmin}}"
        or temp == "{{parempi lähde}}" ):
        return True
    return False


def ispagelist(temp):
    # only if it starts with this and has space after?
    if (temp == "s." or temp == "S." or temp == "sivut"):
        return True
    return False

# scan for end of page list,
# stop if there is something that should not be there
def scanpagelistend(text, begin, end):
    if (end < begin):
        return -1

    i = begin
    while (i < end):
        ch = text[i]
        
        #print("DEBUG: page ch", ch)

        # note: we can't rely on dot as ending,
        # sometimes comma is used as separator and ending both,
        # so we can't detect end by that itself..
        
        # ok, this might be end of list?
        if (ch == "."):
            return i
        if (ch == "," or ch == "-"):
            # comma and dash are allowed as separators
            i += 1
            continue
        if (ch.isnumeric() == True):
            # numbers are allowed of course
            i += 1
            continue
        
        # stop before this:
        # textual character?
        # but some parts of books may have roman numerals as page numbers..
        # - less common case perhaps?
        if (ch.isalpha() == True):
            return i-1
        
        i += 1
    # no ending character? just ends at end of reference?
    return i


def issupportedfileformat(temp):
    if (beginswithcommaordot(temp) == True):
        temp = removefirstchar(temp)
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)
        
    if (temp == "(PDF)" or temp == "(pdf)"):
        return True
    return False

def cleanupfileformat(temp):
    if (beginswithcommaordot(temp) == True):
        temp = removefirstchar(temp)
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)

    if (len(temp) > 2):
        if (temp[0] == "(" and temp[len(temp)-1] == ")"):
            print("DEBUG: removing parentheses from", temp)
            temp = getsubstr(temp, 1, len(temp)-1)
        
    return temp

def cleanupdatestr(temp):
    if (endswithcommaordot(temp) == True):
        return removelastchar(temp)
    return temp

# TODO: if there is a bug or a mistake, needs special handling?
# opens without closing -> needs next token
def isopeningtoken(temp):
    if (len(temp) < 1):
        return False
    
    if (len(temp) > 1):
        if (temp[0] == '(' and temp[len(temp)-1] != ')'):
            return True
        if (temp[0] == '"' and temp[len(temp)-1] != '"'):
            return True

    if (len(temp) > 2):
        if (temp[:2] == "''" and temp[len(temp)-2:] != "''"):
            return True
        if (temp[:2] == "{{" and temp[len(temp)-2:] != "}}"):
            return True
    return False

def isclosingtoken(temp):
    if (len(temp) < 1):
        return False
    
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)
    
    if (len(temp) > 1):
        if (temp[len(temp)-1] == ')'):
            return True
        if (temp[len(temp)-1] == '"'):
            return True

    if (len(temp) > 2):
        if (temp[len(temp)-2:] == "''"):
            return True
        if (temp[len(temp)-2:] == "}}"):
            return True
    return False

def stripopenclose(temp):
    if (len(temp) < 1):
        return temp
    
    if (endswithcommaordot(temp) == True):
        temp = removelastchar(temp)

    if (len(temp) > 1):
        if (temp[0] == '(' and temp[len(temp)-1] == ')'):
            return getsubstr(temp, 1, len(temp)-1)
        if (temp[0] == '"' and temp[len(temp)-1] == '"'):
            return getsubstr(temp, 1, len(temp)-1)

    if (len(temp) > 2):
        if (temp[:2] == "''" and temp[len(temp)-2:] == "''"):
            return getsubstr(temp, 2, len(temp)-2)
        if (temp[:2] == "{{" and temp[len(temp)-2:] == "}}"):
            return getsubstr(temp, 2, len(temp)-2)
    return temp


# parse what is found after link
#
# we don't know how spaces are used: maybe there are dots or commas as hints,
# maybe there are spaces in timestamps.
#
# we can look for keyword for accessdate as that is pretty common and use that as a hint
#
def parseafterlink(text, urldomain, begin, end):

    # is there dor or comma immediately at the beginning?
    #if (beginswithcommaordot(text) == True):
    #    begin = begin +1
    #    text = removefirstchar(text)

    # is there dot or comma at end? remove it
    #if (endswithcommaordot(text) == True):
    #    end = end -1
    #    text = removelastchar(text)

    if (end < begin):
        return None
    if ((end-begin) < 1):
        return None

    # final list to parse into
    parselist = dict()

    # after link may commonly have:
    # - publisher, access date, language
    # - language, access date (this order)
    # - access date, language (this order)
    # - fileformat (usually last)
    # - plain date (usually before access date)
    # s. <number>, <number> as pages in some cases..
    # "{{Wayback"
    # is there something else between access date and link?
    # it could be publisher, site or other
    
    # cursive tags? -> publisher/site
    # dot or comma as separator? or just plain space?

    # TODO: remove recognized parts even if we have 
    # to leave unrecognized things in between?

    # make a semi-tokenized list for special cases
    tmplist = list()
    indexsrc = begin
    openingtoken = -1
    accessfound = -1
    parsingstoppedat = indexsrc
    #nokeyword = True # try to detect freeform "as-is" stuff
    while (indexsrc < end and indexsrc > 0):
        previndex = indexsrc
        
        # if we are pointing at space just increment so python doesn't stall on it
        if (text[previndex] == " "):
            #previndex = previndex+1
            indexsrc = indexsrc+1
            continue
        if (previndex == end):
            # end here
            parsingstoppedat = previndex
            break

        # find next space
        indexsrc = text.find(" ", previndex)
        ixnext = end # stop at end of reference by default (if there wasn't a space)
        ixtmpend = end
        if (indexsrc > 0 and indexsrc < end):
            # found another separator (space) before the end of this reference
            ixtmpend = indexsrc
            ixnext = indexsrc +1 # skip space and continue
         
        # TODO:
        # only one character remains?
        #if (indexsrc > 0 and (end-indexsrc) < 2):
        # if there are nothing but spaces remaining, check ending pos (all consumed)
        # 

        tmp = getsubstr(text, previndex, ixtmpend)
        tmp = tmp.strip()
        
        if (iswaybacktemplate(tmp) == True):
            # not expecting useful stuff now (although there may be after)
            # note: there might be spaces between template parameters..
            waybackend = text.find("}}", previndex)
            if (waybackend > previndex and waybackend < end):
                arclink = getarclinkfromwaybacktemplate(text, previndex, waybackend)
                if (arclink != ""):
                    parselist["arkisto"] = arclink

                    indexsrc = waybackend+2
                    parsingstoppedat = waybackend+2
                    continue

            # something went wrong with parsing, stop here
            parsingstoppedat = previndex
            break

        # see case with opening/closing tokens
        #if tmp == "{{Lähde tarkemmin}}" or tmp == "{{Parempi lähde}}"

        # skip rest if this is known
        if (issupportedlangtemplate(tmp) == True):
            if (endswithcommaordot(tmp) == True):
                tmp = removelastchar(tmp)
            parselist["lang"] = tmp
            indexsrc = ixnext
            parsingstoppedat = ixtmpend
            continue
        # see also case with parentheses
        if (isplaintextlanguagetext(tmp) == True):
            print("found plain text language", tmp, "converting to template")
            tmp = getsymbolfromplaintextlanguage(tmp)
            
            # skip this if there is already another one found?
            #if "lang" not in parselist:
            
            parselist["lang"] = "{{" + tmp + "}}"
            indexsrc = ixnext
            parsingstoppedat = ixtmpend
            continue
        if (isdeadlinktemplate(tmp) == True ):
            parselist["vanhentunut"] = "kyllä"
            indexsrc = ixnext
            parsingstoppedat = ixtmpend
            continue
        if (issupportedfileformat(tmp) == True):
            parselist["fileformat"] = cleanupfileformat(tmp)
            indexsrc = ixnext
            parsingstoppedat = ixtmpend
            continue
        
        # might be a list of pages, maybe comma-separated, maybe dashed
        # detect somehow where it ends, expected a dot?
        # starts with S. or s. and ends with a dot?
        # unless there is something else before then?
        if (ispagelist(tmp) == True):
            print("DEBUG: scanning for page list")
            # try to find dot in the reference:
            # scan past the "token"
            # must detect other characters not part of this
            # in case it does not end with dot: dot may have been stripped long before
            # note: there might not be no numbers after s.
            dotpos = scanpagelistend(text, ixtmpend+1, end)
            if (dotpos > 0 and dotpos > ixtmpend and dotpos <= end):
                # TODO: position before start?
                #if ((dotpos-ixtmpend) > 0)
                tmp = getsubstr(text, ixtmpend+1, dotpos)
                tmp = tmp.strip()
                parselist["pages"] = tmp

                print("DEBUG: using page list:", tmp)
                
                # note that we skip ahead of normal parsing here
                indexsrc = dotpos
                parsingstoppedat = dotpos
            else:
                # otherwise, use up until end?
                print("DEBUG: no end for page list?")
            continue

        # starts with a known keyword..
        # note: check for when this is within parentheses
        if (isaccesskeyword(tmp) == True and accessfound < 0):
            accessfound = previndex+len(tmp)
            continue
        # might be separated by spaces..
        if (accessfound >= 0):
            tmp = getsubstr(text, accessfound, ixtmpend)
            tmp = tmp.strip()
            if (isvaliddate(tmp) == True):
                parselist["accessdate"] = cleanupdatestr(tmp)
                accessfound = -1
                parsingstoppedat = ixtmpend
            continue

        # has both opening and closing in same (no spaces?)
        # website/publication name?
        if (isopeningtoken(tmp) == True and isclosingtoken(tmp) == True and openingtoken < 0):
            if (len(tmp) > 0):
                tmplist.append(tmp)
            indexsrc = ixnext
            parsingstoppedat = indexsrc
            continue

        if (isopeningtoken(tmp) == True and openingtoken < 0):
            openingtoken = previndex
            print("DEBUG: opening token:", tmp)
            continue
        if (isclosingtoken(tmp) == False and openingtoken >= 0):
            indexsrc = ixnext
            continue
        if (isclosingtoken(tmp) == True and openingtoken >= 0):
            # get full string
            print("DEBUG: closing token:", tmp)
            tmp = getsubstr(text, openingtoken, ixtmpend)
            tmp = tmp.strip()

            accessdate = parseaccessdateafterlink(tmp)
            if (len(accessdate) > 0):
                print("DEBUG: using access date", accessdate)
                parselist["accessdate"] = cleanupdatestr(accessdate)
                
            elif (isplaintextlanguagetext(tmp) == True):
                tmp = getsymbolfromplaintextlanguage(tmp)
                parselist["lang"] = tmp
                
            # begins with cursive markup? might have journal, website or such?
            elif (len(tmp) > 2 and tmp[:2] == "''" and "publication" not in parselist):
                print("DEBUG: using publication", tmp)
                if (endswithcommaordot(tmp) == True):
                    tmp = removelastchar(tmp)
                parselist["publication"] = tmp
            else:
                print("DEBUG: full token:", tmp)

                # maybe a case where template name has space..
                if (isdeadlinktemplate(tmp) == True ):
                    parselist["vanhentunut"] = "kyllä"
                    indexsrc = ixnext
                    parsingstoppedat = ixnext
                    openingtoken = -1
                    continue

                # break, don't change these, don't append to conversion list
                #if tmp == "{{Lähde tarkemmin}}" or tmp == "{{Parempi lähde}}"
                if (isfixrequesttemplate(tmp) == True):
                    print("DEBUG: found template for requesting fix, stopping parsing", tmp)
                    break

                if (len(tmp) > 0):
                    tmplist.append(tmp)
            openingtoken = -1
            indexsrc = ixnext
            parsingstoppedat = ixnext
            continue

        # a plain date that isn't within any other scope?
        if (isvaliddate(tmp) == True and accessfound < 0 and openingtoken < 0):
            parselist["date"] = cleanupdatestr(tmp)
            indexsrc = ixnext
            parsingstoppedat = ixnext
            continue

        # if there is domain from url after the link,
        # we can skip duplicating it: reference template can parse it again anyway
        tmpdomain = tmp.lower()
        if (endswithcommaordot(tmpdomain) == True):
            tmpdomain = removelastchar(tmpdomain)
        if (tmpdomain == urldomain.lower() and accessfound < 0 and openingtoken < 0):
            print("DEBUG: url domain found after link:", tmp)
            indexsrc = ixnext
            parsingstoppedat = ixnext
            continue
            

        # note: we can't use this, there is often some string like publication
        # without anything at end, followed by year or something..
        #
        # not within some other section, try to look for dot as ending
        # instead of just space: seek forward
        #if (accessfound < 0 and openingtoken < 0):
        #    dotpos = findch(text, ".", ixtmpend+1, end)
        #    commapos = findch(text, ",", ixtmpend+1, end)

        # if only whitespaces -> skip
        # plain dot -> skip
        # otherwise, collect these parts for later
        if (len(tmp) > 0):
            if (tmp != "."):
                tmplist.append(tmp)
        indexsrc = ixnext

    if (openingtoken >= 0):
        print("WARN: opening detected but not closing? something is wrong?")
        return None

    print("DEBUG: tokenized list", tmplist)

    # process semi-tokenized list
    skipped = 0
    tlistc = len(tmplist)
    i = 0
    while (i < tlistc):
        tmp = tmplist[i]
        print("DEBUG: token ", tmp)

        # todo: if there is domain from url after the link,
        # we can skip duplicating it

        # otherwise: push to freeform "explanation" or pubhlisher field?
        # note: should maybe push all those that unknown into this field
        # since they they may be some kind of sentence
        if "selite" in parselist:
            selite = parselist["selite"]
            selite += " "
            selite += tmp
            parselist["selite"] = selite

            i = i+1
            continue
        else:
            parselist["selite"] = tmp
            i = i+1
            continue

        # no match? skip
        skipped = skipped +1
        i = i+1

    #if (skipped > 0):
        # combine those that were skipped ?

    print("DEBUG: parsed list", parselist)

    # return tuple: list, amount skipped, final character consumed -> where to replace
        
    # now check what could not be parsed: was it all or was something skipped?
    # if all were parsed into final list, or were put into tokenized list without skipping -> all consumbed
    if (skipped == 0):
        # all tokens consumed
        print("DEBUG: all tokens matched:", parselist)
        #parsingstoppedat = end ?
    else:
        print("DEBUG: skipped tokens:", skipped)
    return tuple((parselist, skipped, parsingstoppedat))
    

# add string in the middle of another at specified position
#
def insertat(oldtext, pos, string):
    # just insert, otherwise no modification (don't skip or remove anything)
    return oldtext[:pos] + string + oldtext[pos:]

# replace text between given indices with new string
# "foobar" "bah" 2, 5 -> "fobahr"
# - old string between indices does not matter 
# - does not need to be same length
# 
def replacebetween(oldtext, newstring, begin, end):
    
    newtext = oldtext[:begin] + newstring + oldtext[end:]
    return newtext

# get name of tag for checking:
# help compare tag name 
def parsenameoftag(text, index, end):
    if ((end-index) < 4):
        # at least "<ref" if there is a space?
        # something is wrong, unfinished page or tag?
        print("ERROR: tag too short?")
        return ""

    #print("DEBUG: tag ", getsubstr(text, index+1, end))

    if (text[index] != "<"):
        print("ERROR: tag start missing?", text[index], "index", index)
        return ""
    if (text[end] != ">"):
        print("ERROR: tag ending missing?", text[end], "index", end)
        return ""
    
    start = index+1
    stop = end

    # closing tag?
    if (text[start] == "/"):
        #print("DEBUG: closing tag")
        start = start +1
    if (text[start] == "!"):
        # comment, not tag
        return ""

    # self-closing tag?
    if (text[stop-1] == "/"):
        #print("DEBUG: self-closing tag")
        stop = stop -1
    if (text[stop-1] == "-"):
        # comment, not tag
        return ""

    # attributes after name of tag?
    ispace = findch(text, " ", start, stop)
    if (ispace > 0 and ispace < stop):
        # ref name="" ?
        tag = getsubstr(text, start, ispace)
        return tag.lower()

    tag = getsubstr(text, start, stop)
    return tag.lower()
    

def findnextbeginningref(oldtext, begin, end):
    
    prevendingtag = begin
    while (prevendingtag < end):
        itmpbegin = findch(oldtext, "<", prevendingtag, end)
        if (itmpbegin < 1 or itmpbegin > end):
            # no more tags?
            break

        # note: in case of smaller than markings it might not be a tag at all..
        # 

        itmpend = findch(oldtext, ">", itmpbegin+1, end)
        if (itmpend < 1 or itmpend > end):
            print("DEBUG: missing tag end ?")
            break

        if (oldtext[itmpbegin+1] == "/" or oldtext[itmpend-1] == "/"):
            # closing tag or self-closing tag -> skip
            prevendingtag = itmpbegin+1
            continue
        
        tagname = parsenameoftag(oldtext, itmpbegin, itmpend)
        if (tagname == "ref"):
            #print("DEBUG: found opening ref tag:", tagname)
            return itmpbegin
        else:
            print("DEBUG: not opening ref tag:", tagname)
            
        prevendingtag = itmpend+1

    return -1

def findnextendingref(oldtext, begin, end):

    # find next reference closing after end of opening tag
    #indexclosingtag = text.find("</ref>", begin)
    
    # note: there may be other tags in between as well?
    prevendingtag = begin
    while (prevendingtag < end):
        # note: handle upper-case as well
        #indexclosingtag = oldtext.find("</", prevendingtag)
        itmpbegin = findch(oldtext, "<", prevendingtag, end)
        if (itmpbegin < 1 or itmpbegin > end):
            # no more tags?
            break

        # end of tag
        itmpend = findch(oldtext, ">", itmpbegin+1, end)
        if (itmpend < 1 or itmpend > end):
            print("DEBUG: missing tag end ?")
            break

        if (oldtext[itmpbegin+1] != "/"):
            # not a closing tag -> skip
            prevendingtag = itmpbegin+1
            continue

        #print("DEBUG: maybe tag:", getsubstr(oldtext, indexclosingtag, iendclosingtag+1))
        
        # get plain name, should be lower-case for easy comparison
        tagname = parsenameoftag(oldtext, itmpbegin, itmpend)
        if (tagname == "ref"):
            #print("DEBUG: found ending ref tag:", tagname)
            return itmpbegin
        else:
            print("DEBUG: not ending ref tag:", tagname)
            
        prevendingtag = itmpend+1

    return -1

def fixreferencelinks(oldtext):
    textlen = len(oldtext)

    index = 1
    while (index < len(oldtext) and index > 0):
        previndex = index
        textlen = len(oldtext) # update in case changed

        # note that on each pass indices will shift if reference is changed to use a template:
        # only change at last step and get new indices after parsing

        
        # handle upper- and mixed-cases as well,
        # check tag in case of name-attribute,
        # handle self-closing tags as well
        index = findnextbeginningref(oldtext, previndex, textlen)
        if (index < 0):
            # no more references, skip to end
            #print("DEBUG: no more references found")
            index = textlen 
            continue
       
        # find end of tag in case there are attributes like name in it:
        # use this to verify where body of reference starts
        ireftagend = findch(oldtext, ">", index+1, textlen)
        if (ireftagend < 0):
            # found beginning of tag but not end before next one?
            # malformed -> skip to end
            print("DEBUG: malformed tags, no end bracket?")
            index = textlen 
            continue

        # count new length of tag (with attributes) for body location:
        # tag attributes change where body begins, this for the tag with attributes
        lentag = ireftagend-index
        
        # there may be other tags in between as well,
        # also handle upper/mixed cases
        indexclosingtag = findnextendingref(oldtext, ireftagend+1, textlen)
        if (indexclosingtag < 0 or indexclosingtag > textlen):
            # unfinished reference tag? -> end here
            print("DEBUG: unfinished reference? skipping")
            index = textlen
            continue
        # if closing tag is before next tag or before starting tag?
        if (indexclosingtag < index or indexclosingtag < ireftagend):
            print("WARN: something is broken, closing tag should not be before starting tag or within starting tag")
            #index = indexclosingtag
            #exit()
            return "" # don't save changes now
            #continue

        #print("DEBUG: reference has body", getsubstr(oldtext, index+lentag+1, indexclosingtag))


        # there is a double bracket for wikilink? -> skip
        if (getsubstr(oldtext, index+lentag, index+lentag+1) == "[["):
            # should not have wikilink in reference, is it used for something else?
            print("DEBUG: double starting bracket in reference, skipping")
            index += lentag
            continue

        # if there is a template within the reference, don't touch it for now:
        # in a best case it might like [link] {{en}}, worst case there is something else
        if (hastemplatewithin(oldtext, index+lentag+1, indexclosingtag) == True):
            print("DEBUG: unsupported template in reference, skipping")
            index = indexclosingtag
            continue

        # only convert where plain link is still used
        ilinkstart = findch(oldtext, "[", ireftagend+1, indexclosingtag)
        ilinkend = findch(oldtext, "]", ireftagend+1, indexclosingtag)
        if (ilinkstart < 0 or ilinkend < 0):
            #print("DEBUG: no link in reference, skipping")
            index = indexclosingtag
            continue
        if (ilinkend < ilinkstart ):
            # a bracket missing in a reference?
            print("WARN: something is broken, link should not end before start")
            #exit()
            return "" # don't save changes now

        print("DEBUG: reference has link", getsubstr(oldtext, ilinkstart, ilinkend))

        # check that link really has http:// or https://
        # find where to split the link
        # next, find first space where link ends (links should have %20 in any case)
        #
        isplit = checkforurl(oldtext, ilinkstart+1, ilinkend)
        if (isplit < 0):
            print("DEBUG: no url in reference, skipping")
            index = indexclosingtag
            continue

        urldomain = getdomainfromurl(oldtext, ilinkstart+1, ilinkend)
        if (urldomain == ""):
            print("DEBUG: could not parse domain from url")

        refauthor = ""
        if ((ilinkstart - ireftagend) > 1): # at least one character before link?

            # try to parse what might be before the link? 
            # if it looks like magazine/book reference information -> skip
            # for now, just skip if there's plenty of other stuff
            if ((ilinkstart - ireftagend) > 20): # 
                print("DEBUG: too much text before link, skipping", getsubstr(oldtext, ireftagend+1, ilinkstart))
                index = indexclosingtag
                continue
            
            # if it ends with a colon (colon+space) maybe it is author?
            colonpos = rfindch(oldtext, ":", ireftagend+1, ilinkstart)
            if (colonpos > ireftagend and colonpos < ilinkstart):
                refauthor = getsubstr(oldtext, ireftagend+1, colonpos)

            #print("DEBUG: something before the link in reference", getsubstr(oldtext, ireftagend+1, ilinkstart))
            
            
        if (refauthor != ""):
            print("DEBUG: found potential author before link", refauthor)

        # is there known pattern after the link?
        # is it completely consumed with parsing (can be overwritten?)
        isunknownafterlink = True

        parsedlist = dict()
        if ((indexclosingtag - ilinkend) > 1): # at least one character length available
            
            # check for comma after link (common problem) and skip it
            shifta = 1
            ch = oldtext[ilinkend+shifta]
            if (ch == "," or ch == "."):
                shifta = shifta+1 # shift starting

            shiftb = 0
            ch = oldtext[indexclosingtag-(shiftb+1)]
            if (ch == "," or ch == "."):
                shiftb = shiftb+1 # shift ending

            # semi-tokenize:
            #tparsed = parseafterlink(oldtext, ilinkend+shifta, indexclosingtag-shiftb)
            tparsed = parseafterlink(oldtext, urldomain, ilinkend+shifta, indexclosingtag)
            if (tparsed != None ):
                # all consumed
                
                #  if parsing stopped at "wayback" we need to stop conversion there as well:
                # don't overwrite those parts that are not converted
                parsedlist = tparsed[0]
                skipped = tparsed[1]
                iend = tparsed[2]
                #if (skipped == 0 and iend == (indexclosingtag-shiftb)):
                if (skipped == 0 and (iend == indexclosingtag or iend == (indexclosingtag-shiftb))):
                    isunknownafterlink = False
                    print("DEBUG: parsed list, all consumed, end: ", iend, "closing", indexclosingtag)
                else:
                    print("DEBUG: parsed list, skipped ", skipped,", end: ", iend, "closing", indexclosingtag)

        #if (parsedlist == None):
        #    index = indexclosingtag
        #    continue

        tmpurl = oldtext[ilinkstart+1:isplit] # just url without starting bracket
        tmpdesc = oldtext[isplit+1:ilinkend] # description without separating space or ending bracket
        
        # some cases don't have a descriptive text for link..
        if (len(tmpdesc) > 1):
            # is there comma as last character in description?
            # remove it
            if (endswithcommaordot(tmpdesc) == True):
                tmpdesc = removelastchar(tmpdesc)
            
         # if description has language template and no other language template?
        #if (tmpdesc.find("{{") > 0 and len(lang) < 1):
        if (tmpdesc.find("{{") > 0 and "lang" not in parsedlist):
            # only if at end
            langtemp = getsubstr(tmpdesc, len(tmpdesc)-6, len(tmpdesc))

            # only specific cases for now
            #if (langtemp == "{{en}}" or langtemp == "{{sv}}" or langtemp == "{{de}}" or langtemp == "{{fr}}"):
            if (issupportedlangtemplate(langtemp) == True):
                parsedlist["lang"] = langtemp
                tmpdesc = tmpdesc[:len(tmpdesc)-len(langtemp)]

        # if description has fileformat
        if (tmpdesc.find("(PDF)") > 0 or tmpdesc.find("(pdf)") > 0):
            # only if at end
            formtemp = getsubstr(tmpdesc, len(tmpdesc)-5, len(tmpdesc))
            
            # only specific cases for now
            #if (formtemp == "(PDF)" or formtemp == "(pdf)"):
            if (issupportedfileformat(formtemp) == True):
                parsedlist["fileformat"] = cleanupfileformat(formtemp)
                tmpdesc = tmpdesc[:len(tmpdesc)-len(formtemp)]

        parsedlist["nimeke"] = tmpdesc
            
        # something unknown after link that should stay there
        iendreplaceat = ilinkend+1 # plus end bracked
        if (isunknownafterlink == False):
            # completely consumed
            iendreplaceat = indexclosingtag # before angle bracket
            #print("DEBUG: replacing from link end to closing tag")
        
        # replace from start of link, if there is something before leave it there
        ibeginreplaceat = ilinkstart
        
        # if there was a usable author before the link, start replacement
        # at beginning of reference body
        if (refauthor != ""):
            ibeginreplaceat = ireftagend+1
            parsedlist["author"] = refauthor

        # if url has archive.org address we can use arkisto-parameter instead:
        # don't do this for other cases in archive.org
        # others: archive.is, archive.today
        if ((urldomain == "web.archive.org" or urldomain == "archive.today" or urldomain == "archive.is") and "arkisto" not in parsedlist):
            parsedlist["arkisto"] = tmpurl
        else:
            parsedlist["osoite"] = tmpurl

        #print("DEBUG: replacing old body:", getsubstr(oldtext, ibeginreplaceat, iendreplaceat))

        # generate new reference with a template according to parsed information:
        # have to write the whole template rather than fixing pieces
        #newtext = "{{Verkkoviite | osoite = " + tmpurl + " | nimeke = " + tmpdesc + " | viitattu = " + accessdate + "}}"
        
        newtext = []
        newtext.append("{{Verkkoviite")

        if ("nimeke" in parsedlist):
            newtext.append(" | nimeke = ")
            newtext.append(parsedlist["nimeke"])

        # if there was a usable author before the link
        if ("author" in parsedlist):
            newtext.append(" | tekijä = ")
            newtext.append(parsedlist["author"])

        if ("osoite" in parsedlist):
            print("DEBUG: appending osoite", parsedlist["osoite"])
            newtext.append(" | osoite = ")
            newtext.append(parsedlist["osoite"])

        # if we parsed archive link from wayback-template after reference body
        if ("arkisto" in parsedlist):
            print("DEBUG: appending arkisto", parsedlist["arkisto"])
            newtext.append(" | arkisto = ")
            newtext.append(parsedlist["arkisto"])

        if ("date" in parsedlist):
            print("DEBUG: appending date", parsedlist["date"])
            newtext.append(" | ajankohta = ")
            newtext.append(parsedlist["date"])
        
        if ("accessdate" in parsedlist):
            print("DEBUG: found accessdate ", parsedlist["accessdate"])
            newtext.append(" | viitattu = ")
            newtext.append(parsedlist["accessdate"])

        if ("pages" in parsedlist):
            print("DEBUG: appending pages", parsedlist["pages"])
            newtext.append(" | sivut = ")
            newtext.append(parsedlist["pages"])

        if ("vanhentunut" in parsedlist):
            print("DEBUG: appending deadlink", parsedlist["vanhentunut"])
            newtext.append(" | vanhentunut = ")
            newtext.append(parsedlist["vanhentunut"])

        if ("fileformat" in parsedlist):
            print("DEBUG: appending fileformat", parsedlist["fileformat"])
            newtext.append(" | tiedostomuoto = ")
            newtext.append(parsedlist["fileformat"])

        if ("lang" in parsedlist):
            print("DEBUG: appending language template ", parsedlist["lang"])
            newtext.append(" | kieli = ")
            newtext.append(parsedlist["lang"])

        if ("publication" in parsedlist):
            print("DEBUG: appending publication", parsedlist["publication"])
            newtext.append(" | julkaisu = ")
            newtext.append(parsedlist["publication"])

        if ("publisher" in parsedlist):
            print("DEBUG: appending publisher", parsedlist["publisher"])
            newtext.append(" | julkaisija = ")
            newtext.append(parsedlist["publisher"])

        if ("selite" in parsedlist):
            
            # final step of checking ending character here since it might have been appended
            selite = parsedlist["selite"]
            if (endswithcommaordot(selite) == True):
                selite = removelastchar(selite)
            
            print("DEBUG: appending freeform explanation", selite)
            newtext.append(" | selite = ")
            newtext.append(selite)

        newtext.append("}}")
        
        snewtext = joinliststr(newtext)
        if (len(snewtext) < 1):
            print("ERROR: joined new text is too short")
            exit(1)
            return "" # don't save changes now

        # replace with template upto end tag
        oldtext = replacebetween(oldtext, snewtext, ibeginreplaceat, iendreplaceat)
        
        # calculate where ending tag is: our replacement may be shorter 
        # and leaves unkown stuff untouched so check where we are
        oldlen = iendreplaceat-ibeginreplaceat
        oldremain = indexclosingtag-iendreplaceat
        newend = len(snewtext) + ibeginreplaceat + oldremain
        
        # TODO: handle upper case as well
        # just check if our calculations were correct
        endtagnew = getsubstr(oldtext, newend, newend+6)
        endtagnew = endtagnew.lower() # may be upper case?
        if (endtagnew == "</ref>"):
            print("DEBUG: ok, new end found correctly")
            index = newend+6 # yes, we can skip after this tag
        else:
            # next tag should be searched by other position?
            print("DEBUG: ending tag is not correct, falling back", endtagnew)
            # continue search after this referece:
            # we must search for an opening ref-tag again
            index = indexclosingtag

        # check current total length
        #textlen = len(oldtext)

        # this might be more accurate, but it does not count what was left (unparsed)
        # if there was something like a wayback-template after
        #index = ibeginreplaceat + len(snewtext)

        # continue search after this one:
        # we must search for an opening ref-tag again
        #index = indexclosingtag

    return oldtext


def getpagebyname(pywikibot, site, name):
    return pywikibot.Page(site, name)

def getnamedpages(pywikibot, site):
    pages = list()
    
    #fp = getpagebyname(pywikibot, site, "Abeliat")
    #fp = getpagebyname(pywikibot, site, "Single")
    #fp = getpagebyname(pywikibot, site, "Hämeenlinna")
    #fp = getpagebyname(pywikibot, site, "Britteinsaaret")
    
    #fp = getpagebyname(pywikibot, site, "Another Hostile Takeover")
    
    #fp = getpagebyname(pywikibot, site, "Hyönteiset")
    #fp = getpagebyname(pywikibot, site, "Ahvenanmaanruotsi")
    #fp = getpagebyname(pywikibot, site, "Arctia (hotelli- ja ravintolayhtiö)")

    #fp = getpagebyname(pywikibot, site, "Mystery Tracks – Archives Vol. 3")

    #fp = getpagebyname(pywikibot, site, "7-Eleven")

    #fp = getpagebyname(pywikibot, site, "M-16 (albumi)")
    
    #fp = getpagebyname(pywikibot, site, "Deep Shadows and Brilliant Highlights")
    #fp = getpagebyname(pywikibot, site, "At Sixes and Sevens")
    #fp = getpagebyname(pywikibot, site, "Fundamental")

    #fp = getpagebyname(pywikibot, site, "Systematic Chaos")

    #fp = getpagebyname(pywikibot, site, "Arvonimi")

    #fp = getpagebyname(pywikibot, site, "Venetsialaiset")

    #fp = getpagebyname(pywikibot, site, "Leijona")

    #fp = getpagebyname(pywikibot, site, "Makrilli")


    #fp = getpagebyname(pywikibot, site, "Kuunliljat")
    
    fp = getpagebyname(pywikibot, site, "Phillip Cocu")
    


    pages.append(fp)
    return pages
    

def getpagesrecurse(pywikibot, site, maincat, depth=1):
    #final_pages = list()
    cat = pywikibot.Category(site, maincat)
    pages = list(cat.articles(recurse=depth))
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

# check if there is short time since last edit, it might be being edited at the moment?
def checklastedit(pywikibot, page):

    secondssinceedit = (datetime.now() - page.latest_revision.timestamp).seconds
    if (secondssinceedit < 240):
        print("NOTE: Page " + page.title() + " is maybe being edited?")
    else:
        print("Page " + page.title() + " has " + str(secondssinceedit) + " since last edit")


def testparse():
    test = "<ref></ref><ref/>"
    
    end = len(test)
    i = 0
    while (i < end and i >= 0):
        ix = findch(test, "<", i, end)
        #ix = test.find("<", i, end)
        if (ix < 0):
            print("no starting brackets")
            break
        print("ix:", ix)
        ixend = findch(test, ">", ix, end)
        #ixend = test.find("<", ix, end)
        if (ixend < 0):
            print("no ending brackets")
            break
        print("ixend:", ixend)
        
        name = parsenameoftag(test, ix, ixend)
        print("name:", name)
        i = ixend

## main()
#if __name__ == "__main__":
    #testparse()
    #exit()


site = pywikibot.Site("fi", "wikipedia")
site.login()

# musiikkialbumit
#pages = getpagesfrompetscan(pywikibot, site,  40068787, 22000)

# taksopalkki
#pages = getpagesfrompetscan(pywikibot, site,  40079450, 28000)

#pages = getpagesrecurse(pywikibot, site, "Lääkkeet", 1)

#pages = getpagesrecurse(pywikibot, site, "Kemia", 0)

#pages = getpagesrecurse(pywikibot, site, "Jalkapalloilijat", 2)
#pages = getpagesrecurse(pywikibot, site, "Alankomaalaiset jalkapalloilijat", 1)


#pages = getpagesrecurse(pywikibot, site, "Sairaudet", 1)


pages = getpagesrecurse(pywikibot, site, "Puutteelliset lähdemerkinnät", 1)


# for testing
#pages = getnamedpages(pywikibot, site)


rivinro = 1

for page in pages:

    #if (page.namespace() != 6):  # 6 is the namespace ID for files
    # skip user-pages, only main article namespace
    if (page.namespace() != 0):  
        print("Skipping ", page.title() ," - wrong namespace.")
        continue

    #page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" //////////////// ------", rivinro, "/", len(pages), ": [ ", page.title() ," ] ------ ////////////////")
    rivinro += 1

    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping ", page.title() ," - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping ", page.title() ," - bot-restricted.")
        continue
    if (oldtext.find("{{työstetään}}") > 0 or oldtext.find("{{Työstetään}}") > 0):
        print("Skipping ", page.title() ," - under editing.")
        continue

    # check in case page is being edited:
    # how much time since last edit has passed
    checklastedit(pywikibot, page)

    temptext = oldtext

    temptext = fixreferencelinks(temptext)
    summary = 'Muutetaan viitelinkki viitemallineelle'

    if (temptext == ""):
        print("Skipping. ", page.title() ," - something went wrong.")
        continue

    if oldtext == temptext:
        print("Skipping. ", page.title() ," - old and new are equal.")
        continue

    # when there are other changes,
    # also fix cases where mixed-case has been used?
    temptext = temptext.replace("</Ref>", "</ref>")
    temptext = temptext.replace("<Ref>", "<ref>")
    #temptext = temptext.replace("</REF>", "</ref>")
    #temptext = temptext.replace("<REF>", "<ref>")
    

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

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
        page.text = temptext
        page.save(summary)

