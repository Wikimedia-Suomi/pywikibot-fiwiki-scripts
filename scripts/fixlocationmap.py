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
d_engtofin["Germany"] = "Saksa"
d_engtofin["Finland"] = "Suomi"
d_engtofin["Estonia"] = "Viro"
d_engtofin["Denmark"] = "Tanska"
d_engtofin["Norway"] = "Norja" # done
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

d_engtofin["Azerbaijan"] = "Azerbaidžan"

d_engtofin["USA"] = "Yhdysvallat"
d_engtofin["Colombia"] = "Kolumbia"
d_engtofin["Mexico"] = "Meksiko"

d_engtofin["New Zealand"] = "Uusi-Seelanti" # done

d_engtofin["Japan"] = "Japani"
d_engtofin["Thailand"] = "Thaimaa"
d_engtofin["India"] = "Intia"
d_engtofin["Malaysia"] = "Malesia"

d_engtofin["Afghanistan"] = "Afganistan"
d_engtofin["South Korea"] = "Etelä-Korea"
d_engtofin["Iraq"] = "Irak"
d_engtofin["Yemen"] = "Jemen"
d_engtofin["Jordan"] = "Jordania"
d_engtofin["Cambodia"] = "Kambodža"
d_engtofin["Kyrgyzstan"] = "Kirgisia"
d_engtofin["Lebanon"] = "Libanon"
d_engtofin["Tajikistan"] = "Tadžikistan"
d_engtofin["Syria"] = "Syyria"
d_engtofin["Saudi Arabia"] = "Saudi-Arabia"
d_engtofin["North Korea"] = "Pohjois-Korea"

d_engtofin["Egypt"] = "Egypti"
d_engtofin["Kenya"] = "Kenia"
d_engtofin["Chad"] = "Tšad"
d_engtofin["Tanzania"] = "Tansania"
d_engtofin["Sao Tome and Principe"] = "São Tomé ja Príncipe"
d_engtofin["Zambia"] = "Sambia"
d_engtofin["Rwanda"] = "Ruanda"
d_engtofin["Equatorial Guinea"] = "Päiväntasaajan Guinea"
d_engtofin["Côte d'Ivoire"] = "Norsunluurannikko"
d_engtofin["Canary Islands"] = "Kanariansaaret"
d_engtofin["Cape Verde"] = "Kap Verde"
d_engtofin["Mozambique"] = "Mosambik"
d_engtofin["Cameroon"] = "Kamerun"
d_engtofin["Comoros"] = "Komorit"
d_engtofin["Morocco"] = "Marokko"
d_engtofin["Madagascar"] = "Madagaskar"
d_engtofin["Western Sahara"] = "Länsi-Sahara"
d_engtofin["South Africa"] = "Etelä-Afrikka"
d_engtofin["South Sudan"] = "Etelä-Sudan"
d_engtofin["Republic of the Congo"] = "Kongon tasavalta"
d_engtofin["Democratic Republic of the Congo"] = "Kongon demokraattinen tasavalta"

d_engtofin["China"] = "Kiina"
d_engtofin["China2"] = "Kiina2"
d_engtofin["China Liaoning"] = "Kiina Liaoning"
d_engtofin["China Shandong"] = "Kiina Shandong"
d_engtofin["China Guangdong"] = "Kiina Guangdong"

# canada done
d_engtofin["Canada"] = "Kanada"
d_engtofin["Canada Alberta"] = "Kanada Alberta" 
d_engtofin["Canada British Columbia"] = "Kanada Brittiläinen Kolumbia"
d_engtofin["Canada Manitoba"] = "Kanada Manitoba"
d_engtofin["Canada New Brunswick"] = "Kanada New Brunswick"
d_engtofin["Canada Newfoundland and Labrador"] = "Kanada Newfoundland ja Labrador"
d_engtofin["Canada Nova Scotia"] = "Kanada Nova Scotia"
d_engtofin["Canada Ontario"] = "Kanada Ontario"
d_engtofin["Canada Prince Edward Island"] = "Kanada Prinssi Edwardin saari"
d_engtofin["Canada Saskatchewan"] = "Kanada Saskatchewan"
d_engtofin["Canada Quebec"] = "Kanada Quebec"

# sweden done
d_engtofin["Sweden Västra Götaland"] = "Ruotsi Länsi-Götanmaan lääni"
d_engtofin["Sweden Skåne"] = "Ruotsi Skånen lääni"
d_engtofin["Sweden Norrbotten"] = "Ruotsi Norrbottenin lääni"
d_engtofin["Sweden Södermanland"] = "Ruotsi Södermanlandin lääni"
d_engtofin["Sweden Stockholm"] = "Ruotsi Tukholman lääni"
d_engtofin["Sweden Dalarna"] = "Ruotsi Taalainmaan lääni"

