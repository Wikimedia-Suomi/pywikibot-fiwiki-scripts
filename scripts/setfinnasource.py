# Purpose: add metapage to source on pictures from finna
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
import urllib
from urllib.request import urlopen

from http.client import InvalidURL
#import HTTPException

import urllib3

# fix quoting of id:
# commons/python mangles if there are percent-signs by doubling them
# and doesn't handle slashes, also there are problems with umlauted characters.
#
# Note that we normally want to preserve unquoted form 
# and quoted form is used in the query url.
#
def quoteFinnaId(finnaid):
    # spaces may need to be:
    # plus signs (+) 
    # %20
    # or underscores, 
    # depending on id/source
    finnaid = finnaid.replace(" ", "_")

    finnaid = finnaid.replace("/", "%2F")

    # sls.%C3%96TA%2B112
    finnaid = finnaid.replace("Ö", "%C3%96")

    # %25C3%2596TA%2B112 -> undo mangling
    #finnaid = finnaid.replace("%25C3%2596", "%C3%96")

    # %252F -> undo mangling
    finnaid = finnaid.replace("%252F", "%2F")

    return finnaid

def getnewfinnarecordurl(finnarecordid):
    if (len(finnarecordid) == 0):
        return ""
    # quote the id for url
    #if (finnarecordid.find("%") < 0):
        #finnarecordid = urllib.parse.quote(finnarecordid)
    return "https://finna.fi/Record/" + finnarecordid

def getnewsourceforfinna(finnarecordurl, finnarecordid):
    if (len(finnarecordurl) == 0 or len(finnarecordid) == 0):
        return ""
    # quote the id for url
    #if (finnarecordurl.find("%") < 0):
        #finnarecordurl = urllib.parse.quote(finnarecordurl)
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
    indexend = oldsource.find("*")
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

    # in case of multiple lines in string, split at first
    indexend = oldsource.find("\n")
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
    indexend = len(source)

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

# remove pre- and post-whitespaces when mwparser leaves them
def trimlr(string):
    string = string.lstrip()
    string = string.rstrip()
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

# try to find new id to Finna from whatever source might be marked:
# if kuvakokoelmat -> try to generate new id from link (domain is down)
# if europeana -> try to retrieve original from the linked page
def getnewsourcefromoldsource(srcvalue):
    if (srcvalue.find("profium.com") > 0):
        print("WARN: unusable url (redirector), source: ", srcvalue)
        return "" # failed to parse, don't add anything

    if (srcvalue.find("finna.fi") < 0 
        and srcvalue.find("kuvakokoelmat.fi") < 0
        and srcvalue.find("europeana.eu") < 0):
        print("unknown source, skipping", srcvalue)
        return "" # failed to parse, don't add anything
    
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
    print("DEBUG: requesting url: ", pageurl)

    page = ""

    try:
        #if (pageurl.find("flickr.com") > 0):
            #headers={'User-Agent': 'finnabrowser'}
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
    except InvalidURL as e:
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
        print("WARN: failed to request page: " + flickrsource)
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

# does it have a collection that finna might support?
# url in the form https://www.flickr.com/photos/museovirastonkuvakokoelmat/
def isFlickrCollection(srcvalue):
    index = srcvalue.find("flickr.com")
    if (index < 0):
        return False
    
    index = srcvalue.find("museovirastonkuvakokoelmat")
    if (index > 0):
        return True
    index = srcvalue.find("valokuvataiteenmuseo")
    if (index > 0):
        return True
    index = srcvalue.find("finnishnationalgallery")
    if (index > 0):
        return True

    index = srcvalue.find("photos/108605878")
    if (index > 0):
        return True
    index = srcvalue.find("people/108605878")
    if (index > 0):
        return True
    
    # Svenska litteratursällskapet i Finland
    index = srcvalue.find("slsarkiva")
    if (index > 0):
        return True
    
    return False
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
    name = trimlr(name)
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
    if template.has("Accession number"):
        return template.get("Accession number")
    if template.has("accession number"):
        return template.get("accession number")
    if template.has("Id"):
        return template.get("Id")
    if template.has("id"):
        return template.get("id")
    return None

