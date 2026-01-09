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

def getsubstr(text, begin, end):
    if (end < begin):
        return -1
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

    print("DEBUG: searching for template in ref, begin", reftagopen, "end", reftagclose)

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
            print("DEBUG: no more template(s) in ref")
            return hasunkowntemplate
        if (getsubstr(text, iopenbrace, iopenbrace+1) != "{{"):
            print("DEBUG: not double open brace, not template")
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
            if (tmpname == "en" or tmpname == "sv" or tmpname == "de" or tmpname == "fr"):
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
    else:
        print("DEBUG: all templates parsed in reference")
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
        
        if (ch == " "):
            #print("DEBUG: found url", getsubtr(text, begin, ispace))
            return ispace

        ispace += 1

    print("DEBUG: no space to separate url from text in link?")
    return -1

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
        
    if (langtemp == "{{en}}" 
        or langtemp == "{{sv}}" 
        or langtemp == "{{de}}" 
        or langtemp == "{{fr}}"):
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
        or langtemp == "de" 
        or langtemp == "fr"):
        return True
    return False


def isdeadlinktemplate(temp):
    
    # skip
    #if (temp == "{{Wayback".. ): 

    # note: may be : {{vanhentunut linkki | IntenetArchiveBot }}
    #{{Vanhentunut linkki|bot=InternetArchiveBot }}
    #if (temp == "{{Vanhentunut linkki|bot=InternetArchiveBot }}" or temp == "{{Vanhentunut linkki|bot=InternetArchiveBot}}"):
    #    return True

    temp = temp.lower()
    
    if (temp == "{{404}}" or temp == "{{vanhentunut linkki}}"  or temp == "{{kuollut linkki}}" 
        or temp == "{{dead link}}"  or temp == "{{deadlink}}" ):
        return True
    return False

def iswaybacktemplate(temp):
    if (temp.find("{{Wayback") == 0):
        return True
    return False


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
def parseafterlink(text, begin, end):

    # is there dor or comma immediately at the beginning?
    if (beginswithcommaordot(text) == True):
        begin = begin +1
    #    text = removefirstchar(text)

    # is there dot or comma at end? remove it
    if (endswithcommaordot(text) == True):
        end = end -1
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

    # make a semi-tokenized list for special cases
    tmplist = list()
    indexsrc = begin
    openingtoken = -1
    accessfound = -1
    parsingstoppedat = indexsrc
    while (indexsrc < end and indexsrc > 0):
        previndex = indexsrc
        
        # if we are pointing at space just increment so python doesn't stall on it
        if (text[previndex] == " "):
            previndex = previndex+1

        indexsrc = text.find(" ", previndex)
        ixnext = end # stop at last by default
        ixtmpend = end
        if (indexsrc > 0 and indexsrc < end):
            ixtmpend = indexsrc
            ixnext = indexsrc +1 # skip space and continue
            
        tmp = getsubstr(text, previndex, ixtmpend)
        tmp = tmp.strip()
        
        if (iswaybacktemplate(tmp) == True):
            # not expecting useful stuff now (although there may be after)
            parsingstoppedat = previndex
            break

        # skip rest if this is known
        if (issupportedlangtemplate(tmp) == True):
            parselist["lang"] = tmp
            indexsrc = ixnext
            parsingstoppedat = indexsrc
            continue
        if (isdeadlinktemplate(tmp) == True ):
            parselist["vanhentunut"] = "kyllä"
            indexsrc = ixnext
            parsingstoppedat = indexsrc
            continue
        if (issupportedfileformat(tmp) == True):
            parselist["fileformat"] = cleanupfileformat(tmp)
            indexsrc = ixnext
            parsingstoppedat = indexsrc
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
            print("DEBUG: full token:", tmp)
            openingtoken = -1
            if (len(tmp) > 0):
                tmplist.append(tmp)
            indexsrc = ixnext
            parsingstoppedat = indexsrc
            continue
            
        # if only whitespaces -> skip
        # otherwise, collect these parts for later
        if (len(tmp) > 0):
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

        # TODO: also might have to remove separator characeters (, or .)

        # begins with cursive markup? might have website or such?
        if (len(tmp) > 2 and tmp[:2] == "''"):
            print("DEBUG: using publication", tmp)
            parselist["publication"] = tmp
            i = i+1
            continue
        
        if (isopeningtoken(tmp) == True):
            # strip opening/closing and parse then again
            tmp = stripopenclose(tmp)

        # note: check for case where this is within parentheses
        # with the initial parsing we should have access keyword and date in one
        accessdate = parseaccessdateafterlink(tmp)
        if (len(accessdate) > 0):
            parselist["accessdate"] = cleanupdatestr(accessdate)
            i = i+1
            continue
            
        # starts with a known keyword..
        if (isaccesskeyword(tmp) == True):

            # use 1..3 next in list for parts of access date?
            # (if separated by spaces),
            # this is likely in case of textual date ("1. tammikuuta 2025")
            if (i+1 < tlistc):
                tmp1 = tmplist[i+1]
                if (isvaliddate(tmp1) == True):
                    parselist["accessdate"] = cleanupdatestr(tmp1)
                    i = i+1
                    continue

            if (i+2 < tlistc):
                tmp1 = tmplist[i+1]
                tmp2 = tmplist[i+2]
                combo = tmp1+tmp2
                if (isvaliddate(combo) == True):
                    parselist["accessdate"] = cleanupdatestr(combo)
                    i = i+2
                    continue

            if (i+3 < tlistc):
                tmp1 = tmplist[i+1]
                tmp2 = tmplist[i+2]
                tmp3 = tmplist[i+3]
                combo = tmp1+tmp2+tmp3
                if (isvaliddate(combo) == True):
                    parselist["accessdate"] = cleanupdatestr(combo)
                    i = i+3
                    continue
            continue
                
        # might have publication and/or website without a keyword before:
        # those might need to be combined

        # note: should not use date second time here if it was found to be accessdate
        # otherwise may have plain date?
        if (isvaliddate(tmp) == True):
            parselist["date"] = cleanupdatestr(tmp)
            i = i+1
            continue
        
        # otherwise: push to freeform "explanation" or pubhlisher field?

        # note: should maybe push all those that unknown into this field
        # since they they may be some kind of sentence
        #parselist["selite"] = tmp
        #knownc = knownc +1
        #i = i+1
        #continue

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


