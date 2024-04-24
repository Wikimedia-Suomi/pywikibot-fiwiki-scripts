# Script creates wikidata item for last name.
#
# Usage:
# python3 
#
# 

import re
import sys
import pywikibot

import json
import psycopg2
#import sqlite3

from requests import get

import urllib
import urllib.request
import urllib.parse

def escapesinglequote(s):
    return s.replace("'", "''")

class CachedNames:
    def opencachedb(self):
        self.conn = psycopg2.connect("dbname=wikidb")
        cur = self.conn.cursor()

    def updatecache(self, lastname, qcode):

        sqlq = "UPDATE sukunimet SET qcode = '" + qcode + "' WHERE sukunimi = '" + lastname + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()


    def findbyname(self, lastname):
        sqlq = "SELECT sukunimi, qcode FROM sukunimet WHERE sukunimi = '" + lastname + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['sukunimi'] = row[0]
            dt['qcode'] = row[1]
            #print(dt)
            return dt

        return None

    def getnames(self):
        sqlq = "SELECT sukunimi, qcode FROM sukunimet"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        dt = dict()
        for row in rset:
            dt[row[0]] = row[1]
        return dt

# ----- /CachedNames


# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L42
def getURL(url, retry=True, timeout=30):
    raw = ''
    sleep = 10 # seconds
    maxsleep = 900
    #headers = {'User-Agent': 'pywikibot'}
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0' }
    req = urllib.request.Request(url, headers=headers)
    while retry and sleep <= maxsleep:
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except:
            print('Error while retrieving: %s' % (url))
            print('Retry in %s seconds...' % (sleep))
            time.sleep(sleep)
            sleep = sleep * 2
    return raw

