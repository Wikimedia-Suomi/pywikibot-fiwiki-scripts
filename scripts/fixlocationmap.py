# Purpose: fix name given to location map into localized one
#
# Location maps are under switching to completely localized names
# but a number of pages uses english names so those need to be changed first.
# Before adding to list, verify there exists a redirect 
# from "Location map <en-country>" to "Sijaintikartta <fi-country>".
#
# Once names are all one way (not two systems) the other part of the template can be fixed also.
#
# Running script: python <scriptname>

import pywikibot
import mwparserfromhell
import json
from urllib.request import urlopen

# mapping according template redirects to fix
d_engtofin = dict()
d_engtofin["France"] = "Ranska"
d_engtofin["Italy"] = "Italia"
d_engtofin["Spain"] = "Espanja"
d_engtofin["England"] = "Englanti"
d_engtofin["Canada"] = "Kanada"
d_engtofin["Germany"] = "Saksa"
d_engtofin["Finland"] = "Suomi"
d_engtofin["Estonia"] = "Viro"
d_engtofin["Denmark"] = "Tanska"
d_engtofin["Norway"] = "Norja"
d_engtofin["Iceland"] = "Islanti"
d_engtofin["Lithuania"] = "Liettua"
d_engtofin["Austria"] = "Itävalta"
d_engtofin["Portugal"] = "Portugali"
d_engtofin["Croatia"] = "Kroatia"
d_engtofin["United Kingdom"] = "Yhdistynyt kuningaskunta"
d_engtofin["Belgium"] = "Belgia"
d_engtofin["Netherlands"] = "Alankomaat"
d_engtofin["Switzerland"] = "Sveitsi"
d_engtofin["Poland"] = "Puola"
d_engtofin["Ukraine"] = "Ukraina"
d_engtofin["Baltic Sea"] = "Itämeri"
d_engtofin["Belarus"] = "Valko-Venäjä"
d_engtofin["Turkey"] = "Turkki"
d_engtofin["Hungary"] = "Unkari"

d_engtofin["New Zealand"] = "Uusi-Seelanti"
d_engtofin["Colombia"] = "Kolumbia"
d_engtofin["Mexico"] = "Meksiko"
d_engtofin["Japan"] = "Japani"
d_engtofin["Thailand"] = "Thaimaa"
d_engtofin["India"] = "Intia"
d_engtofin["China"] = "Kiina"

d_engtofin["Sweden Västra Götaland"] = "Ruotsi Länsi-Götanmaan lääni"
d_engtofin["Sweden Skåne"] = "Ruotsi Skånen lääni"
d_engtofin["Sweden Norrbotten"] = "Ruotsi Norrbottenin lääni"
d_engtofin["Sweden Södermanland"] = "Ruotsi Södermanlandin lääni"
d_engtofin["Sweden Stockholm"] = "Ruotsi Tukholman lääni"
d_engtofin["Sweden Dalarna"] = "Ruotsi Taalainmaan lääni"


site = pywikibot.Site("fi", "wikipedia")
site.login()

# query: has template Kaupunki2 which uses location map
#
# TODO: also pages with template Arkeologinen kohde, 
# which has two different parameters to fix..
url = "https://petscan.wmflabs.org/?psid=25826661"
url += "&format=json"
url += "&output_limit=8000"
response = urlopen(url)
data_json = json.loads(response.read())

rivinro = 1

for row in data_json['*'][0]['a']['*']:
    page = pywikibot.Page(site, row['title'])
    oldtext = page.text
    changed = False

    print(" ////////", rivinro, ": [ " + row['title'] + " ] ////////")
    rivinro += 1

    if (oldtext.find("#OHJAUS") >= 0 or oldtext.find("#REDIRECT") >= 0):
        print("Skipping " + row['title'] + " - redirect-page.")
        continue
    if (oldtext.find("{{bots") > 0 or oldtext.find("{{nobots") > 0):
        print("Skipping " + row['title'] + " - bot-restricted.")
        continue
        
    # someone has marked the page as being under editing -> don't modify now
    if (oldtext.find("{{Työstetään") > 0 or oldtext.find("{{työstetään") > 0):
        print("Skipping " + row['title'] + " - editing in progress.")
        continue


    wikicode = mwparserfromhell.parse(page.text)
    templatelist = wikicode.filter_templates()

    for template in wikicode.filter_templates():
        if template.name.matches("Kaupunki2"):
            if template.has("pushpin_map"):
                
                par = template.get("pushpin_map")
                srcvalue = str(par.value)

                indexend = len(srcvalue)-1

                if (srcvalue.find("|") > 0):
                    indextemp = srcvalue.find("|")
                    srcvalue = srcvalue[:indextemp]
                    if (indextemp < indexend):
                        indexend = indextemp

                if (srcvalue.find("\n") > 0):
                    indextemp = srcvalue.find("\n")
                    srcvalue = srcvalue[:indextemp]
                    if (indextemp < indexend):
                        indexend = indextemp

                srcvalue = srcvalue.strip()

                # huom: teksti voi olla pidempi (esim. Skotlanti Ulko-Hebridit)
                # eli vain jos koko stringi täsmää -> korvaa kokonaan
                if (srcvalue in d_engtofin):
                    par.value.replace(srcvalue, d_engtofin[srcvalue])
                    
                changed = True

    if (changed == False):
        print("no change, skipping")
        continue

    newtext = str(wikicode)
    
    if oldtext == newtext:
        print("Skipping. " + row['title'] + " - old and new are equal.")
        continue

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, newtext,2)
    summary='Suomennetaan karttamalline'
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
        page.text=newtext
        page.save(summary)

