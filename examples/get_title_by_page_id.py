# Example for getting page title using page_id

import pywikibot

def get_page_title(site, page_id):
    pages = site.load_pages_from_pageids([page_id])
    for page in pages:
        return page.title()

site = pywikibot.Site('commons','commons')
page_id = '132663930'  # replace with your page ID
print(get_page_title(site, page_id))
