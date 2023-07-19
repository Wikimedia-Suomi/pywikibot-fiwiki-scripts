# Howto add multiple claims with one edit in Wikidata
# NOTE: This doesnt work in Structured data on commons.

import pywikibot

site = pywikibot.Site("wikidata", "wikidata")

# Retrieve the item Q15397819 (Sandbox item three)
item = pywikibot.ItemPage(site, "Q15397819")

# Check if the item exists
if not item.exists():
    print("Item Q123456 does not exist")
else:
    
    # Create Claim object for each collection
    claim1 = pywikibot.Claim(site, "P195", datatype='wikibase-item')  # Property:P195 for "collections"
    claim2 = pywikibot.Claim(site, "P195", datatype='wikibase-item')  # Property:P195 for "collections"

    # Create ItemPage objects for Finland and Sweden
    collection1 = pywikibot.ItemPage(site, "Q107388072")  # ItemPage for historical_picture_collection
    collection2 = pywikibot.ItemPage(site, "Q120728209")  # ItemPage for Pietinen collection

    # Set the target value of the claims
    claim1.setTarget(collection1)
    claim2.setTarget(collection2)

    # Actual edit
    new_claims = [ claim1.toJSON(), claim2.toJSON() ] 
    item.editEntity({'claims': new_claims }, summary="Adding P195")
