import pywikibot
import mwparserfromhell
from typing import List, Dict
import re
import requests
import urllib.parse

from difflib import SequenceMatcher  # standard library fuzzy approach

from pywikibot import WbMonolingualText

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


def clean_text(text: str) -> str:
    """Remove HTML tags, excessive spaces, etc."""
    text = re.sub('<.*?>', '', text)
    text = text.replace('&nbsp;', ' ')
    text = ' '.join(text.split())
    return text.strip()


def parse_plaintext_cell(cell_contents: str) -> str:
    wikicode = mwparserfromhell.parse(cell_contents)
    plaintext = wikicode.strip_code()
    return clean_text(plaintext)


def parse_reference(ref_text: str) -> str:
    wikicode = mwparserfromhell.parse(ref_text)
    for template in wikicode.filter_templates():
        if template.name.matches('Verkkoviite'):
            try:
                return f"URL: {template.get('Osoite').value.strip()}"
            except:
                return "Reference found but unable to parse URL"
    return ref_text


def parse_name_cell(cell_contents: str) -> (str, str):
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()

    article = None
    label = None

    if links:
        link = links[0]
        article = link.title.strip()
        label = link.text.strip() if link.text else link.title.strip()
    else:
        label = clean_text(cell_contents)

    return label, article


def parse_country_cell(cell_contents: str) -> (str, str):
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()

    article = None
    label = None

    if links:
        link = links[0]
        article = link.title.strip()
        label = link.text.strip() if link.text else link.title.strip()
    else:
        label = clean_text(cell_contents)

    return label, article


def parse_image_cell(cell_contents: str) -> str:
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()

    for link in links:
        title_lower = link.title.strip().lower()
        if title_lower.startswith("file:") or title_lower.startswith("tiedosto:"):
            parts_after_colon = link.title.split(":", 1)[1]
            file_name = parts_after_colon.split("|")[0].strip()
            return file_name
    return None


def parse_location_cell(cell_contents: str) -> Dict[str, str]:
    wikicode = mwparserfromhell.parse(cell_contents)
    location_data = {
        "identifier": None,
        "lat": None,
        "lon": None,
        "geohack_name": None
    }

    outside_text_parts = []
    for node in wikicode.nodes:
        if node.__class__.__name__ == "Text":
            outside_text_parts.append(str(node).strip())
    outside_text = " ".join(t for t in outside_text_parts if t).strip()
    outside_text = outside_text.rstrip(",")

    if outside_text:
        location_data["identifier"] = clean_text(outside_text)

    paikkalinkki_template = None
    for template in wikicode.filter_templates():
        if template.name.matches("paikkalinkki"):
            paikkalinkki_template = template
            break

    if paikkalinkki_template:
        if paikkalinkki_template.has(1):
            location_data["lat"] = str(paikkalinkki_template.get(1).value.strip())
        if paikkalinkki_template.has(2):
            location_data["lon"] = str(paikkalinkki_template.get(2).value.strip())
        if paikkalinkki_template.has("nimi"):
            location_data["geohack_name"] = str(paikkalinkki_template.get("nimi").value.strip())

    return location_data


def parse_designer_cell(cell_contents: str) -> (str, str):
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()

    if links:
        link = links[0]
        designer_link = link.title.strip()
        designer_name = link.text.strip() if link.text else link.title.strip()
    else:
        designer_name = clean_text(cell_contents)
        designer_link = None

    return designer_name, designer_link


def parse_am_cell(cell_contents: str) -> Dict[str, str]:
    wikicode = mwparserfromhell.parse(cell_contents)
    am_data = {
        "am_commons": None,
        "am_wikidata": None
    }

    for link in wikicode.filter_wikilinks():
        link_text = str(link)
        if "Commons:Category:" in link_text:
            am_data['am_commons'] = link_text.split("Commons:Category:")[-1].rstrip("]]")
        elif ":d:Q" in link_text:
            wikidata_id = link_text.split(":d:Q")[-1].rstrip("]]")
            if wikidata_id.isdigit():
                am_data['am_wikidata'] = "Q" + wikidata_id

    return am_data