d_engtofin["Russia"] = "Venäjä"
d_engtofin["Russia European"] = "Venäjän Euroopan puoli"
d_engtofin["Russia Amur Oblast"] = "Venäjä Amurin alue"
d_engtofin["Russia Arkhangelsk Oblast"] = "Venäjä Arkangelin alue"
d_engtofin["Russia Arkhangelsk Oblast all"] = "Venäjä Arkangelin alue (kokonaan)"
d_engtofin["Republic of Bashkortostan"] = "Venäjä Baškortostan"
d_engtofin["Russia Brjansk Oblast"] = "Venäjä Brjanskin alue"
d_engtofin["Dagestan"] = "Venäjä Dagestan"
d_engtofin["Buryatia"] = "Venäjä Burjatia"
d_engtofin["Russia Khabarovsk Krai"] = "Venäjä Habarovskin aluepiiri"
d_engtofin["Russia Khanty–Mansi Autonomous Okrug"] = "Venäjä Hanti-Mansia"
d_engtofin["Russia Irkutsk Oblast"] = "Venäjä Irkutskin alue"
d_engtofin["Russia Yamalo-Nenets Autonomous Okrug"] = "Venäjä Jamalin Nenetsia"
d_engtofin["Russia Yaroslavl Oblast"] = "Venäjä Jaroslavlin alue"
d_engtofin["Russia Kaliningrad Oblast"] = "Venäjä Kaliningradin alue"
d_engtofin["Kalmykia"] = "Venäjä Kalmukia"
d_engtofin["Russia Kaluga Oblast"] = "Venäjä Kalugan alue"
d_engtofin["Russia Kamchatka Krai"] = "Venäjä Kamtšatkan aluepiiri"
d_engtofin["Russia Kirov Oblast"] = "Venäjä Kirovin alue"
d_engtofin["Russia Komi Republic"] = "Venäjä Komin tasavalta"
d_engtofin["Russia Kostroma Oblast"] = "Venäjä Kostroman alue"
d_engtofin["Russia Krasnodar Krai"] = "Venäjä Krasnodarin aluepiiri"
d_engtofin["Russia Krasnoyarsk Krai"] = "Venäjä Krasnojarskin aluepiiri"
d_engtofin["Russia Kursk Oblast"] = "Venäjä Kurskin alue"
d_engtofin["Russia Magadan Oblast"] = "Venäjä Magadanin alue"
d_engtofin["Russia Mari El Republic"] = "Venäjä Marin tasavalta"
d_engtofin["Russia Mordovia"] = "Venäjä Mordva"
d_engtofin["Russia Moscow Oblast"] = "Venäjä Moskovan alue"
d_engtofin["Murmansk oblast"] = "Venäjä Murmanskin alue"
d_engtofin["Russia Nenets Autonomous Okrug"] = "Venäjä Nenetsia"
d_engtofin["Russia Nizhny Novgorod Oblast"] = "Venäjä Nižni Novgorodin alue"
d_engtofin["Russia Novosibirsk Oblast"] = "Venäjä Novosibirskin alue"
d_engtofin["Russia Orenburg Oblast"] = "Venäjä Orenburgin alue"
d_engtofin["Russia Saint Petersburg"] = "Venäjä Pietari"
d_engtofin["Russia Pskov oblast"] = "Venäjä Pihkovan alue"
d_engtofin["Russia Primorsky Krai"] = "Venäjä Primorjen aluepiiri"
d_engtofin["Russia Rostov Oblast"] = "Venäjä Rostovin alue"
d_engtofin["Russia Sakhalin Oblast"] = "Venäjä Sahalinin alue"
d_engtofin["Russia Sakha Republic"] = "Venäjä Sahan tasavalta"
d_engtofin["Russia Samara Oblast"] = "Venäjä Samaran alue"
d_engtofin["Russia Smolensk Oblast"] = "Venäjä Smolenskin alue"
d_engtofin["Russia Sverdlovsk Oblast"] = "Venäjä Sverdlovskin alue"
d_engtofin["Russia Republic of Tatarstan"] = "Venäjä Tatarstan"
d_engtofin["Russia Tomsk Oblast"] = "Venäjä Tomskin alue"
d_engtofin["Russia Chelyabinsk Oblast"] = "Venäjä Tšeljabinskin alue"
d_engtofin["Russia Chukotka Autonomous Okrug"] = "Venäjä Tšukotka"
d_engtofin["Russia Tver Oblast"] = "Venäjä Tverin alue"
d_engtofin["Russia Republic of Udmurtia"] = "Venäjä Udmurtia"
d_engtofin["Russia Vladimir Oblast"] = "Venäjä Vladimirin alue"
d_engtofin["Russia Volgograd Oblast"] = "Venäjä Volgogradin alue"
d_engtofin["Russia Vologda Oblast"] = "Venäjä Vologdan alue"
d_engtofin["Russia Novgorod Oblast"] = "Venäjä Novgorodin alue"
d_engtofin["Republic of Karelia"] = "Venäjä Karjalan tasavalta"
d_engtofin["Russia Karelia Aunuksen piiri"] = "Russia Karelia Aunuksen piiri"
d_engtofin["Russia Karelia Belomorskin piiri"] = "Venäjä Karjalan tasavalta Belomorskin piiri"
d_engtofin["Russia Karelia Kalevalan piiri"] = "Venäjä Karjalan tasavalta Kalevalan piiri"
d_engtofin["Russia Karelia Karhumäen piiri"] = "Venäjä Karjalan tasavalta Karhumäen piiri"
d_engtofin["Russia Karelia Kemin piiri"] = "Venäjä Karjalan tasavalta Kemin piiri"
d_engtofin["Russia Karelia Kontupohjan piiri"] = "Venäjä Karjalan tasavalta Kontupohjan piiri"
d_engtofin["Russia Karelia Lahdenpohjan piiri"] = "Venäjä Karjalan tasavalta Lahdenpohjan piiri"
d_engtofin["Russia Karelia Louhen piiri"] = "Venäjä Karjalan tasavalta Louhen piiri"
d_engtofin["Russia Karelia Mujejärven piiri"] = "Venäjä Karjalan tasavalta Mujejärven piiri"
d_engtofin["Russia Karelia Pitkärannan piiri"] = "Venäjä Karjalan tasavalta Pitkärannan piiri"
d_engtofin["Russia Karelia Prääsän piiri"] = "Venäjä Karjalan tasavalta Prääsän piiri"
d_engtofin["Russia Karelia Puutoisen piiri"] = "Venäjä Karjalan tasavalta Puudožin piiri"
d_engtofin["Russia Karelia Sekeen piiri"] = "Venäjä Karjalan tasavalta Segežan piiri"
d_engtofin["Russia Karelia Sortavalan piiri"] = "Venäjä Karjalan tasavalta Sortavalan piiri"
d_engtofin["Russia Karelia Suojärven piiri"] = "Venäjä Karjalan tasavalta Suojärven piiri"
d_engtofin["Russia Karelia Äänisenrannan piiri"] = "Venäjä Karjalan tasavalta Äänisenrannan piiri"

