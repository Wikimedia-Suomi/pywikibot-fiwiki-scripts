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

    # some other text after url?
    indexend = oldsource.find(",")
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
    #print("DEBUG: source url is: " + source)

    protolen = len("http://")
    index = source.find("http://")
    if (index < 0):
        protolen = len("https://")
        index = source.find("https://")
        if (index < 0):
            # no url in string
            return ""

    indexproto = index+protolen

    # try to find space or something
    indexend = source.find(" ", indexproto)
    if (indexend > 0):
        source = source[:indexend]

    # wiki-markup end of url
    indexend = source.find("]", indexproto)
    if (indexend > 0):
        source = source[:indexend]

    if (index > 0):
        # finally, if there was anything before start of url
        # -> strip to just url 
        #indexend = len(source)-1 # just use string length
        source = source[index:]

    #print("DEBUG: found source url: " + source)
    return source

# input: kuvakokoelmat.fi url
# output: old format id
def getkuvakokoelmatidfromurl(source):
    # if there is human readable stuff in source -> strip to just url
    source = geturlfromsource(source)

    indexstart = source.find("kuvakokoelmat.fi")
    if (indexstart <= 0):
        indexstart = source.find("europeana.eu")
        if (indexstart <= 0):
            print("something went wrong, unexpected domain in: " + source)
            return ""
    source = source[indexstart:]
    
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
        # if the part after dot is a number -> leave it
        remainder = kkid[indexlast+1:]
        if (remainder.isnumeric() == False):
            # if it is image type extension -> remove it (not part of ID)
            kkid = kkid[:indexlast]
    return kkid

# just for documentation purposes
def getidfromeuropeanaurl(source):
    mid = getkuvakokoelmatidfromurl(source)
    if (len(mid) > 0):
        # urls may have session/tracking parameters in some cases -> remove trash from end
        mid = stripid(mid)
    
    # should be like M012_HK10000_944
    # note: in some cases with multiple underscores last on should be changed to dash
    # such as in HK19321130:115-1877
    # otherwise underscore to colon works
    if (len(mid) > 0 and mid.startswith("M012")):
        mid = mid.replace("_", ":")
        #musketti = "musketti." + mid[:index] + ":" + mid[index+1:]
        musketti = "musketti." + mid
        return musketti
    return "" # failed parsing

# if there's garbage in id, strip to where it ends
def leftfrom(string, char):
    index = string.find(char)
    if (index > 0):
        return string[:index]

    return string