def string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_nearby_wikidata_items(lat: float, lon: float, radius=1.0, lang='fi') -> List[Dict[str, str]]:
    sparql_query = f"""
SELECT ?place ?placeLabel ?distance
WHERE {{
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],{lang}" }}

  SERVICE wikibase:around {{
    ?place wdt:P625 ?location .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral.
    bd:serviceParam wikibase:radius "{radius}".
    bd:serviceParam wikibase:distance ?distance.
  }}
}}
ORDER BY ?distance
LIMIT 10
    """

    try:
        resp = requests.get(
            SPARQL_ENDPOINT,
            params={"query": sparql_query, "format": "json"},
            headers={"User-Agent": "SuomenlinnaParser/1.0 (https://fi.wikipedia.org/)"}
        )
        data = resp.json()
    except Exception as e:
        print("SPARQL query failed:", e)
        return []

    results = []
    bindings = data.get("results", {}).get("bindings", [])
    for row in bindings:
        item_uri = row.get("place", {}).get("value", "")
        label_val = row.get("placeLabel", {}).get("value", "")
        dist_val = row.get("distance", {}).get("value", "")
        qid = item_uri.split("/")[-1] if "entity/" in item_uri else None

        try:
            dist_float = float(dist_val)
        except ValueError:
            dist_float = None

        results.append({
            "qid": qid,
            "label": label_val,
            "distance": dist_float
        })
    return results


def fuzzy_match_label(target_label: str, candidates: List[Dict[str, str]], threshold=0.8) -> Dict[str, str]:
    best_match = {}
    best_score = 0.0

    for c in candidates:
        sim = string_similarity(target_label, c['label'])
        if sim > best_score:
            best_score = sim
            best_match = c

    if best_score >= threshold:
        return best_match
    else:
        return {}


