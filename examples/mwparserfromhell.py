import pywikibot
import mwparserfromhell

site = pywikibot.Site('commons', 'commons')  # The site we're working on
page = pywikibot.Page(site, 'File:Veli-Aine-1994.jpg')  # The page you're interested in

wikicode = mwparserfromhell.parse(page.text)

template = wikicode.filter_templates(matches=lambda template: template.name.matches("Information"))[0]
parameter = template.get("Source") 
parameter.value = str(parameter.value).strip() + " foobarbiz\n"

modified_wikitext = str(wikicode)

print(modified_wikitext)
