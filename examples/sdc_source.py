# Script adds source information to SDC
# Example exit
# - https://commons.wikimedia.org/w/index.php?title=File%3AAkateemisen_Karjala-Seuran_15-vuotisjuhlat_Vanhalla_ylioppilastalolla_21.2.1937.jpg&diff=769748618&oldid=769747981

import pywikibot

# Accessing wikidata properties and items
wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata

# Wikimedia Commons Structured data access
commons_site = pywikibot.Site("commons", "commons")  # Connect to Wikimedia Commons
commons_site.login()
page = pywikibot.FilePage(commons_site, 'File:Akateemisen Karjala-Seuran 15-vuotisjuhlat Vanhalla ylioppilastalolla 21.2.1937.jpg')  # Specify the file
item = page.data_item()  # Get the data item associated with the page

# Get claims
data=item.get()
claims = data['statements']  # Get the item's current claims

source_prop = 'P7482'  # property ID for "source of file"
if source_prop not in claims:

    # Create main value

    # P7482 "source of file" 
    claim_target = pywikibot.ItemPage(wikidata_site, 'Q74228490')  # file available on the internet
    new_claim = pywikibot.Claim(wikidata_site, source_prop)
    new_claim.setTarget(claim_target)

    # Now we'll add the qualifiers

    # P973 "described at URL"
    qualifier_url = pywikibot.Claim(wikidata_site, 'P973')  # property ID for "described at URL"
    qualifier_url.setTarget('https://www.finna.fi/Record/hkm.HKMS000005:km0000nlbh')
    new_claim.addQualifier(qualifier_url, summary='Adding described at URL qualifier')

    # P137 "operator"
    qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')  # Replace with the property ID for "operator"
    qualifier_target = pywikibot.ItemPage(wikidata_site, 'Q420747')  # National Library of Finland (Kansalliskirjasto)
    qualifier_operator.setTarget(qualifier_target)
    new_claim.addQualifier(qualifier_operator, summary='Adding operator qualifier')

    # P123 "publisher"
    qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')  # property ID for "publisher"
    qualifier_target = pywikibot.ItemPage(wikidata_site, 'Q3029524')  # Finnish Heritage Agency (Museovirasto)
    qualifier_publisher.setTarget(qualifier_target)
    new_claim.addQualifier(qualifier_publisher, summary='Adding publisher qualifier')

    # Write changes
    commons_site.addClaim(item,new_claim)
    print("Added statement P7482")

else:
    print("Skipping: Statement P7482 - source of file already exits")
