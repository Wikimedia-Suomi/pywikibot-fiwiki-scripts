# Purpose: Add Astronominen kappale WD -template to articles with relation to asteroids, comets etc.
# Currently relies on Petscan-query to find candidate-articles with some filtering as well.
#
# Running script: python astroboksi.py

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


site = pywikibot.Site("fi", "wikipedia")
site.login()

# property: P31=Q3863
url = "https://petscan.wmflabs.org/?psid=24604002"
url += "&format=json"
url += "&output_limit=10"
response = urlopen(url)
data_json = json.loads(response.read())

rivinro = 1

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" ========", rivinro, ": [ " + row['title'] + " ]")
    rivinro += 1
    if (oldtext.find("{{Astronominen kappale WD") > 0):
        print("Skipping " + row['title'] + " - astroboksi already added.")
        continue
    if (oldtext.find("{{Planeetta") > 0):
        print("Skipping " + row['title'] + " - Planeetta-malline already added.")
        continue

    temptext = "{{Astronominen kappale WD}}\n" + oldtext

    if oldtext == temptext:
        print("Exiting. " + row['title'] + " - old and new are equal.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Lisätään Astronominen kappale WD -malline'
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

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

