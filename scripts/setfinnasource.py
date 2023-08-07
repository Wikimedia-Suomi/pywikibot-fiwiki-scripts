# Purpose: add metapage to source on pictures from finna
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
import urllib
from urllib.request import urlopen

import urllib3

def getnewfinnarecordurl(finnarecordid):
    if (len(finnarecordid) == 0):
        return ""
    return "https://finna.fi/Record/" + finnarecordid

def getnewsourceforfinna(finnarecordurl, finnarecordid):
    if (len(finnarecordurl) == 0 or len(finnarecordid) == 0):
        return ""
    return "<br>Image record page in Finna: [" + finnarecordurl + " " + finnarecordid + "]\n"

# strip id from other things that may be after it:
# there might be part of url or some html in same field..
def stripid(oldsource):
    # space after url?
    indexend = oldsource.find(" ")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # html tag after url?
    indexend = oldsource.find("<")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find(">")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # wikimarkup after url?
    indexend = oldsource.find("[")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("]")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("{")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("}")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("|")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("&")
    if (indexend > 0):
        oldsource = oldsource[:indexend]
    indexend = oldsource.find("#")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # some parameters in url?
    indexend = oldsource.find("?")
    if (indexend > 0):
        oldsource = oldsource[:indexend]

    # linefeed at end?
    if (oldsource.endswith("\n")):
        oldsource = oldsource[:len(oldsource)-1]

    return oldsource

def getidfromoldsource(oldsource):
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return oldsource

    oldsource = oldsource[indexid+3:]
    return stripid(oldsource)

# commons source may have human readable stuff in it
# parse to plain url
def geturlfromsource(source):
    protolen = len("http://")
    index = source.find("http://")
    if (index < 0):
        protolen = len("https://")
        index = source.find("https://")
        if (index < 0):
            # no url in string
            return ""

    # try to find space or something            
    indexend = source.find(" ", index+protolen)
    if (indexend < 0):
        # no space or other clear separator -> just use string length
        indexend = len(source)-1
        
    return source[index:indexend]

# input: kuvakokoelmat.fi url
# output: old format id
def getkuvakokoelmatidfromurl(source):
    # if there is human readable stuff in source -> strip to just url
    source = geturlfromsource(source)
    
    indexlast = source.rfind("/", 0, len(source)-1)
    if (indexlast < 0):
        # no separator found?
        print("invalid url: " + source)
        return ""
    kkid = source[indexlast+1:]
    if (kkid.endswith("\n")):
        kkid = kkid[:len(kkid)-1]

    # .jpg or something at end? remove from id
    indexlast = kkid.rfind(".", 0, len(source)-1)
    if (indexlast > 0):
        kkid = kkid[:indexlast]
    return kkid

# input: old format "HK"-id, e.g. HK7155:219-65-1
# output: newer "musketti"-id, e.g. musketti.M012%3AHK7155:219-65-1
def convertkuvakokoelmatid(kkid):
    if (len(kkid) == 0):
        print("empty kuvakokoelmat id ")
        return ""

    # verify
    if (kkid.startswith("HK") == False):
        print("does not start appropriately: " + kkid)
        return ""

    index = kkid.find("_")
    if (index < 0):
        print("no underscores: " + kkid)
        return ""
    # one underscore to colon
    # underscores to dash
    # add prefix
    kkid = kkid[:index] + ":" + kkid[index+1:]
    kkid = kkid.replace("_", "-")
    musketti = "musketti.M012:" + kkid
    return musketti

def getnewsourcefromoldsource(srcvalue):
    if (srcvalue.find("kuvakokoelmat.fi") > 0):
        kkid = getkuvakokoelmatidfromurl(srcvalue)
        newfinnaid = convertkuvakokoelmatid(kkid)
        if (len(newfinnaid) > 0):
            return urllib.parse.quote(newfinnaid) # quote for url
            #newsourceurl = "https://www.finna.fi/Record/" + newfinnaid
        return "" # failed to parse, don't add anything
        
    if (srcvalue.find("finna.fi") > 0):
        # finna.fi url
        return getidfromoldsource(srcvalue)

    return ""

