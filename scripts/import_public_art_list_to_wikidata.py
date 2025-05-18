!/usr/bin/env python3
"""
Script to parse the Finnish Wikipedia page of Raisio's public artworks and memorials,
extracting data and creating Wikidata items for artworks missing them.
Outputs JSON and updates the Wikipedia page table with new Wikidata IDs,
and adds proper sourcing (P143 & P4656 as a single reference), focus list (P5008),
stores "Paikka" into P2795 (directions) as Finnish monolingual text,
parses any street address from "Paikka" into P969, and if a wikilink appears in the "alue" or "paikka" fields,
prompts whether to use that article's Wikidata QID as P276 (location).


Usage

# python3 -m venv venv
# source venv/bin/activate

Create user-config.py
> usernames['wikidata']['wikidata'] = 'yoursername'
> usernames['wikipedia']['fi'] = 'yoursername' 

# python import_public_art_list_to_wikidata.py

"""
import re
import json
import pywikibot
import mwparserfromhell
from pywikibot import (
    Claim,
    WbMonolingualText,
    Coordinate,
    WbTime
)

# Initialize site and repository
site = pywikibot.Site('fi', 'wikipedia')
repo = site.data_repository()

# Mapping of art type descriptions to Wikidata Q-items
ART_TYPE_MAP = {
    'veistos': 'Q860861',
    'muraali': 'Q219423',
    'muistomerkki': 'Q5003624',
    'muistokivi': 'Q11734477',
    'muistolaatta': 'Q721747'
}

# Source page and import URL (filled in main)
SOURCE_PAGE_TITLE = 'Luettelo Raision julkisista taideteoksista ja muistomerkeistä'
IMPORT_URL = None


def prompt(text):
    return input(text + ' ')


