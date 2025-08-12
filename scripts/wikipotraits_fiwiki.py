import pywikibot
from pywikibot.data.superset import SupersetQuery

def get_wikidata_ids(sitename, titles, batch_size: int = 50):
        site=site_from_code(sitename)

        results = {}

        # Process titles in batches
        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            # Prepare API parameters
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'pageprops',
                'ppprop': 'wikibase_item',
                'titles': '|'.join(batch),
                'formatversion': 2
            }

            try:
                # Make the API request using current pywikibot method
                request = pywikibot.data.api.Request(site=site, parameters=params)
                response = request.submit()

                # Process the response
                if 'query' in response and 'pages' in response['query']:
                    for page_data in response['query']['pages']:
                        title = page_data.get('title', '')
                        wikidata_id = None

                        if 'pageprops' in page_data and 'wikibase_item' in page_data['pageprops']:
                            wikidata_id = page_data['pageprops']['wikibase_item']

                        results[title] = wikidata_id

            except Exception as e:
                print(f"Error processing batch {i//batch_size + 1}: {e}")
                # Add None for all titles in this batch
                for title in batch:
                    results[title] = None

        return results


def site_from_code(code: str) -> pywikibot.site.APISite:
    # "frwiki" -> Site('fr','wikipedia')
    if code.endswith('wiki'):
        return pywikibot.Site(code[:-4], 'wikipedia')
    raise ValueError(f"Unexpected site code: {code}")


# target wiki (lang, family)
site = pywikibot.Site("commons", "commons")

# create a Superset query helper bound to that wiki
sq = SupersetQuery(site=site)

# run SQL against the replica schema behind that wiki
rows = sq.query("""
SELECT
    p2.page_title as image,
    gil_wiki,
    gil_page_namespace,
    gil_page_title
FROM
        globalimagelinks AS g,
    page AS p2,
    categorylinks,
    (
      SELECT
        p1.page_title AS page_title
      FROM
        page AS p1,
        categorylinks AS cl1
      WHERE (
        cl1.cl_to="Wikiportrait_uploads"
        AND cl1.cl_type = "subcat"
        AND p1.page_id=cl1.cl_from
      )
      UNION
        SELECT "Wikiportrait_uploads" AS page_title
    ) AS c
WHERE
        p2.page_id=cl_from
    AND c.page_title=cl_to
    AND p2.page_title=gil_to
GROUP BY gil_to, gil_page_title, gil_wiki

""")

images={}
for row in rows:
    i=row['image']
    if i not in images:
        image={}
        image['sites']=[]
        image['data']=[]
        images[i]=image
    images[i]['sites'].append(row['gil_wiki'])
    images[i]['data'].append(row)

FIWIKI = pywikibot.Site('fi', 'wikipedia')
cache={}
printed=[]

site_pages={}

for i in images:
    print(".", end="")
    for wikipage in images[i]['data']:
        if 'fiwiki' in images[i]['sites']:
            continue

        if wikipage['gil_page_namespace']!="":
            continue

        if wikipage['gil_wiki']=="wikidatawiki":
            continue

        try:
            src_site=site_from_code(wikipage['gil_wiki'])
        except:
            continue

        if wikipage['gil_wiki'] not in site_pages:
            site_pages[wikipage['gil_wiki']]=[]
        site_pages[wikipage['gil_wiki']].append(wikipage['gil_page_title'])


wikidata_ids_filter=[]
wikidata_ids={}
site_pages2={}
for sitename in site_pages:
    if sitename not in site_pages2:
        site_pages2[sitename]={}
    pages = get_wikidata_ids(sitename, site_pages[sitename])
    for page in pages:
        if pages[page]:
            wikidata_ids_filter.append(pages[page])
        if pages[page] not in wikidata_ids:
            wikidata_ids[pages[page]]={}
        wikidata_ids[pages[page]][sitename]=page
        site_pages2[sitename][page]=pages[page]



wikidata_ids_filter= list(set(wikidata_ids_filter))

# create a Superset query helper bound to that wiki
sq = SupersetQuery(site=FIWIKI)

ids_formatted = "', '".join(wikidata_ids_filter)

# run SQL against the replica schema behind that wiki
query="""
SELECT page_title, pp_value
FROM page, page_props
WHERE
page_id=pp_page
AND page_namespace=0
AND pp_value IN ('__IDS_FORMATTED__' )
AND pp_propname  = 'wikibase_item'
"""

query=query.replace('__IDS_FORMATTED__', ids_formatted)
print(query)

rows = sq.query(query)

fiwiki_map={}

for row in rows:
    fiwiki_map[row['pp_value']]=row['page_title']

printed=[]

for i in images:
    for wikipage in images[i]['data']:
        if 'fiwiki' in images[i]['sites']:
            continue

        if wikipage['gil_page_namespace']!="":
            continue

        if wikipage['gil_wiki']=="wikidatawiki":
            continue

        try:
            src_site=site_from_code(wikipage['gil_wiki'])
        except:
            continue

        try:
            wikidata_id=site_pages2[wikipage['gil_wiki']][wikipage['gil_page_title'].replace("_", " ")]
        except:
            if i=="Bart_Schneemann.jpg":
                print(site_pages2[wikipage['gil_wiki']])
                print(wikipage)
                print("ERROR")
                exit(1)
            continue
        if wikidata_id in fiwiki_map:
            out=f'{i}|{{{{Q|{wikidata_id}}}}}\t[[{fiwiki_map[wikidata_id].replace("_", " ")}]]'
            if out not in printed:
                print(out)
                printed.append(out)

