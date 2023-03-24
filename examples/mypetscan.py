# What this does
# 1.) Program reads list of articles without "Perustiedot Wikidatassa" templates from petscan in json format
# 2.) then it and tries to add the template to wikicode 
# 3.) after confirm it will save it to Finnish Wikipedia
#
# Execute: 
# - python mypetscan.py 
#


import pywikibot
import json
from urllib.request import urlopen

site = pywikibot.Site("fi", "wikipedia")
site.login()

url = "https://petscan.wmflabs.org/?psid=24092213"
url += "&format=json"
url += "&output_limit=3"
response = urlopen(url)
data_json = json.loads(response.read())

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    replacementtext="\n{{Perustiedot Wikidatassa}}\n{{Auktoriteettitunnisteet"

    if 'erustiedot Wikidatassa' in oldtext:
        print("Skipping " + row['title'] + " - perustiedot Wikidatassa already added.")
        continue

    if 'Auktoriteettitunnisteet' in oldtext:
        newtext=oldtext.replace("\n{{Auktoriteettitunnisteet", replacementtext)
    elif 'auktoriteettitunnisteet' in oldtext:
        newtext=oldtext.replace("\n{{auktoriteettitunnisteet", replacementtext)
    else:
        print("Skipping " + row['title'] + " - Auktoriteettitunnisteet template not found.")
        continue

    if oldtext == newtext:
        print("Exiting. " + row['title'] + " - adding perustiedot Wikidatassa template failed.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, newtext,2)
    summary='Lisätään perustiedot Wikidatassa -malline'
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
        page.text=newtext
        page.save(summary)
