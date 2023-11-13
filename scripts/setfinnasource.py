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
    indexend = oldsource.find(")")
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

# link might have "?id=<id>" which we handle here, might have:
# - "/Cover/Show?id="
# - "/Record/DownloadFile?id="
def getidfromoldsource(oldsource):
    strlen = len("id=")
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return ""

    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)

# for: "Record/<id>" 
def getrecordid(oldsource):
    # not suitable here, use getlinksourceid()
    indexid = oldsource.find("/Record/DownloadFile")
    if (indexid > 0):
        return ""
    
    strlen = len("/Record/")
    indexid = oldsource.find("/Record/")
    if (indexid < 0):
        return ""
    oldsource = oldsource[indexid+strlen:]
    return stripid(oldsource)

# commons source information
def findurlbeginfromsource(source, begin):
    # just skip it
    if (len(source) == 0):
        return -1
    
    indexend = len(source)-1
    indexbegin = begin
    while (indexbegin < indexend):
        # may have http or https,
        # also there may be encoded url given to 
        # redirecting services as parameters
        # 
        index = source.find("http", indexbegin)
        if (index < 0):
            # no url proto in string
            return -1

        if ((indexend - index) < 8):
            # nothing usable remaining in string, partial url left unfinished?
            return -1

        # should have http:// or https:// to be valid:
        # check that we have :// since url may given as encoded parameter to another
        if (source[index:index+7].lower() == "http://" 
            or source[index:index+8].lower() == "https://"):
            # should be usable url?
            return index
            
        # otherwise look for another
        indexbegin = index + 7

    # not found
    return -1

# commons source may have human readable stuff in it,
# it may be mixed with wiki-markup and html as well:
# try to locate where url ends from that soup
def findurlendfromsource(source, indexbegin=0):
    indexend = len(source)-1

    i = indexbegin
    while i < indexend:
        # space after url or between url and description
        if (source[i] == " " and i < indexend):
            indexend = i
            
        # wikimarkup after url?
        # end of url markup?
        if (source[i] == "]" and i < indexend):
            indexend = i
        # template parameter after url?
        if (source[i] == "|" and i < indexend):
            indexend = i
        # end of template with url in it?
        if (source[i] == "}" and i < indexend):
            indexend = i
        # start of template after url?
        if (source[i] == "{" and i < indexend):
            indexend = i

        # html after url?
        if (source[i] == "<" and i < indexend):
            indexend = i

        # some human-readable text after url?
        if (source[i] == "," and i < indexend):
            indexend = i
        if (source[i] == ")" and i < indexend):
            indexend = i

        # just newline after url
        if (source[i] == "\n" and i < indexend):
            indexend = i
        i += 1

    return indexend

# commons source may have human readable stuff in it,
# also may have multiple urls (old and new),
# parse to plain urls
def geturlsfromsource(source):
    #print("DEBUG: source is: " + source)
    
    urllist = list()
    index = 0
    while (index >= 0 and index < len(source)):
        index = findurlbeginfromsource(source, index)
        if (index < 0):
            break
            
        indexend = findurlendfromsource(source, index)
        url = source[index:indexend]
        #print("DEBUG: source has url: " + url)
        urllist.append(url)
        index = indexend

    #print("DEBUG: urllist: ", urllist)
    return urllist

# input: kuvakokoelmat.fi url
# output: old format id
def getkuvakokoelmatidfromurl(source):
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
            # note: in some cases there maybe be a file extension, 
            # but also there may be a part of the ID in some cases..
            if (remainder.lower() == "jpg" or remainder.lower() == "jpeg"
                or remainder.lower() == "png" or remainder.lower() == "tiff" or remainder.lower() == "tif"):
                # if it is image type extension -> remove it (not part of ID)
                kkid = kkid[:indexlast]
    return kkid

# just for documentation purposes
def getidfromeuropeanaurl(source):
    if (source.find("europeana.eu") < 0):
        # not found?
        return ""

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
    if "kuvakokoelmat.fi" in srcvalue:
        kkid = getkuvakokoelmatidfromurl(srcvalue)
        newfinnaid = convertkuvakokoelmatid(kkid)
        if (len(newfinnaid) > 0):
            return urllib.parse.quote(newfinnaid) # quote for url
            #newsourceurl = "https://www.finna.fi/Record/" + newfinnaid
        return "" # failed to parse, don't add anything

    if "europeana.eu" in srcvalue:
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
        
    if "finna.fi" in srcvalue:
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
    except UnicodeDecodeError as e:
        print(e.__dict__)
        return ""
    except UnicodeEncodeError as e:
        print(e.__dict__)
        return ""
    except http.client.InvalidURL as e:
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
    if (commonssource.find("proxy.europeana.eu") >= 0):
        print("can't use proxy (might direct to binary image): " + commonssource)
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

