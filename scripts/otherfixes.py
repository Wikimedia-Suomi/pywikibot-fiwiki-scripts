# Purpose: replace old style template with current style
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen

# vanhantyylinen viitelohko
def convertreftoviitteet(oldtext):
    if '<references/>' in oldtext:
        return oldtext.replace("<references/>", "{{Viitteet}}")
    if '<references />' in oldtext:
        return oldtext.replace("<references />", "{{Viitteet}}")
    return oldtext

# ohjaus eng-kielisestä fi-wikin käyttämään
def convertreflisttoviitteet(oldtext):
    if '{{Reflist}}' in oldtext:
        return oldtext.replace("{{Reflist}}", "{{Viitteet}}")
    if '{{reflist}}' in oldtext:
        return oldtext.replace("{{reflist}}", "{{Viitteet}}")
    return oldtext

# vanhantyylinen aakkostus
def convertoldsort(oldtext):
    if '{{DEFAULTSORT:' in oldtext:
        return oldtext.replace("{{DEFAULTSORT:", "{{AAKKOSTUS:")
    if '{{OLETUSAAKKOSTUS:' in oldtext:
        return oldtext.replace("{{OLETUSAAKKOSTUS:", "{{AAKKOSTUS:")
    return oldtext

site = pywikibot.Site("fi", "wikipedia")
site.login()

# property: takso, artikkelissa taksonomiamalline (/kasvit, /eläimet)
url = "https://petscan.wmflabs.org/?psid=24596149"
url += "&format=json"
url += "&output_limit=100"
response = urlopen(url)
data_json = json.loads(response.read())

rivinro = 1

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" ////////", rivinro, ": [ " + row['title'] + " ] ////////")
    rivinro += 1

    temptext = oldtext
    temptext = convertreftoviitteet(temptext)
    temptext = convertreflisttoviitteet(temptext)
    temptext = convertoldsort(temptext)
    
    if oldtext == temptext:
        print("Skipping. " + row['title'] + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Vanhojen mallineiden päivitys'
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

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
        page.text=temptext
        page.save(summary)

