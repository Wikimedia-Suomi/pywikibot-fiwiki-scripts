# Purpose: Add Taksopalkki-template to articles with relation to taxonomy of animals, plants etc.
# Additionally, check some linefeeds in articles and fix those where needed when adding Taksopalkki.
# Currently relies on Petscan-query to find candidate-articles with some filtering as well.
#
# Running script: python taksopetscan.py

import pywikibot
import json
from urllib.request import urlopen

def findrefblock(oldtext,refstring):
    index = oldtext.find(refstring)
    if (index > 0):
        strlen = len(refstring)
        tmpstr = oldtext[index:index+strlen]
        return tuple((index, tmpstr))
    return tuple((-1, ""))

def findrefs(oldtext):
    ref = findrefblock(oldtext,"{{Viitteet}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{viitteet}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{Viitteet|Sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{Viitteet|sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{viitteet|sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"<references/>")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"<references />")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{Reflist}}")
    if (ref[0] > 0):
        return ref
    ref = findrefblock(oldtext,"{{reflist}}")
    if (ref[0] > 0):
        return ref
    return tuple((-1, ""))

# ei rivinvaihtoa viitemallineen perässä? -> lisätään puuttuva
def addnewline(oldtext):
    reftup = findrefs(oldtext)
    if (reftup[0] < 0):
        # not found or some other form of making the refs list..
        return oldtext

    index = reftup[0]
    strlen = len(reftup[1])
    
    # verify we can find string with newline at end
    tmpstr = oldtext[index:index+strlen+1]
    if tmpstr.endswith("\n"):
        # at least one newline there, ok
        return oldtext
    else:
        # add one linefeed (beginning .. newline .. rest)
        return oldtext[:index+strlen] + "\n" + oldtext[index+strlen:]

# ei tyhjää riviä viitemallineen ja tynkämallineen välissä? -> lisätään
def fixlinespacebeforetemplate(oldtext,template):
    # find stub-template or other given template..
    indextemp = oldtext.find(template)
    if (indextemp < 0):
        return oldtext

    # find where reference-template is and which type it is
    reftup = findrefs(oldtext)
    if (reftup[0] < 0):
        # not found or some other form of making the refs list..
        return oldtext

    reftext = reftup[1]
    indexref = reftup[0]

    # check if there is only one linechange separating
    singleline = reftext + "\n" + template;
    strlen = len(singleline)
    sub = oldtext[indexref:indexref+strlen]
    if (sub == singleline):
        # output start + newline + rest (can't modify otherwise)
        return oldtext[:indextemp] + "\n" + oldtext[indextemp:]
        
    #print("no changes, oldtext")
    return oldtext

# check before adding template: is there something else in same line?
# if so, we should add newline
def needsprecedingnewline(oldtext,index):
    tmp = oldtext[index-1:index]
    if (tmp.endswith("\n")):
        # ok, nothing else there
        return False
    return True

# check preceding line: should we have extra line between it and addition?
def needsdoublenewline(oldtext,index):
    indexlast = oldtext.rfind("\n", 0, index)
    if (indexlast == -1):
        # no linechanges found?
        return False
    if (indexlast == index-1):
        # two linechanges in sequence? -> no need for another
        return False
    tmp = oldtext[indexlast:index]
    if (tmp.startswith("*", 1, 2) == True):
        # line is a part of list? -> should leave space
        return True
    # alternative: if (tmp.index("*") == 1):
        
    # maybe navigation or something else -> don't add another linechange
    return False

# ei tynkämallinetta? -> etsitään luokka ja lisätään sitä ennen
def insertnostub(oldtext):
    if (oldtext.find('{{tynkä') == -1 and oldtext.find('{{Tynkä') == -1):
        indexluokka = oldtext.find("[[Luokka:")
        if (indexluokka > 0):
            templatestring = "{{Taksopalkki}}\n"
            if (needsprecedingnewline(oldtext,indexluokka) == True):
                templatestring = "\n" + templatestring
            if (needsdoublenewline(oldtext,indexluokka-1) == True):
                templatestring = "\n" + templatestring
       
            return oldtext[:indexluokka] + templatestring + oldtext[indexluokka:]
    return oldtext

def insertabovetemplate(oldtext,templatename):
    indexluokka = oldtext.find(templatename)
    if (indexluokka > 0):
        templatestring = "{{Taksopalkki}}\n"
        if (needsprecedingnewline(oldtext,indexluokka) == True):
            templatestring = "\n" + templatestring
        if (needsdoublenewline(oldtext,indexluokka-1) == True):
            templatestring = "\n" + templatestring
        return oldtext[:indexluokka] + templatestring + oldtext[indexluokka:]
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
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + row['title'] + " - bot-restricted.")
        continue
    
    if (oldtext.find("{{Taksopalkki") > 0 or oldtext.find("{{taksopalkki") > 0):
        print("Skipping " + row['title'] + " - taksopalkki already added.")
        continue

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

