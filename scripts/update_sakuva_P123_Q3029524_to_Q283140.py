import pywikibot
import json
from pywikibot.data import sparql

# Get files to be updated
def get_sparql_filelist():
    # Define the SPARQL query
    query = """

SELECT ?item ?described_url WHERE {
  ?item wdt:P7482 wd:Q74228490 .       # P7482 (source of file) = Q74228490 (file available on the internet)
  ?item p:P7482 ?statement .
  ?statement pq:P137 wd:Q420747.       # P137 (operator) = Q420747 (National Library of Finland)
  ?statement pq:P123 wd:Q3029524.      # P123 (publisher) = Q3029524 (Finnish Heritage Agency)

  ?statement pq:P973 ?described_url.
  FILTER(CONTAINS(STR(?described_url), "sa-kuva"))
}
"""

    # Set up the SPARQL endpoint and entity URL
    # Note: https://commons-query.wikimedia.org requires user to be logged in

    entity_url = 'https://commons.wikimedia.org/entity/'
    endpoint = 'https://commons-query.wikimedia.org/sparql'

    # Create a SparqlQuery object
    query_object = sparql.SparqlQuery(endpoint= endpoint, entity_url= entity_url)

    # Execute the SPARQL query and retrieve the data
    data = query_object.select(query, full_data=True)
    return data


def edit_with_confirmation(site, page, statement, qualifier, oldvalue, newvalue):
    # Capture original text
    oldtext=json.dumps(qualifier.toJSON(),indent=2)

    # Update text
    qualifier.target = pywikibot.ItemPage(wikidata_site, newvalue)
    newtext=json.dumps(qualifier.toJSON(),indent=2)

    # Confirmation
    pywikibot.showDiff(oldtext, newtext,context=10)
    question=page.title() + ' - Do you want to accept these changes?'
    choice = pywikibot.input_choice(
            question,
            [('Yes', 'Y'), ('No', 'n')],
            default='Y',
            automatic_quit=False
    )
    # Edit
    if choice.lower() == 'y':
        site.editQualifier(statement, qualifier, summary=f'Fix: Changing qualifier P123 (publisher) from {oldvalue} (Finnish heritage agency)  to {newvalue} (Military museum)')
        return True

def update_operator_item(site, page, oldvalue, newvalue, testvalue):
    updated=False
    print(page.title())
    page = pywikibot.FilePage(site, pages[0].title())
    item = page.data_item()
    data = item.get()

    # Basic sanitycheck
    if not testvalue in json.dumps(data['statements'].toJSON()):
        print("ERROR: testvalue not found")
        exit(1)

    if 'statements' in data:
        statements = data['statements'] 
        # P7482 = Source of file
        if 'P7482' in statements:
            if len(statements['P7482']) != 1:
                print("ERROR: Unexpected P7482 count")
                exit(1)
            for statement in statements['P7482']:
                # P123 = Publisher
                if 'P123' in statement.qualifiers:
                    if len(statement.qualifiers['P123']) != 1:
                        print("ERROR: Unexpected P7482.P123 count")
                        exit(1)

                    for qualifier in statement.qualifiers['P123']:
                        if qualifier.target.id == oldvalue:
                            updated=edit_with_confirmation(site, page, statement, qualifier, oldvalue, newvalue)
                    

    return updated


site = pywikibot.Site('commons', 'commons')
wikidata_site = pywikibot.Site('wikidata', 'wikidata')
site.login()
print('----')
print(site.user())

rows=get_sparql_filelist()

# Iterate through the SPARQL results and print the file page titles and their associated values
for row in rows:
    page_id=int(row['item'].getID().replace('M',''))
    pages = list(site.load_pages_from_pageids([page_id]))

    # Test that number of pages is expected
    if len(pages) == 1:
        oldvalue='Q3029524' # Q3029524 = Finnish Heritage Agency
        newvalue='Q283140' # Q283140 = Military Museum of Finland
        testvalue='sa-kuva.'

        updated=update_operator_item(site, pages[0], oldvalue, newvalue, testvalue)
        if updated:
            print("Updated: " + pages[0].title())
    else:
        print("ERROR: Incorrect result number")
        exit(1)
        
    