# input: old format "HK"-id, e.g. HK7155:219-65-1
# output: newer "musketti"-id, e.g. musketti.M012%3AHK7155:219-65-1
def convertkuvakokoelmatid(kkid):
    if (len(kkid) == 0):
        print("empty kuvakokoelmat id ")
        return ""

    # verify
    if (kkid.startswith("HK") == False and kkid.startswith("JOKA") == False
        and kkid.startswith("SUK") == False and kkid.startswith("SMK") == False 
        and kkid.startswith("KK") == False and kkid.startswith("VKK") == False 
        and kkid.startswith("1") == False):
        print("does not start appropriately: " + kkid)
        return ""

    if (kkid.startswith("HK") == True):
        index = kkid.find("_")
        if (index < 0):
            print("no underscores: " + kkid)
            return ""
        # one underscore to colon
        # underscores to dash
        # add prefix
        kkid = kkid[:index] + ":" + kkid[index+1:]
        #kkid = kkid.replace("_", "-")
        kkid = kkid.replace("_", ":") # some images seem to need colon?

    if (kkid.startswith("JOKA") == True):
        # if there is one underscore -> set to colon
        #kkid = kkid.replace("_", ":")
        # if there is two -> only set the latter one to colon and leave first as underscore
        indexlast = kkid.rfind("_", 0, len(kkid)-1)
        if (indexlast > 0):
            kkid = kkid[:indexlast] + ":" + kkid[indexlast+1:]
            
    if (kkid.startswith("SUK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("SMK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("KK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("VKK") == True):
        kkid = kkid.replace("_", ":")

    if (kkid.startswith("1") == True):
        kkid = "HK" + kkid
        kkid = kkid.replace("_", ":")

    # url may have something else in it -> remove it
    kkid = leftfrom(kkid, "#")
    kkid = leftfrom(kkid, "]")
    #kkid = stripid(kkid)

    musketti = "musketti.M012:" + kkid
    return musketti

def getnewsourcefromoldsource(srcvalue):
    # if there is human readable stuff in source -> strip to just url
    srcvalue = geturlfromsource(srcvalue)

    if (srcvalue.find("kuvakokoelmat.fi") > 0):
        kkid = getkuvakokoelmatidfromurl(srcvalue)
        newfinnaid = convertkuvakokoelmatid(kkid)
        if (len(newfinnaid) > 0):
            return urllib.parse.quote(newfinnaid) # quote for url
            #newsourceurl = "https://www.finna.fi/Record/" + newfinnaid
        return "" # failed to parse, don't add anything

    if (srcvalue.find("europeana.eu") > 0):
        eusource = parsesourcefromeuropeana(srcvalue)
        if (len(eusource) < 0):
            print("Failed to retrieve source from europeana")
            return "" # failed to parse, don't add anything

        # museovirasto.finna.fi or museovirasto.<id>
        if (eusource.find("museovirasto") > 0 or eusource.find("finna") > 0):
            # ok, we might use this as-is
            indexrec = eusource.find("/Record/")
            if (indexrec >= 0):
                indexrec = indexrec + len("/Record/")
                newid = eusource[indexrec:]
                newid = stripid(newid)
                print("Found finna id from europeana: " + newid)
                return newid
        
        # if url has musketti-id: europeana.eu/%/M012..
        mid = getidfromeuropeanaurl(srcvalue)
        if (len(mid) <= 0):
            return "" # failed to parse, don't add anything
        print("DEBUG: europeana-link had id: " + mid)
        return mid
        
    if (srcvalue.find("finna.fi") > 0):
        # finna.fi url
        return getidfromoldsource(srcvalue)

    return ""

def requestpage(pageurl):

    page = ""

    try:
        headers={'User-Agent': 'pywikibot'}
        #response = requests.get(url, headers=headers, stream=True)
    
        request = urllib.request.Request(pageurl, headers=headers)
        print("request done: " + pageurl)

        response = urllib.request.urlopen(request)
        if (response.readable() == False):
            print("response not readable")
            return ""

        htmlbytes = response.read()
        page = htmlbytes.decode("utf8")

        #print("page: " + finnapage)
        return page # page found
        
    except urllib.error.HTTPError as e:
        print(e.__dict__)
        return ""
    except urllib.error.URLError as e:
        print(e.__dict__)
        return ""
    #except:
        #print("failed to retrieve page")
        #return ""

    return ""

# fetch metapage from finna and check if we have a valid url
# since we might have obsolete ID.
def getfinnapage(finnaurl):
    finnapage = requestpage(finnaurl)
    if (len(finnapage) > 0):
        return True
    return False


# input: source reported by commons (url to europeana eu)
def parsesourcefromeuropeana(commonssource):
    if (commonssource.find("europeana.eu") < 0):
        print("Not europeana url: " + commonssource)
        return ""

    eupage = requestpage(commonssource)
    if (len(eupage) <= 0):
        return ""

    attrlen = len('class="data-provider"')
    indexdp = eupage.find('class="data-provider"')
    if (indexdp < 0):
        return ""
    indexdp = eupage.find('>', indexdp+attrlen)
    if (indexdp < 0):
        return ""
    attrlen = len('href="')
    indexdp = eupage.find('href="', indexdp+1)
    if (indexdp < 0):
        return ""
    indexend = eupage.find('"', indexdp+attrlen)
    if (indexend < 0):
        return ""

    # this should get the actual source of image as it is set in europeana        
    eusource = eupage[indexdp+attrlen:indexend]
    if (len(eusource) <= 0):
        print("Failed to parse source from europeana: " + commonssource)
        return ""

    # this should be the source reported in europeana    
    print("europeana page source: " + eusource)
    return eusource


# filter blocked images that can't be updated for some reason
def isblockedimage(page):
    pagename = str(page)

    # no blocking currently here
    return False

# get pages immediately under cat
# and upto depth of 1 in subcats
def getcatpages(pywikibot, commonssite, maincat, recurse=False):
    final_pages = list()
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(commonssite.categorymembers(cat))

    for page in pages:
        if isblockedimage(page) == False:
            if page not in final_pages:
                final_pages.append(page)


    # no recursion by default, just get into depth of 1
    if (recurse == True):
        subcats = list(cat.subcategories())
        for subcat in subcats:
            subpages = commonssite.categorymembers(subcat)
            for subpage in subpages:
                if isblockedimage(subpage) == False: 
                    if subpage not in final_pages: # avoid duplicates
                        final_pages.append(subpage)

    return final_pages

def getlinkedpages(pywikibot, commonssite, linkpage):
    listpage = pywikibot.Page(commonssite, linkpage)  # The page you're interested in

    pages = list()
    # Get all linked pages from the page
    for linked_page in listpage.linkedPages():
        if isblockedimage(linked_page) == False: 
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

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Simo Rista", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Vyborg in the 1930s")

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist2')
pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/sakuvat')

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/europeana-kuvat')


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
        if template.name.matches("Information") or template.name.matches("information") or template.name.matches("Photograph") or template.name.matches("photograph") or template.name.matches("Artwork") or template.name.matches("artwork") or template.name.matches("Art Photo") or template.name.matches("art photo"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                
                if (srcvalue.find("profium.com") > 0):
                    print("WARN: unusable url (redirector) in: " + page.title() + ", source: " + srcvalue)
                    break
                if (srcvalue.find("finna.fi") < 0 
                    and srcvalue.find("kuvakokoelmat.fi") < 0
                    and srcvalue.find("europeana.eu") < 0):
                    print("unknown source, skipping")
                    break
                if (srcvalue.find("finna.fi") > 0 and srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                pageurltemp = geturlfromsource(srcvalue)
                newsourcetext = ""
                newsourceid = getnewsourcefromoldsource(pageurltemp)
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
                if (srcvalue.find("finna.fi") < 0 
                    and srcvalue.find("kuvakokoelmat.fi") < 0
                    and srcvalue.find("europeana.eu") < 0):
                    print("unknown source, skipping")
                    break
                if (srcvalue.find("finna.fi") > 0 and srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                pageurltemp = geturlfromsource(srcvalue)
                newsourcetext = ""
                newsourceid = getnewsourcefromoldsource(pageurltemp)
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

