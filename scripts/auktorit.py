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

site = pywikibot.Site("fi", "wikipedia")
site.login()

# haku auktoriteettitunnisteiden luettelossa olevilla
url = "https://petscan.wmflabs.org/?psid=24582298"
url += "&format=json"
url += "&output_limit=5"
response = urlopen(url)
data_json = json.loads(response.read())

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text
    
    if 'uktoriteettitunnisteet' in oldtext:
        print("Skipping " + row['title'] + " - auktoriteetit already added.")
        continue

    #temptext = reftoviitteet(oldtext)
    #pywikibot.showDiff(oldtext, temptext,2)
    
# onko käännösmallinetta tai tynkämallinetta? jos ei kumpaakaan, onko aakkostusmallinetta?
# jos ei ole sitäkään etsi luokka ja lisää sen ylle
    if 'Käännös' in oldtext:
        temptext = oldtext.replace("\n{{Käännös", "\n{{Auktoriteettitunnisteet}}\n{{Käännös")
    elif 'käännös' in oldtext:
        temptext = oldtext.replace("\n{{käännös", "\n{{Auktoriteettitunnisteet}}\n{{käännös")
    elif 'Tynkä' in oldtext:
        temptext = oldtext.replace("\n{{Tynkä", "\n{{Auktoriteettitunnisteet}}\n{{Tynkä")
    elif 'tynkä' in oldtext:
        temptext = oldtext.replace("\n{{tynkä", "\n{{Auktoriteettitunnisteet}}\n{{tynkä")
    if '{{OLETUSAAKKOSTUS' in oldtext:
        temptext = oldtext.replace("\n{{OLETUSAAKKOSTUS", "\n{{Auktoriteettitunnisteet}}\n{{OLETUSAAKKOSTUS")
    elif '{{AAKKOSTUS' in oldtext:
        temptext = oldtext.replace("\n{{AAKKOSTUS", "\n{{Auktoriteettitunnisteet}}\n{{AAKKOSTUS")
    elif '{{DEFAULTSORT' in oldtext:
        temptext = oldtext.replace("\n{{DEFAULTSORT", "\n{{Auktoriteettitunnisteet}}\n{{DEFAULTSORT")
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

