
#!/usr/bin/env python3
# The script prints quickstatement commands for adding language (P407) qualifier
# to videos (P10) in Spanish language (Q1321)
#
# Usage:
# python3 -m venv venv
# source venv/bin/activate
# pip install pywikibot SPARQLWrapper
# python generate_quickstatement_commants_for_adding_P407_to_videos.py


from SPARQLWrapper import SPARQLWrapper, JSON
from urllib.parse import unquote
from datetime import datetime
import urllib.parse
import pywikibot
import requests

CATEGORY = 'Videos_in_Spanish'
LANGUAGE_KEYWORD = 'Spanish'
LANGUAGE_QID = 'Q1321'

# Initialize Commons site
commonssite = pywikibot.Site('commons', 'commons')

def fetch_petscan_categories(petscan_url):
    """
    Fetch category titles from a Petscan 
    """
    resp = requests.get(petscan_url)
    resp.raise_for_status()
    data = resp.json()
    cats = []
    # Navigate JSON structure: top-level key "*" is a list, then each has key 'a'->'*' list of categories
    for entry in data.get('*', []):
        a = entry.get('a', {})
        for cat in a.get('*', []):
            title = cat.get('title')
            if title:
                # Category titles come as 'Category:Name'
                cat_page = pywikibot.Page(commonssite, f'Category:{title}', ns=14)
                cats.append(cat_page.title())
    return set(cats)


def fetch_petscan_pages(url):
    """
    Fetch page titles from a Petscan JSON and normalize via pywikibot.Page.title().
    """
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    pages = set()
    for entry in data.get('*', []):
        a = entry.get('a', {})
        for p in a.get('*', []):
            title = p.get('title')
            if title:
                # Normalize file title
                page = pywikibot.Page(commonssite, title, ns=6)
                pages.add(page.title())
    return pages


def run_sparql_query():
    """
    Run the SPARQL query against Wikidata to fetch items and video URLs.
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery("""
    SELECT ?item ?video WHERE {
        ?item p:P10 ?p10Stmt .
        ?p10Stmt ps:P10 ?video .
        FILTER NOT EXISTS { ?p10Stmt pq:P407 ?lang }
        FILTER(REGEX(STR(?item), "/Q[0-9]+$"))
        FILTER(!REGEX(STR(?video), "[.]gif$", "i"))
    }
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results["results"]["bindings"]

def get_page_from_file_url(file_url):
    """
    Parse filename from url and create page from it
    """
    path = urllib.parse.urlparse(file_url).path
    raw_filename = path.split('/')[-1]
    decoded = unquote(raw_filename)
    # Normalize via pywikibot
    file_page = pywikibot.Page(commonssite, f'File:{decoded}', ns=6)
    return file_page

def main():
    # Petscan query for getting the videos in target language
    petscan_file_url = (
        'https://petscan.wmcloud.org/?psid=35618112&format=json'
        '&categories=' + CATEGORY
    )
    petscan_pages = fetch_petscan_pages(petscan_file_url)

    # Petscan query for getting categories containg the videos in the target language
    petscan_cats_url = (
        'https://petscan.wmcloud.org/?psid=35620397&format=json'
        '&categories=' + CATEGORY
    )
    petscan_cats = fetch_petscan_categories(petscan_cats_url)

    # Get target wikidata items
    items = run_sparql_query()

    # Loop items
    for r in items:
        # Extract QID
        item_uri = r['item']['value']
        qid = item_uri.rsplit('/', 1)[-1]

        # Parse the video URL to get filename and URL-decode it
        video_url = r['video']['value']
        file_page = get_page_from_file_url(video_url)
        norm_title = file_page.title()

        # Process only files which are in target language files
        if norm_title in petscan_pages:
            source_cat = ''
            for cat in file_page.categories():
                cat_title = cat.title()
                if cat_title in petscan_cats:
                    if LANGUAGE_KEYWORD in cat_title:
                        source_cat = cat_title
                        break
                    source_cat = cat_title

            if source_cat:
                norm_title_without_ns=norm_title.replace('File:', '')
                current_ts = datetime.utcnow().strftime("+%Y-%m-%dT00:00:00Z/11")
                source_cat_norm=source_cat.replace(' ', '_')

                # Print quickstatement command
                print(f"{qid}|P10|\"{norm_title_without_ns}\"|P407|{LANGUAGE_QID}|S143|Q565|S887|Q133818885|S4656|\"https://commons.wikimedia.org/wiki/{source_cat_norm}\"|S813|{current_ts}")

if __name__ == "__main__":
    main()


