# What this does?
# - script tries to add Perustiedot Wikidatassa templates to the Tynkä-articles found by petscan query.
# - it handles only a specific cases where tynkä-template is directly after viitteet template
#
# Execute
# - python add-perustiedot-wikidatassa-template.py

import re
import pywikibot
import json
from urllib.request import urlopen

site = pywikibot.Site("fi", "wikipedia")
site.login()

requireconfirmation = 1
url = "https://petscan.wmflabs.org/?psid=24568722"
url += "&format=json"
url += "&output_limit=10000"

response = urlopen(url)
data_json = json.loads(response.read())

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    # Handle only cases where tynkä-template is directly after Viitteet template
    if not "iitteet}}\n\n{{Tynkä" in oldtext:
        continue

    replacementtext="\n{{Perustiedot Wikidatassa}}\n{{Tynkä"

    if 'erustiedot Wikidatassa' in oldtext:
        print("Skipping " + row['title'] + " - perustiedot Wikidatassa already added.")
        continue

    if '{{Tynkä' in oldtext:
        newtext=oldtext.replace("\n{{Tynkä", replacementtext)
    elif '{{tynkä' in oldtext:
        newtext=oldtext.replace("\n{{tynkä", replacementtext)
    else:
        print("Skipping " + row['title'] + " - Auktoriteettitunnisteet template not found.")
        continue

    if oldtext == newtext:
        print("Exiting. " + row['title'] + " - adding perustiedot Wikidatassa template failed.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, newtext,4)
    summary='Lisätään [[template:perustiedot Wikidatassa|perustiedot Wikidatassa]] -malline ([[wikipedia:pywikibot|Pywikibot]])'
    pywikibot.info('Edit summary: {}'.format(summary))

    choice='y'
    if requireconfirmation:
        question='Do you want to accept these changes?'
        choice = pywikibot.input_choice(
                question,
                [('Yes', 'y'),('No', 'N')],
                default='Y',
                automatic_quit=False
            )
            
    pywikibot.info(choice)
    if choice == 'y':
        page.text=newtext
        page.save(summary)