def create_new_wikidata_item(building: Dict) -> str:
    """
    Creates a new Wikidata item for the given building dictionary.
    Prints all info, asks the user for confirmation, and then
    edits the item with relevant statements.
    """
    print("\nNo Wikidata item found for this building. Here are the details:\n")
    for key, value in building.items():
        print(f"  {key}: {value}")
    confirmation = input("\nCreate a new Wikidata item for this building? [y/N]: ")
    if confirmation.strip().lower() != 'y':
        print("Skipping creation of a new Wikidata item.\n")
        return None

    saari = (building['identifier'][0]) if building['identifier'] else ""
    if saari == "A":
        muuttuja276 = 'Q5399296'
        commons_category_value = 'Kustaanmiekka'
        print('Kustaanmiekka')
    elif saari == "B":
        muuttuja276 = 'Q16928377'
        commons_category_value = 'Susisaari'
        print('Susisaari')
    elif saari == "C":
        muuttuja276 = 'Q11865193'
        commons_category_value = 'Iso Mustasaari'
        print('Iso Mustasaari')
    elif saari == "D":
        muuttuja276 = 'Q11888097'
        commons_category_value = 'Pikku Mustasaari'
        print('Pikku Musta')
    elif saari == "E":
        muuttuja276 = 'Q11880027'
        commons_category_value = 'Länsi Mustasaari'
        print('Länsi Musta')
    else:
        print('tuntematon arvo')
        return None

    if building['am_commons']:
        commons_category_value = building['am_commons']

    monolingual_text_value = WbMonolingualText(text='Suomenlinna ' + building['identifier'], language='fi')
    rakennusvuosi = ""
    if building['built']:
        try:
            rakennusvuosi = int(building['built'])
            print('rakennusvuosi on ', rakennusvuosi)
        except:
            print('Useita vuosilukuja tai tunnistamaton teksti')

    site = pywikibot.Site('wikidata', 'wikidata')
    repo = site.data_repository()

    new_item = pywikibot.ItemPage(repo)
    labels = {"fi": building['label']}
    descriptions = {"fi": "Rakennus Suomenlinnassa"}

    new_item.editEntity({
        'labels': labels,
        'descriptions': descriptions
    })

    new_qid = new_item.title()
    print(f"Created new Wikidata item: {new_qid}")

    # Koordinaatit
    lat_str = building.get('lat')
    lon_str = building.get('lon')
    if lat_str and lon_str:
        try:
            lat_f = float(lat_str.replace(",", "."))
            lon_f = float(lon_str.replace(",", "."))
            coord_claim = pywikibot.Claim(repo, 'P625')  # coordinate location
            coord_target = pywikibot.Coordinate(
                lat_f,
                lon_f,
                precision=0.0001,
                site=repo
            )
            coord_claim.setTarget(coord_target)
            new_item.addClaim(coord_claim)
            print(f"  - Added P625 (coordinate location) to {new_qid}")
        except ValueError:
            pass

    # instance of
    instance_claim = pywikibot.Claim(repo, 'P31')
    instance_target = pywikibot.ItemPage(repo, 'Q811979')  # architectural structure
    instance_claim.setTarget(instance_target)
    new_item.addClaim(instance_claim)
    print(f"  - Added P31 (architectural structure) to {new_qid}")

    # country = Finland
    instance_claim = pywikibot.Claim(repo, 'P17')
    instance_target = pywikibot.ItemPage(repo, 'Q33')
    instance_claim.setTarget(instance_target)
    new_item.addClaim(instance_claim)
    print(f"  - Added P17 (country) to {new_qid}")

    # municipality = Helsinki
    instance_claim = pywikibot.Claim(repo, 'P131')
    instance_target = pywikibot.ItemPage(repo, 'Q1757')
    instance_claim.setTarget(instance_target)
    new_item.addClaim(instance_claim)
    print(f"  - Added P131 (Helsinki) to {new_qid}")

    # location (island)
    instance_claim = pywikibot.Claim(repo, 'P276')
    instance_target = pywikibot.ItemPage(repo, muuttuja276)
    instance_claim.setTarget(instance_target)
    new_item.addClaim(instance_claim)
    print(f"  - Added P276 (location) to {new_qid}")

    # Commons-luokka (P373)
    instance_claim = pywikibot.Claim(repo, 'P373')
    instance_claim.setTarget(commons_category_value)
    new_item.addClaim(instance_claim)
    print(f"  - Added P373 (Commons category) to {new_qid}")

    # katuosoite (P6375)
    instance_claim = pywikibot.Claim(repo, 'P6375')
    address = monolingual_text_value
    instance_claim.setTarget(address)
    new_item.addClaim(instance_claim)
    print(f"  - Added P6375 (Street address) to {new_qid}")

    # image (P18)
    if building['image']:
        instance_claim = pywikibot.Claim(repo, 'P18')
        commonssite = pywikibot.Site('commons')
        imagename = building['image']
        imagelink = pywikibot.Link(imagename, source=commonssite, default_namespace=6)
        image = pywikibot.FilePage(imagelink)
        if image.isRedirectPage():
            image = pywikibot.FilePage(image.getRedirectTarget())
        if not image.exists():
            pywikibot.info(f"{image} doesn't exist so I can't link to it")
        else:
            instance_claim.setTarget(image)
            new_item.addClaim(instance_claim)
            print(f"  - Added P18 (image) to {new_qid}")

    # rakennusvuosi (inception, P571)
    if rakennusvuosi:
        rv = int(rakennusvuosi)
        instance_claim = pywikibot.Claim(repo, 'P571')
        instance_target = pywikibot.WbTime(year=rv, precision=9)
        instance_claim.setTarget(instance_target)
        new_item.addClaim(instance_claim)
        print(f"  - Added P571 (Inception) to {new_qid}")

    return new_qid


