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
def fixlinespacebeforetemplate(oldtext,template):
    # find template..
    indextemp = oldtext.find(template)
    if (indextemp < 0):
        return oldtext

    # find where reference-template is and which type it is
    reftext = "iitteet}}"
    indexref = oldtext.find(reftext)
    if (indexref < 0):
        reftext = "iitteet|sarakkeet}}"
        indexref = oldtext.find(reftext)
        if (indexref < 0):
            #print("did not find referencetemplate")
            return oldtext

    # check if there is only one linechange separating
    singleline = reftext + "\n" + template;
    strlen = len(singleline)
    sub = oldtext[indexref:indexref+strlen]
    if (sub == singleline):
        # output start + newline + rest (can't modify otherwise)
        #print("adding linechange")
        return oldtext[:indextemp] + "\n" + oldtext[indextemp:]
        
    #print("no changes, oldtext")
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
    if (oldtext.find("{{Taksopalkki") > 0 or oldtext.find("{{taksopalkki") > 0):
        print("Skipping " + row['title'] + " - taksopalkki already added.")
        continue

    #temptext = reftoviitteet(oldtext)
    #pywikibot.showDiff(oldtext, temptext,2)
    
    temptext = addnewline(oldtext)
    pywikibot.showDiff(oldtext, temptext,2)

    if (temptext.find("{{Käännös") > 0):
        temptext = fixlinespacebeforetemplate(temptext,"{{Käännös")
        temptext = insertabovetemplate(temptext,"{{Käännös")
    elif (temptext.find("{{käännös") > 0):
        temptext = fixlinespacebeforetemplate(temptext,"{{käännös")
        temptext = insertabovetemplate(temptext,"{{käännös")
    elif (temptext.find("{{Tynkä") > 0):
        temptext = fixlinespacebeforetemplate(temptext,"{{Tynkä")
        temptext = insertabovetemplate(temptext,"{{Tynkä")
    elif (temptext.find("{{tynkä") > 0):
        temptext = fixlinespacebeforetemplate(temptext,"{{tynkä")
        temptext = insertabovetemplate(temptext,"{{tynkä")
    else:
        temptext = fixlinespacebeforetemplate(temptext,"[[Luokka:")
        temptext = insertnostub(temptext)

    if oldtext == temptext:
        print("Exiting. " + row['title'] + " - old and new are equal.")
        exit

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Lisätään taksopalkki -malline'
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

