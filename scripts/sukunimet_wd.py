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
            return urllib.request.urlopen(req, timeout=timeout).read().strip().decode('utf-8')
        except:
            print('Error while retrieving: %s' % (url))
            print('Retry in %s seconds...' % (sleep))
            time.sleep(sleep)
            sleep = sleep * 2
    return raw

def checkqcode(wtitle, itemqcode, lang):
    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    dictionary = itemfound.get()

    isLastName = False
    instance_of = itemfound.claims.get('P31', [])
    for claim in instance_of:
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page")
            return False

        if (claim.getTarget().id == 'Q101352'):
            print("instance ok")
            isLastName = True

    isFinnishLabel = False
    isEnglishLabel = False
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

    isDescriptionMissing = True
    for dsc in itemfound.descriptions:
        description = itemfound.descriptions[dsc]
        if (description == "sukunimi" and dsc == 'fi'):
            isDescriptionMissing = False


    if (isFinnishLabel == False and isEnglishLabel == True and isLastName == True):
        print("label for finnish missing: ", wtitle)
        copy_labels = {"fi": wtitle}
        copy_descr = {"fi": "sukunimi"}
        itemfound.editLabels(labels=copy_labels, summary="Adding missing labels.")
        if (isDescriptionMissing == True):
            itemfound.editDescriptions(copy_descr, summary="Adding missing descriptions.")
        itemfound.get()
        return True
 
    # exact match found
    if (isFinnishLabel == True and isLastName == True):
        return True
    return False
    #return isFinnishLabel

# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L706
def searchname(wtitle, lang='fi'):

    searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&format=xml' % (urllib.parse.quote(wtitle), lang)
    raw = getURL(searchitemurl)
    #print(searchitemurl.encode('utf-8'))

    if not '<search />' in raw:
        m = re.findall(r'id="(Q\d+)"', raw)
        
        numcandidates = '' #do not set to zero
        numcandidates = len(m)
        print("Found %s candidates" % (numcandidates))
        
        for itemfoundq in m:
            # NOTE! server gives suggestions, verify it matches!
            print("potential match exists ", str(itemfoundq))
            if (checkqcode(wtitle, itemfoundq, lang) == True):
                return str(itemfoundq)

    print("not found", wtitle)
    return ''


# see: https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Labels
def addname(par_name):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()

    new_descr = {"fi": "sukunimi", "en": "family name"}
    newitemlabels = {'fi': par_name,'en': par_name}

    print('Creating a new item...', par_name)

    #create item
    newitem = pywikibot.ItemPage(repo)

    #for key in newitemlabels:
        #newitem.editLabels(labels={key: newitemlabels[key]},
            #summary="Setting label: {} = '{}'".format(key, newitemlabels[key]))
        
    #for key in new_descr:
        #newitem.editDescriptions({key: new_descr[key]},
            #summary="Setting description: {} = '{}'".format(key, new_descr[key]))
        
    data = {"labels": {"en": par_name, "fi": par_name},
    "descriptions": {"en": "family name", "fi": "sukunimi"}}
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    newitem.get()

    print('Adding properties...')

    # instance of
    if not 'P31' in newitem.claims:
        print("Adding claim: family name")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q101352') # family name
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')
        
    # writing system
    if not 'P282' in newitem.claims:
        print("Adding claim: writing system")
        claim = pywikibot.Claim(repo, 'P282')
        target = pywikibot.ItemPage(repo, 'Q8229') # latin alphabet
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')
        
    # native label
    #if not 'P1705' in newitem.claims:
        #print("Adding claim: native label")
        #claim = pywikibot.Claim(repo, 'P1705')
        #claim.setTarget(par_name) # + qualifer lang Q1412

            #l_claim = pywikibot.Claim(wikidata_site, 'P???', is_reference=False, is_qualifier=True)
            #q_target = pywikibot.ItemPage(wdsite, 'Q1412')
            #l_claim.setTarget(q_target)
            #claim.addQualifier(l_claim)
        
        #newitem.addClaim(claim)#, summary='Adding 1 claim')

    nid = newitem.getID()
    print('All done', nid)
    return nid

# main()

if __name__ == "__main__":
    cache = CachedNames()
    cache.opencachedb()
    
    names = cache.getnames()
    for name in names:
        qc = names[name]
        if (qc == None):
            if (name.find("'") > 0):
                print("skipping name", name)
                continue
            qid = searchname(name)
            if (len(qid) == 0):
                qid = addname(name)
                cache.updatecache(name, qid)
                #exit(1) ## TEST
            else:
                cache.updatecache(name, qid)
    
