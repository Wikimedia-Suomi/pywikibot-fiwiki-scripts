# Purpose: Add Auktoriteettitunnisteet-template to articles with relation to people
# Additionally, check some linefeeds in articles and fix those where needed when adding Auktoriteettitunnisteet.
# Currently relies on Petscan-query to find candidate-articles with some filtering as well.
#
# Running script: python auktorit.py

import pywikibot
import json
from urllib.request import urlopen

# vanhantyylinen viitelohko
def reftoviitteet(oldtext):
    if '<references/>' in oldtext:
        return oldtext.replace("<references/>", "{{Viitteet}}")
    if '<references />' in oldtext:
        return oldtext.replace("<references />", "{{Viitteet}}")
    return oldtext

# ei tynkämallinetta tai muuta? -> etsitään luokka ja lisätään sitä ennen
def insertaboveclass(oldtext):
    indexluokka = oldtext.find("[[Luokka:")
    if (indexluokka > 0):
        return oldtext[:indexluokka] + "{{Auktoriteettitunnisteet}}\n" + oldtext[indexluokka:]
    return oldtext

def insertabovetemplate(oldtext,templatename):
    indexluokka = oldtext.find(templatename)
    if (indexluokka > 0):
        return oldtext[:indexluokka] + "{{Auktoriteettitunnisteet}}\n" + oldtext[indexluokka:]
    return oldtext

site = pywikibot.Site("fi", "wikipedia")
site.login()

# haku auktoriteettitunnisteiden luettelossa olevilla
url = "https://petscan.wmflabs.org/?psid=24591041"
url += "&format=json"
url += "&output_limit=10"
response = urlopen(url)
data_json = json.loads(response.read())

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text
    
    if (oldtext.find("{{Auktoriteettitunnisteet") > 0 or oldtext.find("{{auktoriteettitunnisteet") > 0):
        print("Skipping " + row['title'] + " - auktoriteetit already added.")
        continue

    #temptext = reftoviitteet(oldtext)
    #pywikibot.showDiff(oldtext, temptext,2)
    
# onko käännösmallinetta tai tynkämallinetta? jos ei kumpaakaan, onko aakkostusmallinetta?
# jos ei ole sitäkään etsi luokka ja lisää sen ylle
    if (oldtext.find("{{Käännös") > 0):
        temptext = insertabovetemplate(oldtext,"{{Käännös")
    elif (oldtext.find("{{käännös") > 0):
        temptext = insertabovetemplate(oldtext,"{{käännös")
    elif (oldtext.find("{{Tynkä") > 0):
        temptext = insertabovetemplate(oldtext,"{{Tynkä")
    elif (oldtext.find("{{tynkä") > 0):
        temptext = insertabovetemplate(oldtext,"{{tynkä")
    elif (oldtext.find("{{OLETUSAAKKOSTUS") > 0):
        temptext = insertabovetemplate(oldtext,"{{OLETUSAAKKOSTUS")
    elif (oldtext.find("{{AAKKOSTUS") > 0):
        temptext = insertabovetemplate(oldtext,"{{AAKKOSTUS")
    elif (oldtext.find("{{DEFAULTSORT") > 0):
        temptext = insertabovetemplate(oldtext,"{{DEFAULTSORT")
    else:
        temptext = insertaboveclass(oldtext)

    if oldtext == temptext:
        print("Exiting. " + row['title'] + " - old and new are equal.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Lisätään auktoriteettitunnisteet -malline'
    pywikibot.info('Edit summary: {}'.format(summary))

    question='Do you want to accept these changes?'
    choice = pywikibot.input_choice(
                question,
                [('Yes', 'y'),('No', 'N')],
                default='N',
                automatic_quit=False
            )

    pywikibot.info(choice)
    if choice == 'y':
        page.text=temptext
        page.save(summary)

