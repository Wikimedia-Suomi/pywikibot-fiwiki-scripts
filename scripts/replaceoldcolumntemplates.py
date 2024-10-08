# Purpose: replace old column templates with current style
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen

# vanhantyylinen viitelohko
# huom: joissakin vanhoissa artikkeleissa viiteluettelo on 
# merkitty <references> .. </references> tagien välissä
def convertreftoviitteet(oldtext):
    if '<references/>' in oldtext:
        return oldtext.replace("<references/>", "{{Viitteet}}")
    if '<references />' in oldtext:
        return oldtext.replace("<references />", "{{Viitteet}}")
    
    if '<References/>' in oldtext:
        return oldtext.replace("<References/>", "{{Viitteet}}")
    if '<References />' in oldtext:
        return oldtext.replace("<References />", "{{Viitteet}}")

    if '<references responsive="" />' in oldtext:
        return oldtext.replace('<references responsive="" />', "{{Viitteet}}")
    return oldtext


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
    return tuple((-1, ""))

def convertColTemplates(oldtext):
    startreplaced = False
    
    if '{{palsta-a|width=75%}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a|width=75%}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    
    if '{{palstoitus alkaa}}' in oldtext:
        oldtext = oldtext.replace("{{palstoitus alkaa}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{Palstoitus alkaa}}' in oldtext:
        oldtext = oldtext.replace("{{Palstoitus alkaa}}", "{{Monta palstaa|75%}}")
        startreplaced = True

    if '{{palstoitus alkaa|leveä}}' in oldtext:
        oldtext = oldtext.replace("{{palstoitus alkaa|leveä}}", "{{Monta palstaa|100%}}")
        startreplaced = True
    if '{{Palstoitus alkaa|leveä}}' in oldtext:
        oldtext = oldtext.replace("{{Palstoitus alkaa|leveä}}", "{{Monta palstaa|100%}}")
        startreplaced = True


    if '{{palstoitus loppuu}}' in oldtext:
        oldtext = oldtext.replace("{{palstoitus loppuu}}", "{{Monta palstaa-loppu}}")
    if '{{Palstoitus loppuu}}' in oldtext:
        oldtext = oldtext.replace("{{Palstoitus loppuu}}", "{{Monta palstaa-loppu}}")

    if '{{palstanvaihto}}' in oldtext:
        oldtext = oldtext.replace("{{palstanvaihto}}", "{{Monta palstaa-katko}}")
    if '{{Palstanvaihto}}' in oldtext:
        oldtext = oldtext.replace("{{Palstanvaihto}}", "{{Monta palstaa-katko}}")
    

    if '{{Monta palstaa|75%}}\n{{Monta palstaa-katko}}' in oldtext:
        oldtext = oldtext.replace("{{Monta palstaa|75%}}\n{{Monta palstaa-katko}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    
    # if there is a combination of two rows, replace with just one
    if '{{palsta-a}}\n{{palsta-2}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a}}\n{{palsta-2}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{palsta-a}}\n{{palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a}}\n{{palsta-3}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{palsta-a}}\n{{palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a}}\n{{palsta-4}}", "{{Monta palstaa|75%}}")
        startreplaced = True

    if '{{palsta-a}}\n{{Monta palstaa-katko}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a}}\n{{Monta palstaa-katko}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{Palsta-a}}\n{{Monta palstaa-katko}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-a}}\n{{Monta palstaa-katko}}", "{{Monta palstaa|75%}}")
        startreplaced = True

    if '{{palsta-a}}\n\n{{Monta palstaa-katko}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-a}}\n\n{{Monta palstaa-katko}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{Palsta-a}}\n\n{{Monta palstaa-katko}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-a}}\n\n{{Monta palstaa-katko}}", "{{Monta palstaa|75%}}")
        startreplaced = True


    # if there is a combination of two rows, replace with just one
    if '{{Palsta-a}}\n{{palsta-2}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-a}}\n{{palsta-2}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{Palsta-a}}\n{{palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-a}}\n{{palsta-3}}", "{{Monta palstaa|75%}}")
        startreplaced = True
    if '{{Palsta-a}}\n{{palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-a}}\n{{palsta-4}}", "{{Monta palstaa|75%}}")
        startreplaced = True


    # try 
    #if '{{palsta-a}}' in oldtext:
        #oldtext = oldtext.replace("{{palsta-a}}", "{{Monta palstaa}}")
    #if '{{Palsta-a}}' in oldtext:
        #oldtext = oldtext.replace("{{Palsta-a}}", "{{Monta palstaa}}")

    # change other templates breaking columns
    if '{{palsta-2}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-2}}", "{{Monta palstaa-katko}}")
    if '{{Palsta-2}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-2}}", "{{Monta palstaa-katko}}")

    if '{{palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-3}}", "{{Monta palstaa-katko}}")
    if '{{Palsta-3}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-3}}", "{{Monta palstaa-katko}}")

    if '{{palsta-4}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-4}}", "{{Monta palstaa-katko}}")
    if '{{Palsta-4}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-4}}", "{{Monta palstaa-katko}}")
    
    if '{{palsta-l}}' in oldtext:
        oldtext = oldtext.replace("{{palsta-l}}", "{{Monta palstaa-loppu}}")
    if '{{Palsta-l}}' in oldtext:
        oldtext = oldtext.replace("{{Palsta-l}}", "{{Monta palstaa-loppu}}")


    return oldtext


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

def getpagesrecurse(pywikibot, site, maincat, depth=1):
    #final_pages = list()
    cat = pywikibot.Category(site, maincat)
    pages = list(cat.articles(recurse=depth))
    return pages

def getpagesfrompetscan(pywikibot, site, psid, limit=6000):

    pages = list()

    # property: takso, artikkelissa taksonomiamalline (/kasvit, /eläimet)
    #url = "https://petscan.wmflabs.org/?psid=26259099"
    url = "https://petscan.wmflabs.org/?psid=" + str(psid)
    url += "&format=json"
    url += "&output_limit=" + str(limit)
    response = urlopen(url)
    data_json = json.loads(response.read())
    if (data_json == None):
        print("No data")
        return None
    if (len(data_json) == 0):
        print("empty data")
        return None

    for row in data_json['*'][0]['a']['*']:
        page = pywikibot.Page(site, row['title'])
        pages.append(page)

    return pages


site = pywikibot.Site("fi", "wikipedia")
site.login()

pages = getpagesfrompetscan(pywikibot, site,  29463732)

#pages = getpagesrecurse(pywikibot, site, "Koripallon maailmanmestaruuskilpailut", 2)


rivinro = 1

for page in pages:
    #page=pywikibot.Page(site, row['title'])
    oldtext=page.text

    print(" ////////", rivinro, ": [ " + page.title() + " ] ////////")
    rivinro += 1

    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping " + page.title() + " - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + page.title() + " - bot-restricted.")
        continue


    temptext = oldtext
    #temptext = convertreftoviitteet(temptext)
    #temptext = addnewline(temptext)
    #temptext = addnewline(temptext)

    temptext = convertColTemplates(temptext)

    
    if oldtext == temptext:
        print("Skipping. " + page.title() + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, temptext,2)
    summary='Vaihdetaan nykyiseen palstamallineeseen'
    pywikibot.info('Edit summary: {}'.format(summary))

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

    page.text=temptext
    page.save(summary)

    #question='Do you want to accept these changes?'
    #choice = pywikibot.input_choice(
    #            question,
    #            [('Yes', 'y'),('No', 'N'),('Quit', 'q')],
    #            default='N',
    #            automatic_quit=False
    #        )

    #pywikibot.info(choice)
    #if choice == 'q':
    #    print("Asked to exit. Exiting.")
    #    exit()

    #if choice == 'y':
    #    page.text=temptext
    #    page.save(summary)