# fetch metapage from finna and check if we have a valid url
# since we might have obsolete ID.
def getfinnapage(finnaurl):

    finnapage = ""

    try:
        request = urllib.request.Request(finnaurl)
        print("request done: " + finnaurl)

        response = urllib.request.urlopen(request)
        if (response.readable() == False):
            print("response not readable")

        htmlbytes = response.read()
        finnapage = htmlbytes.decode("utf8")

        #print("page: " + finnapage)
        return True # page found
        
    except urllib.error.HTTPError as e:
        print(e.__dict__)
        return False
    except urllib.error.URLError as e:
        print(e.__dict__)
        return False
    #except:
        #print("failed to retrieve finna page")
        #return False

    return False

# get pages immediately under cat
# and upto depth of 1 in subcats
def getcatpages(pywikibot, commonssite, maincat, recurse=False):
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(commonssite.categorymembers(cat))

    # no recursion by default, just get into depth of 1
    if (recurse == True):
        subcats = list(cat.subcategories())
        for subcat in subcats:
            subpages = commonssite.categorymembers(subcat)
            for subpage in subpages:
                if subpage not in pages: # avoid duplicates
                    pages.append(subpage)

    return pages

def getlinkedpages(pywikibot, commonssite, linkpage):
    listpage = pywikibot.Page(commonssite, linkpage)  # The page you're interested in

    pages = list()
    # Get all linked pages from the page
    for linked_page in listpage.linkedPages():
        if linked_page not in pages: # avoid duplicates
            pages.append(linked_page)

    return pages

# ------ main()

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')

rowcount = 1
#rowlimit = 10

print("Pages found: " + str(len(pages)))

for page in pages:
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    filepage = pywikibot.FilePage(page)
    if filepage.isRedirectPage():
        continue    

    newsourceurl = ""
    changed = False
    oldtext=page.text

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")
    rowcount += 1

    wikicode = mwparserfromhell.parse(page.text)
    
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        if template.name.matches("Information") or template.name.matches("Photograph") or template.name.matches("Artwork") or template.name.matches("Art Photo"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                if (srcvalue.find("profium.com") > 0):
                    print("WARN: unusable url (redirector) in: " + page.title() + ", source: " + srcvalue)
                    break
                if (srcvalue.find("finna.fi") < 0 and srcvalue.find("kuvakokoelmat.fi") < 0):
                    print("unknown source, skipping")
                    break
                if (srcvalue.find("finna.fi") > 0 and srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                newsourcetext = ""
                newsourceid = getnewsourcefromoldsource(srcvalue)
                newsourceurl = getnewfinnarecordurl(newsourceid)
                if (len(newsourceurl) > 0):
                    newsourcetext = getnewsourceforfinna(newsourceurl, newsourceid)
                if (newsourcetext != srcvalue and len(newsourcetext) > 0):
                    # remove newline from existing before appending
                    if (srcvalue.endswith("\n")):
                        srcvalue = srcvalue[:len(srcvalue)-1]
                    par.value = srcvalue + newsourcetext
                    changed = True

            if template.has("source"):
                par = template.get("source")
                srcvalue = str(par.value)
                if (srcvalue.find("profium.com") > 0):
                    print("WARN: unusable url (redirector) in: " + page.title() + ", source: " + srcvalue)
                    break
                if (srcvalue.find("finna.fi") < 0 and srcvalue.find("kuvakokoelmat.fi") < 0):
                    print("unknown source, skipping")
                    break
                if (srcvalue.find("finna.fi") > 0 and srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                newsourcetext = ""
                newsourceid = getnewsourcefromoldsource(srcvalue)
                newsourceurl = getnewfinnarecordurl(newsourceid)
                if (len(newsourceurl) > 0):
                    newsourcetext = getnewsourceforfinna(newsourceurl, newsourceid)
                if (newsourcetext != srcvalue and len(newsourcetext) > 0):
                    # remove newline from existing before appending
                    if (srcvalue.endswith("\n")):
                        srcvalue = srcvalue[:len(srcvalue)-1]
                    par.value = srcvalue + newsourcetext
                    changed = True
 
    if (changed == False):
        print("no change, skipping")
        continue
    if (getfinnapage(newsourceurl) == False):
        print("Failed to get finna metapage with new url: " + newsourceurl)
        continue
    print("Found finna metapage with new url: " + newsourceurl)

    newtext = str(wikicode)

    if oldtext == newtext:
        print("Skipping. " + page.title() + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, newtext,2)
    summary='Adding metapage to source'
    pywikibot.info('Edit summary: {}'.format(summary))

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
        page.text=newtext
        page.save(summary)