d_engtofin["Russia Leningrad Oblast"] = "Venäjä Leningradin alue"
d_engtofin["Russia Leningrad Hatsinan piiri"] = "Venäjä Leningradin alue Hatsinan piiri"
d_engtofin["Russia Leningrad Kirišin piiri"] = "Venäjä Leningradin alue Kirišin piiri"
d_engtofin["Russia Leningrad Jaaman piiri"] = "Venäjä Leningradin alue Jaaman piiri"
d_engtofin["Russia Leningrad Kirovskin piiri"] = "Venäjä Leningradin alue Korotkan piiri"
d_engtofin["Russia Leningrad Koskenalan piiri"] = "Venäjä Leningradin alue Koskenalan piiri"
d_engtofin["Russia Leningrad Käkisalmen piiri"] = "Venäjä Leningradin alue Käkisalmen piiri"
d_engtofin["Russia Leningrad Laukaan piiri"] = "Venäjä Leningradin alue Laukaan piiri"
d_engtofin["Russia Leningrad Lomonosovin piiri"] = "Venäjä Leningradin alue Lomonosovin piiri"
d_engtofin["Russia Leningrad Lotinapellon piiri"] = "Venäjä Leningradin alue Lotinapellon piiri"
d_engtofin["Russia Leningrad Olhavan piiri"] = "Venäjä Leningradin alue Olhavan piiri"
d_engtofin["Russia Leningrad Seuloskoin piiri"] = "Venäjä Leningradin alue Seuloskoin piiri"
d_engtofin["Russia Leningrad Slantsyn piiri"] = "Venäjä Leningradin alue Slantsyn piiri"
d_engtofin["Russia Leningrad Tihvinän piiri"] = "Venäjä Leningradin alue Tihvinän piiri"
d_engtofin["Russia Leningrad Tusinan piiri"] = "Venäjä Leningradin alue Tusinan piiri"
d_engtofin["Russia Leningrad Viipurin piiri"] = "Venäjä Leningradin alue Viipurin piiri"
d_engtofin["Russia Leningrad Volossovan piiri"] = "Venäjä Leningradin alue Volossovan piiri"


site = pywikibot.Site("fi", "wikipedia")
site.login()

# query: has template Kaupunki2 which uses location map
#
# TODO: also pages with template Arkeologinen kohde, 
# which has two different parameters to fix..
# european: 25830419, 14000 pages..
#url = "https://petscan.wmflabs.org/?psid=25830419"
#url = "https://petscan.wmflabs.org/?psid=25834114"
url = "https://petscan.wmflabs.org/?psid=25898940"
url += "&format=json"
url += "&output_limit=15000"
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

    if site.userinfo['messages']:
        print("Warning: Talk page messages. Exiting.")
        exit()

    pywikibot.info('----')
    pywikibot.showDiff(oldtext, newtext,2)
    summary='Suomennetaan karttamalline'
    pywikibot.info('Edit summary: {}'.format(summary))

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

