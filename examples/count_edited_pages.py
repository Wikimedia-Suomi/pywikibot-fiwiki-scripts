import pywikibot
from datetime import datetime

site = pywikibot.Site('wikidata', 'wikidata')
user = pywikibot.User(site, 'Zache')

start_date = datetime(2022, 1, 1)
end_date = datetime(2022, 12, 31)

contributions = user.contributions(total=50000, namespaces=[0])

# Filter contributions by date and remove duplicates
distinct_page_contributions = set()
for contrib in contributions:
    page, rev_id, timestamp, comment = contrib
    year=timestamp.year

    if start_date <= timestamp <= end_date:
        distinct_page_contributions.add(page.title())

    if year==2021:
        break

# Count distinct contributions
num_pages = len(distinct_page_contributions)
print(num_pages)