def create_wikidata_item(entry):
    """
    Given an entry dict, create a new Wikidata item with all
    the desired claims, each properly sourced with:
      - P143 → Q175482 (imported from Finnish Wikipedia)
      - P4656 → the exact import URL
    Also adds:
      - P5008 (focus list)
      - P276 or P2795 depending on user choice
      - P969 (street address) from entry['address'], if present
    """

    def add_claim_with_sources(prop, target, summary):
        c = Claim(repo, prop)
        c.setTarget(target)
        # Two source-claims
        s1 = Claim(repo, 'P143')
        s1.setTarget(pywikibot.ItemPage(repo, 'Q175482'))
        s2 = Claim(repo, 'P4656')
        s2.setTarget(IMPORT_URL)
        # Add main claim and attach sources as one reference
        item.addClaim(c, summary=summary)
        c.addSources([s1, s2], summary='Add import references')

    # Display info for confirmation
    print("\n=== Artwork Information ===")
    print(f"Title: {entry['teos_nimi']}\n"
          f"Artist: {entry['tekijä']}\n"
          f"Inception Year: {entry['paljastusvuosi']}\n"
          f"Location link name: {entry['paikkalinkki_nimi']}\n"
          f"Coordinates: {entry['latitude']}, {entry['longitude']}\n"
          f"Paikka (directions): {entry['paikka']}\n"
          f"Alue: {entry['alue']}\n"
          f"Street address: {entry.get('address') or 'None'}")

    # Determine label
    label = entry['varmistettu_nimi'] or prompt(f"Enter title for artwork '{entry['teos_nimi']}':")
    if not label:
        label = entry['teos_nimi']

    # Select artwork type
    print("Select the type of artwork:")
    opts = list(ART_TYPE_MAP.keys())
    for i, o in enumerate(opts, 1):
        print(f"{i}. {o}")
    while True:
        ch = prompt("Choice (number):").strip()
        if ch.isdigit() and 1 <= (idx := int(ch)) <= len(opts):
            art_type = opts[idx-1]
            break
        print("Invalid choice.")
    instance_q = ART_TYPE_MAP[art_type]

    # Create new Wikidata item
    item = pywikibot.ItemPage(repo)
    labels = {'fi': label}
    if entry.get('varmistettu_nimi'):
        labels['mul'] = entry['varmistettu_nimi']
    item.editLabels(labels, summary='Add artwork entry from Raisio list')

    # P1448 Official name
    add_claim_with_sources('P1448', WbMonolingualText(label, 'fi'), 'Add official name')
    # P31 Instance of
    add_claim_with_sources('P31', pywikibot.ItemPage(repo, instance_q), 'Add instance of (artwork type)')

    # Descriptions
    item.editDescriptions(
        {'fi': f"{art_type} Raisiossa, Finland",
         'en': f"{art_type} in Raisio, Finland"},
        summary='Add description'
    )

    # P17 Country → Finland
    add_claim_with_sources('P17', pywikibot.ItemPage(repo, 'Q33'), 'Add country')
    # P131 Located in → Raisio
    add_claim_with_sources('P131', pywikibot.ItemPage(repo, 'Q372075'), 'Add located in')

    # Handle wikilinks in 'alue'/'paikka' for P276 or fallback P2795
    link_pattern = re.compile(r"\[\[([^|\]]+)")
    match_area = link_pattern.search(entry.get('alue', ''))
    match_place = link_pattern.search(entry.get('paikka', ''))
    if match_area or match_place:
        article = match_area.group(1) if match_area else match_place.group(1)
        use_loc = prompt(
            f"Field 'alue'/'paikka' contains link to '{article}'. Use its Wikidata QID as P276 (location)? (y/n):"
        ).strip().lower()
        if use_loc == 'y':
            try:
                loc_item = pywikibot.ItemPage.fromPage(pywikibot.Page(site, article))
                add_claim_with_sources('P276', loc_item, 'Add location (P276)')
            except Exception:
                print(f"Could not find Wikidata item for article '{article}'. Adding P2795 instead.")
                add_claim_with_sources('P2795', WbMonolingualText(entry['paikka'], 'fi'), 'Add directions (Paikka)')
        else:
            add_claim_with_sources('P2795', WbMonolingualText(entry['paikka'], 'fi'), 'Add directions (Paikka)')
    else:
        add_claim_with_sources('P2795', WbMonolingualText(entry['paikka'], 'fi'), 'Add directions (Paikka)')

    # P969 Street address
    if entry.get('address'):
        add_claim_with_sources('P6375', WbMonolingualText(entry['address'], 'fi'), 'Add street address')

    # P170 Creator
    if entry.get('tekijä_wikidata'):
        add_claim_with_sources('P170', pywikibot.ItemPage(repo, entry['tekijä_wikidata']), 'Add creator')
    # P571 Inception year
    if re.match(r'^\d{4}$', (yr := entry.get('paljastusvuosi','').strip())):
        add_claim_with_sources('P571', WbTime(year=int(yr)), 'Add inception year')
    # P625 Coordinates
    if entry.get('latitude') and entry.get('longitude'):
        lat, lon = float(entry['latitude']), float(entry['longitude'])
        add_claim_with_sources('P625', Coordinate(lat, lon, precision=0.0001), 'Add coordinates')
    # P18 Free image
    if entry.get('free_image'):
        add_claim_with_sources('P18', entry['free_image'], 'Add free image')
    # P5008 Focus list
    list_page = pywikibot.Page(site, SOURCE_PAGE_TITLE)
    list_item = pywikibot.ItemPage.fromPage(list_page)
    add_claim_with_sources('P5008', list_item, 'Add source page to focus list (P5008)')

    return item.id