# accession number may hold:
# - bare link (http..)
# - wikilink with id ([http.. id])
# - bare id (HK.. / d1999..)
# -> convert to a usable ID with modern Finna
# also use method for flickr-links
def getIdFromAccessionValue(parval):
    # mwparser is bugged, remove spaces before or after
    parval = trimlr(parval)

    # bare link, not finna? -> no id directly..
    if (parval.startswith("http")):
        print("DEBUG: plain url for accession, ignored")
        return ""
    
    # wikimarkup with link and id (hopefully)
    # sometimes link may point to flickr but text is finna-id..
    if (parval.startswith("[http:")
        or parval.startswith("[https:")):
        #print("DEBUG: link-markup in accession, parsing", parval)

        # national gallery in flickr
        isFngflickr = False
        
        if (isFlickrCollection(parval) == False):
            print("DEBUG: not supported flickr collection:", parval)
            return ""
        if (parval.find("finnishnationalgallery") > 0):
            isFngflickr = True
        
        # end of url in wikimarkup
        indexend = parval.find("]")
        if (indexend < 0):
            print("DEBUG: failed to find link end:", parval)
            return ""
        if (isFngflickr == True):
            indexspace = parval.find(" ", 0, indexend)
            if (indexspace < 0):
                print("DEBUG: failed to find space:", parval)
                return ""
            parval = parval[indexspace+1:indexend]
            if (parval.startswith("HS")):
                indexcomma = parval.rfind(",")
                if (indexcomma > 0):
                    temp = parval[indexcomma+1:]
                    temp = stripid(temp)
                    temp = trimlr(temp)
                    if (temp.isnumeric() == True):
                        # if there is number like year -> not part of finna id
                        parval = parval[:indexcomma]
                    #else:
                        # if it is a string -> part of finna id
                parval = "fng_simberg." + parval.replace(" ", "_")
            print("DEBUG: accession number found in alien link:", parval)
            return parval
        else:
            # last space before descriptive text (might have multiple parts)
            indexspace = parval.rfind(" ", 0, indexend)
            if (indexspace < 0):
                print("DEBUG: failed to find space:", parval)
                return ""
            parval = parval[indexspace+1:indexend]

    # strip newline etc.
    parval = stripid(parval)
        
    # historical picture collection
    if (parval.startswith("HK")):
        parval = "musketti.M012:" + parval
        #parval = urllib.parse.quote(parval)
        print("DEBUG: accession number found in alien link:", parval)
        return parval

    # to uppercase
    parval = parval.upper()
    
    # finnish photographic museum
    if (parval.startswith("D1999") 
        or parval.startswith("D_2005") 
        or parval.startswith("D2000") 
        or parval.startswith("D2005") 
        or parval.startswith("D1970") 
        or parval.startswith("D200") 
        or parval.startswith("D19")
        or parval.startswith("D_")):
       
        #if d_ -> remove first underscore
        if (parval.startswith("D_")):
            parval = parval.replace("D_", "D")

        # convert first underscore to colon, rest to slash
        index = parval.find("_")
        if (index > 0):
            parval= parval[:index] + ":" + parval[index+1:]
            #parval = parval.replace("_", "/")
            parval = parval.replace("_", "%2F") # url-quoted

        parval = parval.replace("/", "%2F") # url-quoted

        #if (parval.startswith("D:")):
            #parval.replace("D:", "D")
        
        # finally, add prefix
        parval = "fmp." + parval
        print("DEBUG: accession number found in alien link:", parval)
        return parval

    print("DEBUG: not valid accession number:", parval)
    return ""

