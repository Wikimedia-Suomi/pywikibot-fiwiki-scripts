# Script will find articles about women in fiwiki without image, but which have depicted images in commons.

mport pywikibot
from pywikibot.data import sparql

lang='fi'
wikipedia_uri=f'https://{lang}.wikipedia.org/'
wikipedia_site = pywikibot.Site(lang, 'wikipedia')
wikidata_site = pywikibot.Site("wikidata", "wikidata")
commons_site = pywikibot.Site('commons', 'commons')
commons_site.login()

query = '''
SELECT DISTINCT ?media ?depicts ?article WITH {
  SELECT DISTINCT ?media ?depicts ?finna_id ?image WHERE {
    ?media wdt:P9478 ?finna_id .
    ?media wdt:P180 ?depicts .
    ?media schema:url ?image.
    }
} AS %mediaitems
WHERE
{
  include %mediaitems
  SERVICE <https://query.wikidata.org/sparql>  {
    ?depicts wdt:P31 wd:Q5 .
    ?depicts wdt:P21 ?gender .
    ?article schema:about ?depicts ; schema:isPartOf <WIKIPEDIA_URI> ;  .
    MINUS { ?depicts wdt:P21 wd:Q6581097} .
    MINUS { ?depicts wdt:P21 wd:Q44148 } .
    MINUS { ?depicts wdt:P21 wd:Q2449503 }
  }
}
ORDER BY ?image
'''

query=query.replace('WIKIPEDIA_URI', wikipedia_uri)
print(commons_site.user())
entity_url='https://commons.wikimedia.org/entity/'
endpoint='https://commons-query.wikimedia.org/sparql'
dependencies = {'endpoint': endpoint, 'entity_url': entity_url}

query_object = sparql.SparqlQuery(**dependencies)  # type: ignore[arg-type]
data=query_object.select(query, full_data=True)
for row in data:
#    item_id=str(row['depicts']).replace('http://www.wikidata.org/entity/', '')
    wikipedia_page_title = str(row['article']).replace(wikipedia_uri +'wiki/', '')
    if wikipedia_page_title:
        wikipedia_page = pywikibot.Page(wikipedia_site, wikipedia_page_title)
        page_image=wikipedia_page.page_image()
        if not page_image:
            image_page_id=int(str(row['media']).replace('https://commons.wikimedia.org/entity/M', ''))
            image = list(commons_site.load_pages_from_pageids([image_page_id]))[0]
            wikipedia_page_title=wikipedia_page_title.replace("_", " ")
            print(f'{image.title()}|[[{wikipedia_page_title}]]')
        else:
            print(".", end="")