# try to find musketti-ID from flickr,
# expecting to find ID-line like: HK6985:15 / Historian kuvakokoelma
def parsemuskettifromflickr(flickrsource):
    if (flickrsource.find("flickr.com") < 0):
        print("Not flickr url: " + flickrsource)
        return ""

    flickrpage = requestpage(flickrsource)
    if (len(flickrpage) <= 0):
        return ""

    elemname = '<h2 class=" meta-field photo-desc "'
    indexdps = flickrpage.find(elemname)
    if (indexdps < 0):
        return ""
    indexdpe = flickrpage.find('</h2>', indexdps+len(elemname))
    if (indexdpe < 0):
        # bugged page, can't continue
        return ""
    index = flickrpage.find('<p>', indexdps+len(elemname))
    while (index >= 0 and index <= indexdpe):
        # p-element content
        inel = flickrpage.find('>', index)
        inele = flickrpage.find('<', inel)
        tmpstr = flickrpage[inel+1:inele]
        if (tmpstr.startswith("HK")):
            return tmpstr
        index = flickrpage.find('<p>', index)
    return ""

# few checks on what the source value has
def checkcommonsparsource(srcvalue, title):
    if (srcvalue.find("profium.com") > 0):
        print("WARN: unusable url (redirector) in: " + title + ", source: " + srcvalue)
        return False
    if (srcvalue.find("finna.fi") < 0 
        and srcvalue.find("kuvakokoelmat.fi") < 0
        and srcvalue.find("europeana.eu") < 0):
        print("unknown source, skipping")
        return False
    return True

# if there is /Record/ but not /Record/DownloadFile
# -> ok
# otherwise, add normal viewing link to metapage
def checkcommonsforfinnadownload(srcvalue):
    index = srcvalue.find("finna.fi/Record/DownloadFile")
    if (index >= 0):
        print("DEBUG: has a Finna download-link")
        return True
    return False

# normal record has /Record/<id>
# but downloads have Record/DownloadFile/?id=<id>
# so they need different handling
def isNormalFinnaRecord(srcvalue):
    index = srcvalue.find("finna.fi/Record/")
    if (index < 0):
        return False
    
    index += len("finna.fi/Record/")
    tmplen = len("DownloadFile")
    tmpstr = srcvalue[index:index+tmplen]
    if (tmpstr == "DownloadFile"):
        # record with download link instead of id -> different parsing
        return False
    return True

# url in the form https://www.flickr.com/photos/museovirastonkuvakokoelmat/
def isFlickrCollection(srcvalue):
    index = srcvalue.find("flickr.com")
    if (index < 0):
        return False
    index = srcvalue.find("museovirastonkuvakokoelmat/")
    if (index < 0):
        return False
    
    return True
    # id at end of url, can we use it?
    #index += len("museovirastonkuvakokoelmat/")
    #tmpstr = srcvalue[index:]
    #if (tmpstr.endswith("\n")):
        #tmpstr = tmpstr[:len(tmpstr)-1]
    

def hasMetapageInUrls(urllist, title):
    for pageurltemp in urllist:
        # check for normal finna record, unless there's download-link handle that
        if (isNormalFinnaRecord(pageurltemp) == True):
            # no need to do anything here
            print("already has metapage link, skipping: " + title)
            return True
        # download-url handling
        #if (checkcommonsforfinnadownload(pageurltemp) == True):
    return False

def isSupportedCommonsTemplate(template):
    #print("DEBUG commons template: ", template.name)
    name = template.name.lower()
    name = leftfrom(name, "\n") # mwparserfromhell is bugged
    if (name == "information" 
        or name == "photograph" 
        or name == "artwork" 
        or name == "art photo"):
        return True
    #print("DEBUG: not supported template: ", name)
    return False

def getSourceFromCommonsTemplate(template):
    if template.has("Source"):
        return template.get("Source")
    if template.has("source"):
        return template.get("source")
    return None

def getAccessionFromCommonsTemplate(template):
    if template.has("accession number"):
        return template.get("accession number")
    if template.has("Id"):
        return template.get("Id")
    if template.has("id"):
        return template.get("id")
    return None

def getFlickrCollectionFromPar(par):
    srcvalue = str(par.value)
    urllist = geturlsfromsource(srcvalue)
    for pageurltemp in urllist:
        if (isFlickrCollection(pageurltemp) == True):
            return pageurltemp
    return ""

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

# recurse upto given depth:
# 0 for no recursion (only those directly in category)
# 1 is for one level on subcats
# 2 is for two levels and so on
def getpagesrecurse(pywikibot, commonssite, maincat, depth=1):
    #final_pages = list()
    cat = pywikibot.Category(commonssite, maincat)
    pages = list(cat.articles(recurse=depth))
    return pages

# list of pages with links listed in a page 
def getlinkedpages(pywikibot, commonssite, linkpage):
    listpage = pywikibot.Page(commonssite, linkpage)  # The page you're interested in

    pages = list()
    # Get all linked pages from the page
    for linked_page in listpage.linkedPages():
        if isblockedimage(linked_page) == False: 
            if linked_page not in pages: # avoid duplicates
                pages.append(linked_page)

    return pages