def getAccessionFromFilename(parval):
    # mwparser is bugged, remove spaces before or after
    parval = trimlr(parval)

    # filename from commons
    if (parval.startswith("File:") == False):
        return ""
        
    print("DEBUG: trying to find accession from filename:", parval)
    
    # to uppercase
    parval = parval.upper()
    
    indexbegin = parval.find("D19")
    if (indexbegin < 0):
        indexbegin = parval.find("D20")
        if (indexbegin < 0):
            return ""
    indexend = parval.find("(", indexbegin)
    if (indexend < 0):
        indexend = parval.find(")", indexbegin)

    if (indexend < 0):
        indexend = parval.rfind(".")
    parval = parval[indexbegin:indexend]
    print("DEBUG: accession from filename:", parval)

    # note: might be something else in some cases,
    # but most of the pictures found is missing this in filename
    if (parval.startswith("D1974")):
        if (parval.find("33") < 0):
            indexspace = parval.find(" ")
            if (indexspace > 0):
                parval = parval[:indexspace] + " 33 " + parval[indexspace+1:]
                print("DEBUG: added missing part:", parval)

    parval = trimlr(parval)
    parval = parval.replace(" ", "_") # some files have space..
    parval = parval.replace("-", "_") # some files have dash..
    if (parval.startswith("D_")):
        parval = parval.replace("D_", "D")

    index = parval.find("_")
    if (index > 0):
        parval= parval[:index] + ":" + parval[index+1:]
        #parval = parval.replace("_", "/")
        parval = parval.replace("_", "%2F") # url-quoted
    parval = parval.replace("/", "%2F") # url-quoted
    
    # finally, add prefix
    parval = "fmp." + parval
    print("DEBUG: accession from filename:", parval)
    return parval


# TODO:
# try to parse file history for potentially useful information,
# file might originate from finna but isn't marked in sources
# in which case url might be a comment in the history..
def parseCommonsHistory(filepage):
    #print("DEBUG: history:", filepage.latest_file_info)
    #print("DEBUG: history:", filepage.get_file_history())
    #hd = dict(filepage.get_file_history())
    #for k, v in hd:
        #print("DEBUG: history:", str(k), str(v))
    
    #for hist in filepage.get_file_history():
        #print("DEBUG: history:", str(hist), type(hist))
        #for k, v in hist.items()
        #for v in hist.values():
           # print("DEBUG: ", v)
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

#pages = getlinkedpages(pywikibot, commonssite, 'user:FinnaUploadBot/filesfromip')

#pages = getcatpages(pywikibot, commonssite, "Category:Juho Vennola")

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Photographs by Hugo Simberg", 2)
#pages = getcatpages(pywikibot, commonssite, "Category:Photographs by Hugo Simberg")

pages = getcatpages(pywikibot, commonssite, "Black and white photographs of Finland in the 1950s")

#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finnish Museum of Photography", 0)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Finnish Museum of Photography", 3)
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Files from the Finnish Museum of Photography", 0)


# many are from valokuvataiteenmuseo via flickr
#pages = getpagesrecurse(pywikibot, commonssite, "Category:Historical photographs of Helsinki by I. K. Inha", 1)
 
