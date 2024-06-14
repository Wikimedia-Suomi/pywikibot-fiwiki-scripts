# Purpose: replace old style tt-tag with current code-tag
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen


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


def convertOldFilePrefix(oldtext):
    if '[[File:' in oldtext:
        oldtext = oldtext.replace("[[File:", "[[Tiedosto:")
    if '[[file:' in oldtext:
        oldtext = oldtext.replace("[[file:", "[[Tiedosto:")

    if '[[Image:' in oldtext:
        oldtext = oldtext.replace("[[Image:", "[[Tiedosto:")
    if '[[image:' in oldtext:
        oldtext = oldtext.replace("[[image:", "[[Tiedosto:")

    if '[[Kuva:' in oldtext:
        oldtext = oldtext.replace("[[Kuva:", "[[Tiedosto:")
    if '[[kuva:' in oldtext:
        oldtext = oldtext.replace("[[kuva:", "[[Tiedosto:")
    
    return oldtext


# main()

site = pywikibot.Site("fi", "wikipedia")
site.login()

#pages = getpagesfrompetscan(pywikibot, site, 26694363)


#pages = getpagesrecurse(pywikibot, site, "Keskiajan yhteiskunta", 0)

#pages = getpagesrecurse(pywikibot, site, "Taidemaalarit maittain", 3)

pages = getpagesrecurse(pywikibot, site, "Kokemäenjoen vesistö", 2)


rivinro = 1

for page in pages:
    #page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" ////////", rivinro, ": [ " + page.title() + " ] ////////")
    rivinro += 1

    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping " + page.title() + " - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + page.title() + " - bot-restricted.")
        continue


    temptext = oldtext
    temptext = convertOldFilePrefix(oldtext)

    #temptext = convertreftoviitteet(temptext)
    #temptext = addnewline(temptext)

    
    if oldtext == temptext:
        print("Skipping. " + page.title() + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Vaihdetaan tiedosto-liitteeseen'
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

    page.text=temptext
    page.save(summary)

    #question='Do you want to accept these changes?'
    #choice = pywikibot.input_choice(
    #            question,
    #            [('Yes', 'y'),('No', 'N'),('Quit', 'q')],
    #            default='N',
    #            automatic_quit=False
    #        )

    #pywikibot.info(choice)
    #if choice == 'q':
    #    print("Asked to exit. Exiting.")
    #    exit()

    #if choice == 'y':
    #    page.text=temptext
    #    page.save(summary)