def parse_suomenlinna_table() -> List[Dict]:
    site = pywikibot.Site('fi', 'wikipedia')
    page = pywikibot.Page(site, 'Luettelo Suomenlinnan rakennuksista')

    # ### UUTTA: Tallennetaan alkuperäinen teksti diffin näyttämistä varten
    old_text = page.text

    wikicode = mwparserfromhell.parse(page.text)
    tables = wikicode.filter_tags(matches=lambda node: node.tag == 'table')

    buildings = []

    stoppi = 'n'
    for table in tables:
        if stoppi.strip().lower() == 'y':
            break
        if 'wikitable sortable' in str(table.attributes):
            rows = table.contents.filter_tags(matches=lambda node: node.tag == 'tr')

            for row in list(rows)[1:]:
                if stoppi.strip().lower() == 'y':
                    break

                # Muussa tapauksessa oletamme data-rivin
                cells = row.contents.filter_tags(matches=lambda node: node.tag == 'td')
                cell_list = list(cells)

                if len(cell_list) < 8:
                    # Jos sarakkeita ei ole tarpeeksi, ohitetaan
                    continue

                building = {}

                # (1) Name
                label, article = parse_name_cell(str(cell_list[0].contents))
                building['label'] = label
                if article:
                    building['article'] = article

                # (2) Image
                building['image'] = parse_image_cell(str(cell_list[1].contents))

                # (3) Location
                loc_data = parse_location_cell(str(cell_list[2].contents))
                building['identifier'] = loc_data.get('identifier')
                building['lat'] = loc_data.get('lat')
                building['lon'] = loc_data.get('lon')
                building['geohack_name'] = loc_data.get('geohack_name')

                # (4) Built
                building['built'] = clean_text(str(cell_list[3].contents))

                # (5) Designer
                d_name, d_link = parse_designer_cell(str(cell_list[4].contents))
                building['designer_name'] = d_name
                if d_link:
                    building['designer_link'] = d_link

                # (6) Info
                building['info'] = clean_text(str(cell_list[5].contents))
                building['info_plaintext'] = parse_plaintext_cell(str(cell_list[5].contents))

                # (7) Reference
                building['reference'] = parse_reference(str(cell_list[6].contents))

                # (8) AM cell
                am_data = parse_am_cell(str(cell_list[7].contents))
                building['am_commons'] = am_data.get('am_commons')
                building['am_wikidata'] = am_data.get('am_wikidata')

                # Fuzzy search, etsitään mahdollisesti lähellä olevia WD-kohteita
                lat_str = building['lat']
                lon_str = building['lon']
                if lat_str and lon_str:
                    try:
                        lat_f = float(lat_str.replace(",", "."))
                        lon_f = float(lon_str.replace(",", "."))
                    except ValueError:
                        lat_f = None
                        lon_f = None

                    if lat_f is not None and lon_f is not None:
                        candidates = get_nearby_wikidata_items(
                            lat=lat_f,
                            lon=lon_f,
                            radius=1.0,
                            lang='fi'
                        )
                        best_match = fuzzy_match_label(building['label'], candidates, threshold=0.8)

                        if best_match:
                            building['fuzzy_wikidata_qid'] = best_match['qid']
                            building['fuzzy_wikidata_label'] = best_match['label']
                            building['fuzzy_wikidata_distance'] = best_match['distance']
                        else:
                            building['fuzzy_wikidata_qid'] = None
                    else:
                        building['fuzzy_wikidata_qid'] = None
                else:
                    building['fuzzy_wikidata_qid'] = None

                # Luodaan uusi WD-kohde, jos sellaista ei ole lainkaan
                if not building.get('am_wikidata') and not building.get('fuzzy_wikidata_qid'):
                    new_qid = create_new_wikidata_item(building)
                    building['created_wikidata_qid'] = new_qid
                else:
                    building['created_wikidata_qid'] = None

                # Jos loimme uuden Wikidata-kohteen, lisätään se rivin viimeiseen soluun
                if building['created_wikidata_qid']:
                    wikidata_link = f" [[Tiedosto:Wikidata-logo.svg|30px|link=:d:{building['created_wikidata_qid']}]]\n"
                    original_cell_content = str(cell_list[7].contents)
                    new_cell_content = original_cell_content.strip() + wikidata_link
                    cell_list[7].contents = new_cell_content
                    stoppi = input("\nKeskeytetäänkö tähän tallennukseen? [y/N]: ")


                buildings.append(building)



    # ### UUTTA: Luodaan new_text uudesta wikicode-rakenteesta
    new_text = str(wikicode)

    # ### UUTTA: Näytetään diff
    pywikibot.showDiff(old_text, new_text)

    # ### UUTTA: Kysytään tallennusvarmistus
    confirm = input("\nHaluatko tallentaa muutokset? [y/N]: ")
    if confirm.strip().lower() == 'y':
        page.text = new_text
        page.save("Lisätty uusi Wikidata-kohde Suomenlinnan rakennuksien luetteloon")
    else:
        print("Muutoksia ei tallennettu.")

    return buildings


def main():
    try:
        buildings = parse_suomenlinna_table()

        # Print the parsed data
        for b in buildings:
            print("\nBuilding Details:")
            print("-" * 50)
            for k, v in b.items():
                print(f"{k}: {v}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
