# Purpose: add template for cases where magic link might be used
#
# Magic links are supposed to be removed and have no validation. 
# Using the template creates link to search and has validation.
#
# Running script: python <scriptname>
#

import pywikibot
import json
from urllib.request import urlopen

from datetime import datetime


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

def findisbnend(source, start, end):

    #if (end >= len(source)):
    #    end = len(source)

    i = start
    while (i < end):
        ch = source[i]
        
        # allowed separators are space and dash
        if (source[i] == " " and i < end):
            i += 1
            continue
        if (source[i] == "-" and i < end):
            i += 1
            continue

        # might be within template already -> skip
        if (ch == "="):
            return -1
        if (ch == "|"):
            return -1
        if (ch == "}"):
            return -1

        # something else that should not be there
        #if (ch == ")"):
        #    return -1
        if (ch == ">"):
            return -1
        if (ch == "]"):
            return -1
        #if (ch == "&"):
        #    return -1


        # check for known possible ending characters
        if (source[i] == "\n" and i < end):
            return i
        if (source[i] == "." and i < end):
            return i
        if (source[i] == "。" and i < end):
            return i
        #if (source[i] == "," and i < end):
        #    return i
        #if (source[i] == ";" and i < end):
        #    return i
        #if (source[i] == "<" and i < end):
        #    return i
        # weblink starting after?
        #if (source[i] == "[" and i < end):
        #    return i
        # template starting after?
        #if (source[i] == "{" and i < end):
        #    return i

        # within parentheses?
        #if (source[i] == ")" and i < end):
        #    return i

        # something else after it or maybe used in url?
        #if (source[i] == "&" and i < end):
        #    return i
        # something else after or mistaken separator?
        if (source[i] == "–" and i < end):
            return i

        # broken tag?
        #if (ch == "/" and i < end):
        #    return i
        # list without new line?
        #if (ch == "*" and i < end):
        #    return i
        # wikimarkup for italics?
        #if (ch == "'" and i < end):
        #    return i


        # not supposed to have any other letters in isbn
        # than X as check digit:
        # a letter that is not X or x
        if (ch.isalpha() and (ch != "X" and ch != "x")):
            return i

        # not a letter, number, space or dash (some other character) -> end
        if (ch.isalpha() == False and ch.isnumeric() == False and ch != " " and ch != "-"):
            return i


        if ((i - start) >= 20):
            # something is wrong, did not find end at suitable place
            return -1
        i += 1

    # did not find end
    return -1

# between "ISBN" and actual number
def findisbnstart(source, start):

    i = start
    end = start + 30 # should not be more than one or two spaces at most
    #if (end >= len(source)):
    #    end = len(source)
    
    while (i < end):
        ch = source[i]
        
        # allowed separators are space
        # (should replace tabulators and non-breakable spaces)
        if (ch == " " and i < end):
            i += 1
            continue

        # tabulator?
        #if (ch == "	"):

        # non-breakable space?
        #if (ch == " "):
        #if (ch == "‭ "):
        

        # might be within template already -> abort
        if (ch == "="):
            return -1
        if (ch == "|"):
            return -1

        # part of URL? -> abort
        if (ch == "_"):
            return -1

        # first number found -> ok
        if (ch.isnumeric()):
            return i

        # isbn should start with a number instead of a letter
        if (ch.isalpha()):
            return -1


        if ((i - start) >= 30):
            # something is wrong, did not find end at suitable place
            return -1
        i += 1

    # did not find end
    return -1


def findisbnmaketemplate(oldtext):
    textlen = len(oldtext)

    index = 1
    while (index < textlen and index > 0):
        previndex = index

        # TODO: check for tabulator and non-breakable space as well
        # be careful for now, expect space before and after
        index = oldtext.find("ISBN", previndex)
        if (index > 0):
            # within url perhaps -> skip
            temp = oldtext[index-4:index]
            if (temp == "vid=" or temp == "URN:"):
                index += 4
                continue
                
            # within a template already? -> skip
            # might be a parameter to something (in url) -> skip
            if (oldtext[index-1] == "{" or oldtext[index-1] == "|" or oldtext[index-1] == "=" or oldtext[index-1] == "/"):
                index += 4
                continue
            
            # find first number or abort if in template
            indexnum = findisbnstart(oldtext, index+len("ISBN"))
            if (indexnum == -1):
                index += 4
                continue
                
            # find suitable ending character after isbn or stop if not found
            # might have 17 characters (including separators) for ISBN-13
            indexend = findisbnend(oldtext, indexnum, indexnum+20)
            if (indexend == -1):
                # could not find suitable end for this
                index += 20
                continue

            # otherwise, make template

            # if last one is space, leave it out (otherwise spaces are valid separators)
            if (oldtext[indexend-1] == " "):
                indexend = indexend-1
            
            oldtext = insertat(oldtext, indexend, "}}")
            oldtext = replacebetween(oldtext, "{{ISBN|", index, indexnum)

            # continue search after this one
            index = indexend
            
    return oldtext


def getpagebyname(pywikibot, site, name):
    return pywikibot.Page(site, name)

def getnamedpages(pywikibot, site):
    pages = list()
    
    fp = getpagebyname(pywikibot, site, "Abeliat")
    
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


#pages = getpagesfrompetscan(pywikibot, site,  31544797, 150000)

#pages = getpagesrecurse(pywikibot, site, "Sivut, joissa on virheellinen ISBN-tunniste", 1)

#pages = getpagesrecurse(pywikibot, site, "Sivut, joissa on virheellinen ISSN-tunniste", 1)

pages = getpagesrecurse(pywikibot, site, "Sivut, jotka käyttävät ISBN-taikalinkkejä", 1)


# for testing
#pages = getnamedpages(pywikibot, site)

rivinro = 1

for page in pages:

    #if (page.namespace() != 6):  # 6 is the namespace ID for files
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
    if (oldtext.find("{{työstetään}}") > 0 or oldtext.find("{{Työstetään}}") > 0):
        print("Skipping " + page.title() + " - under editing.")
        continue

    # check in case page is being edited:
    # how much time since last edit has passed
    checklastedit(pywikibot, page)

    temptext = oldtext
   
    temptext = findisbnmaketemplate(temptext)
    summary='Muutetaan taikalinkki ISBN-mallineelle'

    
    if oldtext == temptext:
        print("Skipping. " + page.title() + " - old and new are equal.")
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

