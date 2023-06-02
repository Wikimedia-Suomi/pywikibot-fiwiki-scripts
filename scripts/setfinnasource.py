# Purpose: add metapage to source on pictures from finna
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
from urllib.request import urlopen

def getnewsource(oldsource):
    indexid = oldsource.find("id=")
    if (indexid < 0):
        return oldsource
    indexend = oldsource.find("&", indexid)
    if (indexend < 0):
        return oldsource
        
    finnarecord = oldsource[indexid+3:indexend]
    return "<br>Image record page in Finna: [https://finna.fi/Record/" + finnarecord + " " + finnarecord + "]\n"


# ------ main()

# site = pywikibot.Site("fi", "wikipedia")
site = pywikibot.Site("commons", "commons")
site.login()
cat = pywikibot.Category(site, "Category:Kuvasiskot")
pages = site.categorymembers(cat)

rowcount = 1
rowlimit = 10

for page in pages:
    if page.namespace() != 6:  # 6 is the namespace ID for files
        continue

    filepage = pywikibot.FilePage(page)
    if filepage.isRedirectPage():
        continue    

    changed = False
    oldtext=page.text

    print(" ////////", rowcount, ": [ " + page.title() + " ] ////////")
    rowcount += 1

    wikicode = mwparserfromhell.parse(page.text)
    
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        if template.name.matches("Information"):
            if template.has("Source"):
                par = template.get("Source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                if (srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                newsource = getnewsource(srcvalue)
                if (newsource != srcvalue):
                    if (srcvalue.endswith("\n")):
                        finalsource = srcvalue[:len(srcvalue)-1] + newsource
                        par.value = finalsource
                    else:
                        par.value = srcvalue + newsource
                    changed = True

            if template.has("source"):
                par = template.get("source")
                srcvalue = str(par.value)
                if (srcvalue.find("finna.fi") < 0):
                    print("source isn't finna")
                    break
                if (srcvalue.find("/Record/") > 0):
                    # already has metapage
                    print("already has metapage link, skipping")
                    break
                newsource = getnewsource(srcvalue)
                if (newsource != srcvalue):
                    if (srcvalue.endswith("\n")):
                        finalsource = srcvalue[:len(srcvalue)-1] + newsource
                        par.value = finalsource
                    else:
                        par.value = srcvalue + newsource
                    changed = True
 
    if (changed == False):
        print("no change, skipping")
        continue

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

