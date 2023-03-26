# Purpose: Add Taksopalkki-template to articles with relation to taxonomy of animals, plants etc.
# Additionally, check some linefeeds in articles and fix those where needed when adding Taksopalkki.
# Currently relies on Petscan-query to find candidate-articles with some filtering as well.
#
# Running script: python taksopetscan.py

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

# ei rivinvaihtoa viitemallineen perässä? -> lisätään puuttuva
def addnewline(oldtext):
    index = oldtext.find("iitteet}}")
    if (index < 0):
        return oldtext
    strlen = len("iitteet}}\n")
    tmpstr = oldtext[index:index+strlen]
    if tmpstr.endswith("\n"):
        return oldtext
    else:
        return oldtext.replace("iitteet}}", "iitteet}}\n")

# ei tyhjää riviä viitemallineen ja tynkämallineen välissä? -> lisätään
def nonewline(oldtext):
    index = oldtext.find("{{tynkä")
    if (index < 0):
        return oldtext
    strlen = len("iitteet}}\n")
    sub = oldtext[index:-strlen]
    if (sub == "iitteet}}\n"):
        return oldtext.replace("iitteet}}\n{{tynkä", "iitteet}}\n\n{{tynkä")
    return oldtext

# sama kuin yllä paitsi iso T..
def nonewlineT(oldtext):
    index = oldtext.find("{{Tynkä")
    if (index < 0):
        return oldtext
    strlen = len("iitteet}}\n")
    sub = oldtext[index:-strlen]
    if (sub == "iitteet}}\n"):
        return oldtext.replace("iitteet}}\n{{Tynkä", "iitteet}}\n\n{{Tynkä")
    return oldtext

# ei tynkämallinetta? -> etsitään luokka ja lisätään sitä ennen
def insertnostub(oldtext):
    if (oldtext.find('{{tynkä') == -1 and oldtext.find('{{Tynkä') == -1):
        indexluokka = oldtext.find("[[Luokka:")
        if (indexluokka > 0):
            return oldtext[:indexluokka] + "{{Taksopalkki}}\n" + oldtext[indexluokka:]
    return oldtext

def insertabovetemplate(oldtext,templatename):
    indexluokka = oldtext.find(templatename)
    if (indexluokka > 0):
        return oldtext[:indexluokka] + "{{Taksopalkki}}\n" + oldtext[indexluokka:]
    return oldtext

site = pywikibot.Site("fi", "wikipedia")
site.login()

# property: takso, artikkelissa taksonomiamalline, ei käännösmallinetta
url = "https://petscan.wmflabs.org/?psid=24572724"
url += "&format=json"
url += "&output_limit=10"
response = urlopen(url)
data_json = json.loads(response.read())

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    if (oldtext.find("{{Taksopalkki") > 0 or oldtext.find("{{taksopalkki") > 0):
        print("Skipping " + row['title'] + " - taksopalkki already added.")
        continue

    #temptext = reftoviitteet(oldtext)
    #pywikibot.showDiff(oldtext, temptext,2)
    
    temptext = addnewline(oldtext)
    pywikibot.showDiff(oldtext, temptext,2)
    temptext = nonewline(temptext)
    pywikibot.showDiff(oldtext, temptext,2)
    temptext = nonewlineT(temptext)
    pywikibot.showDiff(oldtext, temptext,2)

    if (temptext.find("{{Tynkä") > 0):
        temptext = insertabovetemplate(temptext,"{{Tynkä")
    elif (temptext.find("{{tynkä") > 0):
        temptext = insertabovetemplate(temptext,"{{tynkä")
    else:
        temptext = insertnostub(temptext)

    if oldtext == temptext:
        print("Exiting. " + row['title'] + " - old and new are equal.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Lisätään taksopalkki -malline'
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

