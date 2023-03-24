# What this does?
# - script tries to add Perustiedot Wikidatassa templates to the Tynkä-articles found by petscan query.
# - it handles only a specific cases where tynkä-template is directly after viitteet template
#
# Execute
# - python add-perustiedot-wikidatassa-template.py

import time
import re
import pywikibot
import json
from urllib.request import urlopen

site = pywikibot.Site("fi", "wikipedia")
site.login()

url = "https://petscan.wmflabs.org/?psid=24568722"
url += "&format=json"
url += "&output_limit=15000"

response = urlopen(url)
data_json = json.loads(response.read())



def test_navbox_template(templatename):
    template=pywikibot.Page(site, "template:" + templatename)

    pattern = r'{{([Aa]vattavaLoppu|[Tt]yhjä malline|[Cc]oor|[Nn]avigaatio|[Nn]avbox)'
    matches = re.findall(pattern, template.text, re.MULTILINE)
    if matches:
        return True

    if "#OHJAUS" in oldtext:
        return False


    print(template.text)
    time.sleep(10)
    return False


for row in data_json['*'][0]['a']['*']:
    requireconfirmation = 1

#    if not "Kajaanin_liikuntapuisto" == row['title']:
#        continue

    page=pywikibot.Page(site, row['title'])
    oldtext=page.text




    # Handle only cases where tynkä-template is directly after Viitteet template
#    if not "iitteet}}\n{{Tynkä" in oldtext:
#        continue

    replacementtext="\n{{Perustiedot Wikidatassa}}\n{{Tynkä"

    if 'erustiedot Wikidatassa' in oldtext:
        print("Skipping " + row['title'] + " - perustiedot Wikidatassa already added.")
        continue

    if '{{Tynkä' in oldtext:
        newtext=oldtext.replace("\n{{Tynkä", replacementtext)
    elif '{{tynkä' in oldtext:
        newtext=oldtext.replace("\n{{tynkä", replacementtext)
    else:
        print("Skipping " + row['title'] + " - Tynkä template not found.")
        continue

    if not "\n{{Perusti" in newtext:
        continue

    if not "}}\n{{Perusti" in newtext:
        continue

    pattern = r'^(}}|{{[Vv]iitteet|{{[Cc]ommons|\*).*\n{{Perus'
    matches = re.findall(pattern, newtext, re.MULTILINE)
    if matches:
        continue


    pattern = r'^{{(.*)}}\n{{Perus'
    matches = re.findall(pattern, newtext, re.MULTILINE)
    if matches:
        if not test_navbox_template(matches[0]):
            continue
        requireconfirmation = 0


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
        if site.userinfo['messages']:
            print("Warning: Talk page messages. Exiting.")
            exit()

        page.text=newtext
        page.save(summary)