def fixreferencelinks(oldtext):
    textlen = len(oldtext)

    index = 1
    while (index < textlen and index > 0):
        previndex = index

        # TODO: also <ref name..>
        lentag = len("<ref")

        index = oldtext.find("<ref", previndex)
        if (index < 0):
            # no more references, skip to end
            #print("DEBUG: no more references found")
            index = textlen 
            continue

        # verify tags are correctly formed in sequence
        # note that text might have angle brackets too..
        inexttag = oldtext.find("<", index+1)
        #inexttag = finch(oldtext, "<", index+1)
        if (inexttag < 0):
            # we have a beginning tag but no potential ending tag?
            # malformed page -> skip over to end
            print("DEBUG: no start of next tag, no start of ending?")
            index += lentag
            continue
        
        ireftagend = findch(oldtext, ">", index+1, inexttag)
        if (ireftagend < 0):
            # found beginning of tag but not end before next one?
            # malformed -> skip over
            print("DEBUG: malformed tags, no end bracket?")
            index += lentag
            continue

        # count new length of tag (with attributes) for body location:
        # tag attributes change where body begins
        lentag = ireftagend-index

        # don't stop on <references>, just <ref> or <ref name
        reftag = getsubstr(oldtext, index, index+5)
        if (reftag != "<ref>" and reftag != "<ref "): 
            # skip over
            print("DEBUG: not a ref-tag", reftag)
            index += lentag
            continue

        # ref tag might be self closing <ref name/>, don't stop if name has the char..
        if (oldtext[ireftagend-1] == "/"):
            #print("DEBUG: self-closing ref-tag, skipping")
            index += lentag
            continue

        # find next reference closing after end of opening tag
        indexclosingtag = oldtext.find("</ref>", ireftagend)
        if (indexclosingtag < 0):
            # unfinished reference tag? -> end here
            print("DEBUG: unfinished reference? skipping")
            index = textlen
            continue

        #print("DEBUG: reference has body", getsubstr(oldtext, index+lentag+1, indexclosingtag))

        #chfirst = oldtext[index-len("<ref>")]
        #chfirst = oldtext[index+lentag]
        #if (chfirst == "{"):
            # starts with curly brace -> template -> skip
            #print("DEBUG: curly brace in reference, has template? skipping")
        #    index += lentag
        #    continue

        
        # don't touch if it does not start with bracket:
        # could add more cases later
        #if (chfirst != "["):
            #print("DEBUG: no starting bracket in reference, skipping", chfirst)
        #    print("DEBUG: no starting bracket in reference, skipping")
        #    index += lentag
        #    continue

        # there is a double bracket for wikilink? -> skip
        #if (oldtext[ireftagend+1:ireftagend+2] == "[["):
        if (getsubstr(oldtext, index+lentag, index+lentag+1) == "[["):
            print("DEBUG: double starting bracket in reference, skipping")
            index += lentag
            continue


        # within a template already? -> skip
        # might be a parameter to something (in url) -> skip
        #if (oldtext[index-1] == "{" or oldtext[index-1] == "|" or oldtext[index-1] == "=" or oldtext[index-1] == "/"):
        #    index += 4
        #    continue


        # TODO: only if there is a language tag we should continue here

        # if there is a template within the reference, don't touch it for now:
        # in a best case it might like [link] {{en}}, worst case there is something else
        if (hastemplatewithin(oldtext, index+lentag+1, indexclosingtag) == True):
            print("DEBUG: unsupported template in reference, skipping")
            index = indexclosingtag
            continue

        print("DEBUG: no templates in reference or supported templates")

        # don't touch if it does not end with a bracket:
        # might add later handling if there are other templates within reference (like [link] {{en}})
        #chend = oldtext[indexend+1]
        #if (chend != "]"):
        #    print("DEBUG: no ending bracket in reference, skipping")
        #    index = indexend
        #    continue


        ilinkstart = findch(oldtext, "[", ireftagend+1, indexclosingtag)
        ilinkend = findch(oldtext, "]", ireftagend+1, indexclosingtag)
        if (ilinkstart < 0 or ilinkend < 0):
            print("DEBUG: no link in reference, skipping")
            index = indexclosingtag
            continue

        print("DEBUG: reference has link", getsubstr(oldtext, ilinkstart, ilinkend))


        # check that link really has http:// or https://
        # find where to split the link
        # next, find first space where link ends (links should have %20 in any case)
        
        isplit = checkforurl(oldtext, ilinkstart+1, ilinkend)
        if (isplit < 0):
            print("DEBUG: no url in reference, skipping")
            index = indexclosingtag
            continue

        if ((ilinkstart - ireftagend) > 1): # at least one character before link?
            print("DEBUG: something before the link in reference", getsubstr(oldtext, ireftagend, ilinkstart))
            # try to parse what might be before the link? 
            # if it looks like magazine/book reference information -> skip
            # for now, just skip if there's plenty of other stuff
            if ((ilinkstart - ireftagend) > 20): # 
                index = indexclosingtag
                continue


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
            tparsed = parseafterlink(oldtext, ilinkend+shifta, indexclosingtag-shiftb)
            if (tparsed != None ):
                # all consumed
                
                #  if parsing stopped at "wayback" we need to stop conversion there as well:
                # don't overwrite those parts that are not converted
                parsedlist = tparsed[0]
                skipped = tparsed[1]
                iend = tparsed[2]
                if (skipped == 0 and iend == (indexclosingtag-shiftb)):
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
            if (tmpdesc[len(tmpdesc)-1] == ","):
                tmpdesc = tmpdesc[:len(tmpdesc)-1]

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

            
        # something unknown after link that should stay there
        iendreplaceat = ilinkend+1 # plus end bracked
        if (isunknownafterlink == False):
            # completely consumed
            iendreplaceat = indexclosingtag # before angle bracket
            #print("DEBUG: replacing from link end to closing tag")
        
        # replace from start of link, if there is something before leave it there
        ibeginreplaceat = ilinkstart

        #print("DEBUG: replacing old body:", getsubstr(oldtext, ibeginreplaceat, iendreplaceat))

        #newtext = "{{Verkkoviite | osoite = " + tmpurl + " | nimeke = " + tmpdesc + " | viitattu = " + accessdate + "}}"
        
        newtext = []
        newtext.append("{{Verkkoviite | osoite = ")
        newtext.append(tmpurl)
        newtext.append(" | nimeke = ")
        newtext.append(tmpdesc)
        
        if ("accessdate" in parsedlist):
            print("DEBUG: found accessdate ", parsedlist["accessdate"])
            newtext.append(" | viitattu = ")
            newtext.append(parsedlist["accessdate"])

        if ("date" in parsedlist):
            print("DEBUG: appending date", parsedlist["date"])
            newtext.append(" | ajankohta = ")
            newtext.append(parsedlist["date"])
        
        if ("lang" in parsedlist):
            print("DEBUG: appending language template ", parsedlist["lang"])
            newtext.append(" | kieli = ")
            newtext.append(parsedlist["lang"])

        if ("vanhentunut" in parsedlist):
            print("DEBUG: appending deadlink", parsedlist["vanhentunut"])
            newtext.append(" | vanhentunut = ")
            newtext.append(parsedlist["vanhentunut"])

        if ("fileformat" in parsedlist):
            print("DEBUG: appending fileformat", parsedlist["fileformat"])
            newtext.append(" | tiedostomuoto = ")
            newtext.append(parsedlist["fileformat"])

        if ("publication" in parsedlist):
            print("DEBUG: appending publication", parsedlist["publication"])
            newtext.append(" | publication = ")
            newtext.append(parsedlist["publication"])

        if ("publisher" in parsedlist):
            print("DEBUG: appending publisher", parsedlist["publisher"])
            newtext.append(" | julkaisija = ")
            newtext.append(parsedlist["publisher"])

        if ("selite" in parsedlist):
            print("DEBUG: appending freeform explanation", parsedlist["selite"])
            newtext.append(" | selite = ")
            newtext.append(parsedlist["selite"])


        newtext.append("}}")
        
        snewtext = joinliststr(newtext)
        if (len(snewtext) < 1):
            print("ERROR: joined new text is too short")
            exit(1)

        # replace with template upto end tag
        oldtext = replacebetween(oldtext, snewtext, ibeginreplaceat, iendreplaceat)


        # continue search after this one
        index = indexclosingtag
            
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
    
    #fp = getpagebyname(pywikibot, site, "Sakkola-museo")
    
    #fp = getpagebyname(pywikibot, site, "Tapio Furuholm")
    
    #fp = getpagebyname(pywikibot, site, "BCG-rokote")
    
    #fp = getpagebyname(pywikibot, site, "Dimerkaproli")
    
    

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


## main()

site = pywikibot.Site("fi", "wikipedia")
site.login()

# musiikkialbumit
#pages = getpagesfrompetscan(pywikibot, site,  40068787, 22000)

# taksopalkki
#pages = getpagesfrompetscan(pywikibot, site,  40079450, 28000)

#pages = getpagesrecurse(pywikibot, site, "Lääkkeet", 1)

#pages = getpagesrecurse(pywikibot, site, "Jalkapalloilijat", 2)

#pages = getpagesrecurse(pywikibot, site, "Suomalaiset jalkapalloilijat", 0)

#pages = getpagesrecurse(pywikibot, site, "Lempäälä", 0)

pages = getpagesrecurse(pywikibot, site, "Tartuntataudit", 1)
#pages = getpagesrecurse(pywikibot, site, "Sairaudet", 1)

#pages = getpagesrecurse(pywikibot, site, "Rallin MM-sarjan osakilpailut", 1)


#pages = getpagesrecurse(pywikibot, site, "Puutteelliset lähdemerkinnät", 1)


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
    summary='Muutetaan viitelinkki viitemallineelle'

    
    if oldtext == temptext:
        print("Skipping. ", page.title() ," - old and new are equal.")
        continue

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
        page.text=temptext
        page.save(summary)