def isItemLastName(item):
    isLastName = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page")
            return False # skip for now

        # family name
        if (claim.getTarget().id == 'Q101352'):
            print("instance ok", claim.getTarget().id)
            isLastName = True

        # "von something"
        if (claim.getTarget().id == 'Q66480858'):
            print("instance affixed name", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q106319018'):
            print("instance hyphenated surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q60558422'):
            print("instance compound surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q121493679'):
            print("instance surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q29042997'):
            print("instance double family name", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q56219051'):
            print("instance Mac of Mc prefix", claim.getTarget().id)
            isLastName = True
            
    return isLastName

# skip some where translitteration might cause issues
def skipByWritingSystem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # Han-sukunimi
        if (claim.getTarget().id == 'Q1093580'):
            return True

    writingsystem = item.claims.get('P282', [])
    for claim in writingsystem:
        
        # kiinan kirjoitusjärjestelmä
        if (claim.getTarget().id == 'Q8201'):
            return True
        
        # not latin alphabet
        if (claim.getTarget().id != 'Q8229'):
            return True

    return False


##     data = {"labels": {"en": par_name, "fi": par_name, "sv": par_name, "fr": par_name, "it": par_name, "de": par_name, "es": par_name, "pt": par_name},
#    "descriptions": {"en": "family name", "fi": "sukunimi", "sv": "efternamn", "fr": "nom de famille", "it": "cognome", "de": "Familienname", "es": "apellido", "pt": "sobrenome"}}

def copylabels(wtitle, item):

    modifiedItem = False
    
    if "fi" in item.labels:
        label = item.labels["fi"]
        if (label != wtitle):
            # finnish label does not match -> wrong item?
            return False;
        
    # finnish label is not set -> don't modify (avoid mistakes)
    if "fi" not in item.labels:
        return False;

    # start with supported languages
    copy_labels = {}
    supportedLabels = "en", "fi", "sv", "fr", "it", "de", "es", "pt", "nl", "da", "nb", "nn", "et", "pl"
    for lang in supportedLabels:
        if lang not in item.labels:
            # example: "fi": "Virtanen"
            copy_labels[lang] = wtitle
    if (len(copy_labels) > 0):
        item.editLabels(labels=copy_labels, summary="Adding missing labels.")
        modifiedItem = True

    copy_descr = {}
    for lang in supportedLabels:
        if lang not in item.descriptions:
            if (lang == 'fi'):
                copy_descr["fi"] = "sukunimi"
            if (lang == 'en'):
                copy_descr ["en"] = "family name"
            if (lang == 'sv'):
                copy_descr["sv"] = "efternamn"
            if (lang == 'fr'):
                copy_descr["fr"] = "nom de famille"
            if (lang == 'it'):
                copy_descr["it"] = "cognome"
            if (lang == 'de'):
                copy_descr["de"] = "Familienname"
            if (lang == 'es'):
                copy_descr["es"] = "apellido"
            if (lang == 'pt'):
                copy_descr["pt"] = "sobrenome"
            if (lang == 'nl'):
                copy_descr["nl"] = "achternaam"
            if (lang == 'da'):
                copy_descr["da"] = "efternavn"
            if (lang == 'nb'):
                copy_descr["nb"] = "etternavn"
            if (lang == 'nn'):
                copy_descr["nn"] = "etternamn"
            if (lang == 'et'):
                copy_descr["et"] = "perekonnanimi"
            if (lang == 'pl'):
                copy_descr["pl"] = "nazwisko"

    if (len(copy_descr) > 0):
        item.editDescriptions(copy_descr, summary="Adding missing descriptions.")
        modifiedItem = True

    if (modifiedItem == True):
        item.get()
    return modifiedItem

def checkqcode(wtitle, itemqcode, lang):
    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return False

    dictionary = itemfound.get()

    if (skipByWritingSystem(itemfound) == True):
        print("skipping, writing system might cause mismatch ", itemqcode)
        return False

    isLastName = isItemLastName(itemfound)

    isFinnishLabelMissing = True
    isFinnishLabel = False
    isEnglishLabel = False
    isSwedishLabel = False
    print("item id, ", itemfound.getID())
    for li in itemfound.labels:
        label = itemfound.labels[li]
        if (label == wtitle and li != lang):
            print("found matching label for another language: ", li)
        
        if (label == wtitle and li == 'fi'):
            print("found exact matching label: ", label)
            isFinnishLabel = True

        if (label == wtitle and li == 'en'):
            print("found matching label: ", label)
            isEnglishLabel = True

        if (label == wtitle and li == 'sv'):
            print("found matching label: ", label)
            isSwedishLabel = True

        if (li == 'fi'):
            isFinnishLabelMissing = False


    isDescriptionMissing = True
    for dscl in itemfound.descriptions:
        description = itemfound.descriptions[dscl]
        if (dscl == 'fi'):
            isDescriptionMissing = False
            break

    if (isFinnishLabelMissing == True and (isEnglishLabel == True or isSwedishLabel == True) and isLastName == True):
        print("label for finnish missing: ", wtitle)
        copy_labels = {"fi": wtitle}
        copy_descr = {"fi": "sukunimi"}
        itemfound.editLabels(labels=copy_labels, summary="Adding missing labels.")
        if (isDescriptionMissing == True and isLastName == True):
            itemfound.editDescriptions(copy_descr, summary="Adding missing descriptions.")
        itemfound.get()
        return True
    #elif (isFinnishLabel == True and isLastName == True):
        #return copylabels(wtitle, itemfound)
 
    # exact match found
    if (isFinnishLabel == True and isLastName == True):
        return True
    return False
    #return isFinnishLabel

def getqcodesfromresponse(record):
    qcodes = list()
    if "search" in record:
        s = record["search"]
        if (len(s) > 0):
            for res in s:
                if "id" in res:
                    #print("id = ", res["id"])
                    qcodes.append(res["id"])
    return qcodes

# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L706
def searchname(wtitle, lang='fi'):

    qcodes = {}
    hasMoreItems = True
    contfrom = 0
    
    while (hasMoreItems == True):
        if (contfrom == 0):
            searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&limit=50&format=json' % (urllib.parse.quote(wtitle), lang)
        else:
            searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&continue=%s&limit=50&format=json' % (urllib.parse.quote(wtitle), lang, str(contfrom))
        #print(searchitemurl.encode('utf-8'))
        resp = getURL(searchitemurl).strip().decode('utf-8')

        record = json.loads(resp) #.json()

        if (record['success'] != 1):
            print("not successful")
        elif (record['success'] == 1):
            print("success")
            
        # if there is search-continue="7" results are not complete..
        if "search-continue" in record:
            print("continue search from: ", record['search-continue'])
            contfrom = record['search-continue']
        else:
            hasMoreItems = False

        qcodestmp = getqcodesfromresponse(record)
        for qc in qcodestmp:
            qcodes.append(qc)

    if (len(qcodes) == 0):
        print("no codes found for", wtitle)
        return ''
        
    for itemfoundq in qcodes:
        # NOTE! server gives suggestions, verify it matches!
        print("potential match exists ", str(itemfoundq))
        if (checkqcode(wtitle, itemfoundq, lang) == True):
            return str(itemfoundq)

    print("not found", wtitle)
    return ''

def addproperties(repo, wditem):
    # instance of
    if not 'P31' in wditem.claims:
        print("Adding claim: family name")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q101352') # family name
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')
        
    # writing system
    if not 'P282' in wditem.claims:
        print("Adding claim: writing system")
        claim = pywikibot.Claim(repo, 'P282')
        target = pywikibot.ItemPage(repo, 'Q8229') # latin alphabet
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')
        
    # native label
    #if not 'P1705' in wditem.claims:
        #print("Adding claim: native label")
        #claim = pywikibot.Claim(repo, 'P1705')
        #claim.setTarget(par_name) # + qualifer lang Q1412

            #l_claim = pywikibot.Claim(wikidata_site, 'P???', is_reference=False, is_qualifier=True)
            #q_target = pywikibot.ItemPage(wdsite, 'Q1412')
            #l_claim.setTarget(q_target)
            #claim.addQualifier(l_claim)
        
        #wditem.addClaim(claim)#, summary='Adding 1 claim')

    # attested in 
    if not 'P5323' in wditem.claims:
        print("Adding claim: attested in")
        claim = pywikibot.Claim(repo, 'P5323')
        target = pywikibot.ItemPage(repo, 'Q18694404') # väestötietojärjestelmä
        claim.setTarget(target)
        wditem.addClaim(claim)#, summary='Adding 1 claim')

    #elif 'P5323' in wditem.claims:
        #claim = pywikibot.Claim(repo, 'P5323')
        #if (claim.getTarget().id == Q117799914): # väestötietojärjestelmä Suomessa
            #target = pywikibot.ItemPage(repo, 'Q18694404') # väestötietojärjestelmä
            #claim.setTarget(target)
        #wditem.addClaim(claim)#, summary='Adding 1 claim')



# see: https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Labels
def addname(par_name):
    if (len(par_name) == 0):
        return None

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()

    print('Creating a new item...', par_name)

    #create item
    newitem = pywikibot.ItemPage(repo)

    #newitemlabels = {'fi': par_name,'en': par_name}
    #for key in newitemlabels:
        #newitem.editLabels(labels={key: newitemlabels[key]},
            #summary="Setting label: {} = '{}'".format(key, newitemlabels[key]))
        
    #new_descr = {"fi": "sukunimi", "en": "family name"}
    #for key in new_descr:
        #newitem.editDescriptions({key: new_descr[key]},
            #summary="Setting description: {} = '{}'".format(key, new_descr[key]))

    data = {"labels": {"en": par_name, "fi": par_name, "sv": par_name, "fr": par_name, "it": par_name, "de": par_name, "es": par_name, "pt": par_name},
    "descriptions": {"en": "family name", "fi": "sukunimi", "sv": "efternamn", "fr": "nom de famille", "it": "cognome", "de": "Familienname", "es": "apellido", "pt": "sobrenome"}}
    
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    newitem.get()

    print('Adding properties...')

    addproperties(repo, newitem)

    nid = newitem.getID()
    print('All done', nid)
    return nid

def checkproperties(wtitle, itemqcode):
    if (len(itemqcode) == 0):
        return False

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return False
    
    dictionary = itemfound.get()

    isLastName = isItemLastName(itemfound)
    if (isLastName == False):
        print("code is not for a last name ", itemqcode)
        return False

    if (skipByWritingSystem(itemfound) == True):
        print("skipping, writing system might cause mismatch ", itemqcode)
        return False
    
    print("Checking Labels for ", wtitle)
    copylabels(wtitle, itemfound)
    print("Labels checked for ", wtitle)
    
    addproperties(repo, itemfound)
    print("Properties checked for ", itemqcode)
    return True


def skipbyqcode(qc):
    codes = {"Q55221557", "Q2354177", "Q37036807", "Q13391907", "Q21450308", "Q42293799", "Q21511080", "Q125380726"}
    if qc in codes:
        return True
    
    return False

def skipbyname(name):
    names = { "Tan", "Zhu", "Jakovlev" }
    if (name.find("'") > 0):
        return True
    if name in names:
        return True

    return False


# main()

if __name__ == "__main__":
    cache = CachedNames()
    cache.opencachedb()
    
    names = cache.getnames()
    for name in names:
        qc = names[name]
        if (qc == None):
            if (skipbyname(name) == True):
                print("skipping by name", name)
                continue
            qid = searchname(name)
            if (len(qid) == 0):
                qid = addname(name)
                cache.updatecache(name, qid)
            else:
                cache.updatecache(name, qid)
        else:
            if (skipbyname(name) == True):
                print("skipping by name", name)
                continue
            if (skipbyqcode(qc) == True):
                print("skipping by qcode", qc)
                continue
            if (checkproperties(name, qc) == False):
                # not a last name -> reset qcode and try again later
                cache.updatecache(name, '')
    
