# Purpose: Add Auktoriteettitunnisteet-template to articles with relation to people
# Additionally, check some linefeeds in articles and fix those where needed when adding Auktoriteettitunnisteet.
# Currently relies on Petscan-query to find candidate-articles with some filtering as well.
#
# Running script: python auktorit.py

import pywikibot
import json
from urllib.request import urlopen

def findtemplateblock(oldtext,refstring):
    index = oldtext.find(refstring)
    if (index > 0):
        strlen = len(refstring)
        tmpstr = oldtext[index:index+strlen]
        return tuple((index, tmpstr))
    return tuple((-1, ""))

def findrefs(oldtext):
    ref = findtemplateblock(oldtext,"{{Viitteet}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{viitteet}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{Viitteet|Sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{Viitteet|sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{viitteet|sarakkeet}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"<references/>")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"<references />")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{Reflist}}")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{reflist}}")
    if (ref[0] > 0):
        return ref
    return tuple((-1, ""))

def findsorts(oldtext):
    ref = findtemplateblock(oldtext,"{{AAKKOSTUS:")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{OLETUSAAKKOSTUS:")
    if (ref[0] > 0):
        return ref
    ref = findtemplateblock(oldtext,"{{DEFAULTSORT:")
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
        
    #print("no changes, oldtext: " + sub)
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

def insertabovetemplate(oldtext,templatename):
    indexluokka = oldtext.find(templatename)
    if (indexluokka > 0):
        templatestring = "{{Auktoriteettitunnisteet}}\n"
        if (needsprecedingnewline(oldtext,indexluokka) == True):
            templatestring = "\n" + templatestring
        if (needsdoublenewline(oldtext,indexluokka-1) == True):
            templatestring = "\n" + templatestring
        return oldtext[:indexluokka] + templatestring + oldtext[indexluokka:]
    return oldtext


# check ordering of given templates: check both in upper (expected) and lower cases
def checkorder(text,before,after):
    index1 = text.find(before)
    if (index1 < 0):
        # try lowercase
        index1 = text.find(before.lower())
        if (index1 < 0):
            # not there: can't compare
            return -1;
        
    index2 = text.find(after)
    if (index2 < 0):
        # try lowercase
        index2 = text.find(after.lower())
        if (index2 < 0):
            # not there: can't compare
            return -1

    if (index1 < 0 or index2 < 0):
        # either one isn't there
        return -1
    if (index1 < index2):
        # normal: earlier is where expected
        return 0

    # abnormal: the one supposed to be earlier is later..
    return 1

# locate order of specified entries
def locateentries(text):
    items = dict()
    
    index = text.find("{{Käännös")
    if (index > 0):
        items[index] = "{{Käännös"
    index = text.find("{{käännös")
    if (index > 0):
        items[index] = "{{käännös"

    index = text.find("{{Tynkä")
    if (index > 0):
        items[index] = "{{Tynkä"
    index = text.find("{{tynkä")
    if (index > 0):
        items[index] = "{{tynkä"

    index = text.find("[[Luokka:")
    if (index > 0):
        items[index] = "[[Luokka:"
    index = text.find("[[luokka:")
    if (index > 0):
        items[index] = "[[luokka:"

    index = text.find("{{AAKKOSTUS:")
    if (index > 0):
        items[index] = "{{AAKKOSTUS:"
    index = text.find("{{OLETUSAAKKOSTUS:")
    if (index > 0):
        items[index] = "{{OLETUSAAKKOSTUS:"
    index = text.find("{{DEFAULTSORT:")
    if (index > 0):
        items[index] = "{{DEFAULTSORT:"

    # sort it
    keys = list(items.keys())
    keys.sort()
    itemsout = {i: items[i] for i in keys}        
    #return sorted(items.items())
    return itemsout

site = pywikibot.Site("fi", "wikipedia")
site.login()

# haku auktoriteettitunnisteiden luettelossa olevilla

# scopus url = "https://petscan.wmflabs.org/?psid=24596657"
url = "https://petscan.wmflabs.org/?psid=24863519"
url += "&format=json"
url += "&output_limit=1000"
response = urlopen(url)
data_json = json.loads(response.read())

rivinro = 1

for row in data_json['*'][0]['a']['*']:
    page=pywikibot.Page(site, row['title'])
    oldtext=page.text
    
    print(" ////////", rivinro, ": [ " + row['title'] + " ] ////////")
    rivinro += 1
    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping " + row['title'] + " - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + row['title'] + " - bot-restricted.")
        continue
    
    if (oldtext.find("{{Auktoriteettitunnisteet") > 0 or oldtext.find("{{auktoriteettitunnisteet") > 0):
        print("Skipping " + row['title'] + " - auktoriteetit already added.")
        continue

    if (checkorder(oldtext, "{{Viitteet", "{{Käännös") == 1):
        print("Skipping " + row['title'] + " - Käännös and Viitteet in wrong order.")
        continue
    if (checkorder(oldtext, "{{Viitteet", "{{Tynkä") == 1):
        print("Skipping " + row['title'] + " - Tynkä and Viitteet in wrong order.")
        continue
    if (checkorder(oldtext, "{{Wikiaineisto", "{{Tynkä") == 1):
        print("Skipping " + row['title'] + " - Wikiaineisto and Tynkä in wrong order.")
        continue
    if (checkorder(oldtext, "{{Commonscat", "{{Käännös") == 1):
        print("Skipping " + row['title'] + " - Commonscat and Käännös in wrong order.")
        continue
    if (checkorder(oldtext, "{{Commons", "{{Tynkä") == 1):
        print("Skipping " + row['title'] + " - Commons and Tynkä in wrong order.")
        continue
    if (checkorder(oldtext, "{{Edeltäjä-seuraaja", "[[Luokka:") == 1):
        print("Skipping " + row['title'] + " - Edeltäjä-seuraaja and Luokka in wrong order.")
        continue

    reftup = findrefs(oldtext)
    sorttup = findsorts(oldtext)
    if (reftup[0] > 0 and sorttup[0] > 0 and sorttup[0] < reftup[0]):
        print("Skipping " + row['title'] + " - " + reftup[1] + " and " + sorttup[1] + " in wrong order.")
        continue

        
    temptext = addnewline(oldtext)
    
    #if oldtext != temptext:
    #    pywikibot.showDiff(oldtext, temptext,2)
    
    # check what is the topmost
    # onko käännösmallinetta tai tynkämallinetta? jos ei kumpaakaan, onko aakkostusmallinetta?
    # jos ei ole sitäkään etsi luokka ja lisää sen ylle
    entries = locateentries(oldtext)
    if (len(entries) > 0):
        print("top entries: ", entries.values())
        
        topmostindex = next(iter(entries))
        if (topmostindex > 0):
            topmostval = entries[topmostindex]
            temptext = fixlinespacebeforetemplate(temptext,topmostval)
            temptext = insertabovetemplate(temptext,topmostval)

    if oldtext == temptext:
        print("Skipping. " + row['title'] + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Lisätään auktoriteettitunnisteet -malline'
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

