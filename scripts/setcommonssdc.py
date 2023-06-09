# Purpose: add structured data to pictures from finna
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
from urllib.request import urlopen

import urllib.parse

def getlinkourceid(oldsource):
    strlen = len("id=")
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return ""
    indexend = oldsource.find("&", indexid)
    if (indexend < 0):
        indexend = oldsource.find(" ", indexid)
        if (indexend < 0):
            indexend = len(oldsource)-1
        
    return oldsource[indexid+strlen:indexend]

def getrecordid(oldsource):
    strlen = len("/Record/")
    indexid = oldsource.find("/Record/")
    if (indexid < 0):
        return ""
    indexend = oldsource.find(" ", indexid)
    if (indexend < 0):
        indexend = len(oldsource)-1
        
    return oldsource[indexid+strlen:indexend]

# ------ main()

# Accessing wikidata properties and items
wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata

# site = pywikibot.Site("fi", "wikipedia")
commonssite = pywikibot.Site("commons", "commons")
commonssite.login()
cat = pywikibot.Category(commonssite, "Category:Kuvasiskot")
pages = commonssite.categorymembers(cat)

rowcount = 1
rowlimit = 10

for page in pages:
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    filepage = pywikibot.FilePage(page)
    if filepage.isRedirectPage():
        continue    

    oldtext=page.text

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")
    rowcount += 1

    wikicode = mwparserfromhell.parse(page.text)
    templatelist = wikicode.filter_templates()

    finnaid = ""
    for template in wikicode.filter_templates():
        if template.name.matches("Information") or template.name.matches("Photograph"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                finnaid = getlinkourceid(srcvalue)
                if (finnaid == ""):
                    print("no id found: " + finnaid)
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        print("no record found: " + finnaid)
                    break

            if template.has("source"):
                par = template.get("source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                finnaid = getlinkourceid(srcvalue)
                if (finnaid == ""):
                    print("no id found: " + finnaid)
                    finnaid = getrecordid(srcvalue)
                    if (finnaid == ""):
                        print("no record found: " + finnaid)
                    break
 
    # kuvasiskot has "musketti" as part of identier, alternatively "museovirasto" may be used in some cases
    if (finnaid.find("musketti") < 0 and finnaid.find("museovirasto") < 0):
        print("Skipping. " + page.title() + " - not appropriate id: " + finnaid)
        continue
        
    print("finna ID found: " + finnaid)

    sourceurl = "https://www.finna.fi/Record/" + finnaid

    wditem = page.data_item()  # Get the data item associated with the page
    data = wditem.get()
    claims = data['statements']  # Get the item's current claims

    flag_add_source = False
    flag_add_collection = False
    flag_add_finna = False

    claim_sourcep = 'P7482'  # property ID for "source of file"
    if claim_sourcep not in claims:
        # P7482 "source of file" 
        item_internet = pywikibot.ItemPage(wikidata_site, 'Q74228490')  # file available on the internet
        source_claim = pywikibot.Claim(wikidata_site, claim_sourcep)
        source_claim.setTarget(item_internet)
    
        # P973 "described at URL"
        qualifier_url = pywikibot.Claim(wikidata_site, 'P973')  # property ID for "described at URL"
        qualifier_url.setTarget(sourceurl)
        source_claim.addQualifier(qualifier_url, summary='Adding described at URL qualifier')

        # P137 "operator"
        qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')  # Replace with the property ID for "operator"
        qualifier_targetop = pywikibot.ItemPage(wikidata_site, 'Q420747')  # National Library of Finland (Kansalliskirjasto)
        qualifier_operator.setTarget(qualifier_targetop)
        source_claim.addQualifier(qualifier_operator, summary='Adding operator qualifier')

        # P123 "publisher"
        # Q3029524 Finnish Heritage Agency (Museovirasto)
        qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')  # property ID for "publisher"
        qualifier_targetpub = pywikibot.ItemPage(wikidata_site, 'Q3029524')  # Finnish Heritage Agency (Museovirasto)
        qualifier_publisher.setTarget(qualifier_targetpub)
        source_claim.addQualifier(qualifier_publisher, summary='Adding publisher qualifier')

        flag_add_source = True

    claim_collp = 'P195'  # property ID for "collection"
    if claim_collp not in claims:
        # P195 "collection"
        coll_claim = pywikibot.Claim(wikidata_site, claim_collp)
    
        # Q118976025 "Studio Kuvasiskojen kokoelma"
        qualifier_targetcoll = pywikibot.ItemPage(wikidata_site, 'Q118976025')  # Studio Kuvasiskojen kokoelma
        coll_claim.setTarget(qualifier_targetcoll)

        flag_add_collection = True

    claim_finnaidp = 'P9478'  # property ID for "finna ID"
    if claim_finnaidp not in claims:
        # P9478 "Finna ID"
        finna_claim = pywikibot.Claim(wikidata_site, claim_finnaidp)
        finnaunquoted = urllib.parse.unquote(finnaid)
        finna_claim.setTarget(finnaunquoted)

        flag_add_finna = True


    if (flag_add_source == False and flag_add_collection == False and flag_add_finna == False):
        print("Nothing to add, skipping.")
        continue

    #pywikibot.info('----')
    #pywikibot.showDiff(oldtext, newtext,2)
    summary='Adding structured data to file'
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
        if (flag_add_source == True):
            commonssite.addClaim(wditem, source_claim)
        if (flag_add_collection == True):
            commonssite.addClaim(wditem, coll_claim)
        if (flag_add_finna == True):
            commonssite.addClaim(wditem, finna_claim)