#pages = getcatpages(pywikibot, commonssite, "Category:Finnish Agriculture (1899) by I. K. Inha")
 

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

    # TODO:
    # try to parse history for potentially userful information?
    #parseCommonsHistory(filepage)

    newsourceurl = ""
    changed = False
    oldtext=page.text

    print(" ////////", rowcount, "/", len(pages), ": [ " + page.title() + " ] ////////")

    # try to find accession number from commons filename
    isFlickrSource = False
    finnaAccFromName = getAccessionFromFilename(page.title())
    if (len(finnaAccFromName) > 0):
        print("DEBUG: id from file name: ", finnaAccFromName)

    wikicode = mwparserfromhell.parse(page.text)
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        if (isSupportedCommonsTemplate(template) == True):
            
            finnaidAcc = ""
            paracc = getAccessionFromCommonsTemplate(template)
            if (paracc != None):
                # if accession has finna-url but source doesn't 
                # -> try parse id from url-parameters in acc now
                paracc_val = str(paracc.value)
                paracc_val = trimlr(paracc_val) # remove whitespace before and after
                #print("DEBUG: accession number value: ", paracc_val)
                
                accurls = geturlsfromsource(paracc_val)
                for urltemp in accurls:
                    finnaidAcc = getrecordid(urltemp)
                    if (len(finnaidAcc) > 0):
                        print("DEBUG: found fnnna id in accession: ", finnaidAcc)
                        break
                    #if (isFlickrCollection(urltemp) == True):
                        #print("DEBUG: flickr-collection in accession: ", urltemp)
                        #musketti = parsemuskettifromflickr(urltemp)
                        #print("DEBUG: musketti-id from flickr: ", musketti)
                        #finnaidAcc = getIdFromAccessionValue(paracc_val)

                # if there weren't urls in accession -> try to use id
                if (len(accurls) == 0 and len(finnaidAcc) == 0):
                    #print("DEBUG: parsing id from accession number value: ", paracc_val)
                    finnaidAcc = getIdFromAccessionValue(paracc_val)
                    if (len(finnaidAcc) > 0):
                        print("DEBUG: id from accession number: ", finnaidAcc)
            #else:
                #print("NOTE: could not find id or accession number")
            
            # TODO: id-field could have correct finna-source,
            # or it might have flickr-link. 
            # if it is from flickr, it might have different url in source.
            # Musketti-images in flickr are also in Finna, so try to find the ID.
            
           
            par = getSourceFromCommonsTemplate(template)
            if (par != None):
                srcvalue = str(par.value)
                #srcvalue = trimlr(srcvalue) # remove whitespace before and after

                # if source is flickr -> try to parse accession number from it
                # in case we don't have one from actual accession number
                if (len(finnaidAcc) == 0):
                    if (isFlickrCollection(srcvalue) == True):
                        print("DEBUG: flickr-collection in source: ", srcvalue)
                        isFlickrSource = True
                        finnaidAcc = getIdFromAccessionValue(srcvalue)
                        #print("DEBUG: musketti-id from flickr: ", finnaidAcc)
                        
                urllist = geturlsfromsource(srcvalue)
                if (hasMetapageInUrls(urllist, page.title()) == True):
                    # already has metapage -> skip
                   break

                for pageurltemp in urllist:
                    print("DEBUG: url in source: ", pageurltemp)
                    if (pageurltemp.find("profium.com") > 0):
                        #print("WARN: unusable url (redirector), source: ", pageurltemp)
                        continue
                    if (pageurltemp.find("elonet.finna.fi") > 0):
                        # elonet-service differs
                        continue

                    # if commons has flickr as source,
                    # try to find Finna-ID from flickr description
                    # TODO: flickr does not allow bot-access to the pages?
                    #if (isFlickrCollection(pageurltemp) == True):
                        #musketti = parsemuskettifromflickr(pageurltemp)
                        #print("DEBUG: musketti-id from flickr: ", musketti)

                    newsourcetext = ""
                    newsourceid = getnewsourcefromoldsource(pageurltemp)
                    if (len(newsourceid) == 0 and len(finnaidAcc) == 0 and len(finnaAccFromName) == 0):
                        print("DEBUG: no id in source, in accession or in filename")
                        continue
                    if (len(newsourceid) == 0 and len(finnaidAcc) > 0):
                        print("DEBUG: no id found in source, using id from accession: ", finnaidAcc)
                        newsourceid = finnaidAcc
                    if (len(newsourceid) == 0 and len(finnaAccFromName) > 0 and isFlickrSource == True):
                        print("DEBUG: no id found in source, using id from filename: ", finnaAccFromName)
                        newsourceid = finnaAccFromName
                    if (len(newsourceid) > 0):
                        #newsourceid = quoteFinnaId(newsourceid)
                        #print("DEBUG: using source id: ", newsourceid)
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