def main():
    # Load list page and get latest revision
    page = pywikibot.Page(site, SOURCE_PAGE_TITLE)
    page.get()

    # Build import URL
    global IMPORT_URL
    IMPORT_URL = (
        f"https://{site.hostname()}/w/index.php?"
        f"title={page.title(as_url=True)}&oldid={page.latest_revision_id}"
    )

    text = page.text

    # Extract sortable wikitable
    m = re.search(r'(\{\| class="wikitable sortable".*?\n\|\})', text, re.S)
    if not m:
        raise RuntimeError('Sortable wikitable not found.')
    table_wikitext = m.group(1)

    # Split rows for update
    raw_rows = re.split(r'(?<=\n)(?=\|\-)', table_wikitext)
    rows = re.findall(r'\|\-(.*?)(?=\n\|-|\|\})', table_wikitext, re.S)

    # Helper to clean out wikicode and references
    def clean_text(cell):
        no_ref = re.sub(r'<ref[^>]*>.*?</ref>', '', cell, flags=re.S)
        no_ref = re.sub(r'<ref[^>]*/>', '', no_ref)
        return mwparserfromhell.parse(no_ref).strip_code().strip()

    entries = []
    for row in rows:
        cells = re.split(r'\n\|', row.strip())
        cells = [c[1:] if c.startswith('|') else c for c in cells]
        while len(cells) < 8:
            cells.append('')
        teos_cell, paikka_cell, alue_cell, kartalla_cell, tekija_cell, palj_cell, img_cell, wd_cell = cells[:8]

        m2 = re.search(r'\{\{paikkalinkki\|([^|]+)\|([^|]+)[^}]*\|nimi=([^}]+)\}\}', kartalla_cell)
        lat, lon, kartta_nimi = (m2.group(1), m2.group(2), m2.group(3)) if m2 else ('','','')

        clean_name = clean_text(teos_cell)
        verified_name = clean_name if clean_name == kartta_nimi else ''

        full_paikka = clean_text(paikka_cell)
        if ',' in full_paikka:
            location_desc, address = [p.strip() for p in full_paikka.split(',', 1)]
        else:
            location_desc, address = full_paikka, ''

        # Artist parsing
        wikicode = mwparserfromhell.parse(tekija_cell)
        artist_name = artist_page = ''
        for tpl in wikicode.filter_templates():
            if tpl.name.matches('LajiteltavaNimi'):
                p = tpl.params
                artist_name = f"{p[0].value.strip()} {p[1].value.strip()}".strip()
                artist_page = (p[4].value.strip() if len(p)>=5 and p[4].value.strip()
                               else tpl.get('linkki').value.strip() if tpl.has('linkki') else artist_name)
                break

        artist_wd = ''
        if artist_page:
            try:
                artist_wd = pywikibot.ItemPage.fromPage(pywikibot.Page(site, artist_page)).id
            except Exception:
                pass

        free_image = ''
        m_img = re.search(r'\[\[Tiedosto:([^|\]]+)', img_cell)
        if m_img and pywikibot.FilePage(repo, m_img.group(1).strip()).exists():
            free_image = m_img.group(1).strip()

        m_wd2 = re.search(r'\{\{wikidata-logo\|\s*(Q\d+)', wd_cell)
        artwork_q = m_wd2.group(1).strip() if m_wd2 else ''

        entries.append({
            'latitude': lat,
            'longitude': lon,
            'paljastusvuosi': palj_cell.strip(),
            'teos_nimi': clean_name,
            'varmistettu_nimi': verified_name,
            'paikkalinkki_nimi': kartta_nimi,
            'paikka': location_desc,
            'address': address,
            'alue': alue_cell.strip(),
            'tekijä': artist_name,
            'tekijä_sivu': artist_page,
            'tekijä_wikidata': artist_wd,
            'free_image': free_image,
            'wikidata': artwork_q,
        })

    # Inject and update table
    for entry in entries:
        if not entry['wikidata']:
            new_q = create_wikidata_item(entry)
            entry['wikidata'] = new_q

            for i, row_wikitext in enumerate(raw_rows):
                if entry['teos_nimi'] in row_wikitext:
                    parts = row_wikitext.split('\n|')
                    parts[-1] = f' {{{{wikidata-logo| {new_q}}}}}\n'
                    raw_rows[i] = parts[0] + ''.join(f"\n|{c}" for c in parts[1:])
                    break

            if prompt("Continue with the next artwork? (y/n):").strip().lower() != 'y':
                print("Exiting update loop.")
                break

    # Save updated table
    new_table = ''.join(raw_rows)
    page.text = text.replace(table_wikitext, new_table)
    page.save(summary='Update Wikidata identifiers, sources, and addresses in list')

    # Output JSON for inspection
    print(json.dumps(entries, ensure_ascii=False, indent=2))
    print("end")


if __name__ == '__main__':
    main()