# just catch exceptions
def getfilepage(pywikibot, page):
    try:
        return pywikibot.FilePage(page)
    except:
        print("WARN: failed to retrieve filepage: " + page.title())

    return None

# ------ main()

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()

# get list of pages upto depth of 1 
#pages = getcatpages(pywikibot, commonssite, "Category:Kuvasiskot", True)
#pages = getcatpages(pywikibot, commonssite, "Professors of University of Helsinki", True)

#pages = getcatpages(pywikibot, commonssite, "Historians from Finland", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Daniel Nyblin")
#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Simo Rista", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Heritage Agency", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by photographer from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:People of Finland by year", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Painters from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Winter War", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Lotta Svärd", True)

#pages = getcatpages(pywikibot, commonssite, "Category:History of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Files from the Finnish Aviation Museum")

#pages = getcatpages(pywikibot, commonssite, "Category:Monuments and memorials in Helsinki", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Historical images of Vyborg", True)

#pages = getcatpages(pywikibot, commonssite, "Category:Architects from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Artists from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Musicians from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Composers from Finland", True)
#pages = getcatpages(pywikibot, commonssite, "Category:Conductors from Finland", True)

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Companies of Finland", 4)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:People of Finland by occupation", 2)

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filelist2')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat.fi')
#pages = getlinkedpages(pywikibot, commonssite, 'User:FinnaUploadBot/kuvakokoelmat2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/sakuvat')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/europeana-kuvat')

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp1')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp2')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp3')
#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/finnalistp4')

#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Helge Heinonen")
#pages = getcatpages(pywikibot, commonssite, "Category:Mayors of Helsinki")


pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filesfromip')

rowcount = 0
#rowlimit = 10

print("Pages found: " + str(len(pages)))

for page in pages:
    rowcount += 1

    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    # try to catch exceptions and return later
    filepage = getfilepage(pywikibot, page)
    if (filepage == None):
        continue
    if filepage.isRedirectPage():
        continue    

    newsourceurl = ""
    changed = False
    oldtext=page.text

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")

    wikicode = mwparserfromhell.parse(page.text)
    
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        if (isSupportedCommonsTemplate(template) == True):
            
            finnaidAcc = ""
            paracc = getAccessionFromCommonsTemplate(template)
            if (paracc != None):
                # if accession has finna-url but source doesn't 
                # -> try parse id from acc now
                accurls = geturlsfromsource(str(paracc.value))
                for urltemp in accurls:
                    finnaidAcc = getrecordid(urltemp)
                    if (len(finnaidAcc) > 0):
                        print("DEBUG: found fnnna id in accession: ", finnaidAcc)
                        break
                    
            
            # TODO: id-field could have correct finna-source,
            # or it might have flickr-link. 
            # if it is from flickr, it might have different url in source.
            # Musketti-images in flickr are also in Finna, so try to find the ID.
            
            # TODO: flickr does not allow bot-access to the pages?
            #accpar = getAccessionFromCommonsTemplate(template)
            #if (accpar != None):
                #flink = getFlickrCollectionFromPar(accpar)
                #if (flink != ""):
                    #musketti = parsemuskettifromflickr(flink)
                    #print("DEBUG: musketti-id from flickr: ", musketti)

           
            par = getSourceFromCommonsTemplate(template)
            if (par != None):
                srcvalue = str(par.value)

                urllist = geturlsfromsource(srcvalue)
                if (hasMetapageInUrls(urllist, page.title()) == True):
                    # already has metapage -> skip
                   break

                for pageurltemp in urllist:
                    print("DEBUG: url in source: ", pageurltemp)

                    # if commons has flickr as source,
                    # try to find Finna-ID from flickr description
                    # TODO: flickr does not allow bot-access to the pages?
                    #if (isFlickrCollection(pageurltemp) == True):
                        #musketti = parsemuskettifromflickr(pageurltemp)
                        #print("DEBUG: musketti-id from flickr: ", musketti)

                    if (len(finnaidAcc) == 0 
                        and checkcommonsparsource(pageurltemp, page.title()) == False):
                        continue # skip, see if there's another usable url in source

                    newsourcetext = ""
                    newsourceid = getnewsourcefromoldsource(pageurltemp)
                    if (len(newsourceid) == 0 and len(finnaidAcc) > 0):
                        newsourceid = finnaidAcc
                    if (len(newsourceid) > 0):
                        newsourceurl = getnewfinnarecordurl(newsourceid)
                        if (len(newsourceurl) > 0):
                            newsourcetext = getnewsourceforfinna(newsourceurl, newsourceid)
                        if (newsourcetext != srcvalue and len(newsourcetext) > 0):
                            # remove newline from existing before appending
                            if (srcvalue.endswith("\n")):
                                srcvalue = srcvalue[:len(srcvalue)-1]
                            par.value = srcvalue + newsourcetext
                            changed = True
            #else:
                #print("DEBUG: no source par found")

 
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

