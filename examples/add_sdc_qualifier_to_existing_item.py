mport pywikibot

# Add qualifier to existing item
# https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Setting_qualifiers
def add_qualifier(item, claim, qualifier_prop, qualifier_value):
    wikidata_site = pywikibot.Site("wikidata", "wikidata")
    print(f'Adding qualifier: {qualifier_prop} {qualifier_value} to claim value {claim.getTarget()}')
    
    # Create qualifier
    qualifier = pywikibot.Claim(wikidata_site, qualifier_prop)
    qualifier_target = pywikibot.ItemPage(wikidata_site, qualifier_value)
    qualifier.setTarget(qualifier_target)
    
    # Add qualifier to claim. This already saves the edit.
    claim.addQualifier(qualifier)


# Return False if qualifier with qualifier_value doesn't exits

def test_if_qualifier_exists(claim, qualifier_prop, qualifier_value):
    if not claim.qualifiers:
        return False
    
    elif not qualifier_prop in claim.qualifiers:
        return False
    
    else:
        for qualifier in claim.qualifiers[qualifier_prop]:
            qualifier_value = qualifier.getTarget()
            if qualifier_value == qualifier.getTarget():
                return True

### MAIN()

# Connect to Wikidata
site = pywikibot.Site("commons", "commons")
repo = site.data_repository()

# Load the commons item
page = pywikibot.FilePage(site, 'File:Akateemisen Karjala-Seuran 15-vuotisjuhlat Vanhalla ylioppilastalolla 21.2.1937.jpg')  # Specify the file
item = page.data_item()  # Get the data item associated with the page

# Identify the claim (assuming you know the property ID)
property_id = "P9310"  # Replace with the actual property ID of the claim
claims = item.claims[property_id]

qualifier_prop = "P459"
qualifier_value = "Q104884110"

# Loop through claims
for claim in claims:
    print(f"Property: {property_id}, Value: {claim.getTarget()}")
    
    qualifier_exists = test_if_qualifier_exists(claim, qualifier_prop, qualifier_value)
        
    if qualifier_exists:
        print(f'Qualifier: {qualifier_prop} : {qualifier_value} already exists.')
    else:
        add_qualifier(item, claim, qualifier_prop, qualifier_value)
 
