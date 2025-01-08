import pywikibot
import mwparserfromhell
from typing import List, Dict
import re

def clean_text(text: str) -> str:
    """Remove wiki markup and clean the text."""
    # Remove HTML tags
    text = re.sub('<.*?>', '', text)
    # Remove non-breaking spaces
    text = text.replace('&nbsp;', ' ')
    # Remove multiple spaces
    text = ' '.join(text.split())
    return text.strip()

def parse_reference(ref_text: str) -> str:
    """Extract useful information from reference tags."""
    wikicode = mwparserfromhell.parse(ref_text)
    for template in wikicode.filter_templates():
        if template.name.matches('Verkkoviite'):
            try:
                return f"URL: {template.get('Osoite').value.strip()}"
            except:
                return "Reference found but unable to parse URL"
    return ref_text

def parse_name_cell(cell_contents: str) -> (str, str):
    """
    Parse the name cell to extract:
      - label: The visible text of the cell
      - article: The target of the wikilink, if it exists
    """
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()
    
    article = None
    label = None
    
    if links:
        # Take the first wikilink if multiple exist
        link = links[0]
        article = link.title.strip()
        # If there's custom text in [[Link|Text]], use it as label; otherwise use link.title
        label = link.text.strip() if link.text else link.title.strip()
    else:
        # No wikilinks, just clean the text
        label = clean_text(cell_contents)
    
    return label, article

def parse_image_cell(cell_contents: str) -> str:
    """
    Parse the image cell to extract the image file name.
    Looks for links that begin with 'File:' or 'Tiedosto:' and returns just the filename.
    Example: [[File:SomeImage.jpg|thumb|...]] -> 'SomeImage.jpg'
    """
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()
    
    for link in links:
        title_lower = link.title.strip().lower()
        if title_lower.startswith("file:") or title_lower.startswith("tiedosto:"):
            # e.g., "Tiedosto:SomeImage.jpg|thumb|..."
            #  1) remove "Tiedosto:" prefix
            #  2) split on "|" 
            #  3) the first part is the filename
            parts_after_colon = link.title.split(":", 1)[1]
            file_name = parts_after_colon.split("|")[0].strip()
            return file_name
    
    return None

def parse_location_cell(cell_contents: str) -> Dict[str, str]:
    """
    Parse the location cell to extract:
      - identifier: any text outside of {{paikkalinkki}}
      - lat, lon, geohack_name from within {{paikkalinkki|...}}
    """
    wikicode = mwparserfromhell.parse(cell_contents)
    location_data = {
        "identifier": None,
        "lat": None,
        "lon": None,
        "geohack_name": None
    }
    
    # Collect any plain text outside the paikkalinkki template
    outside_text_parts = []
    for node in wikicode.nodes:
        if node.__class__.__name__ == "Text":
            outside_text_parts.append(str(node).strip())
    outside_text = " ".join(t for t in outside_text_parts if t).strip()
    outside_text = outside_text.rstrip(",")
    
    if outside_text:
        location_data["identifier"] = clean_text(outside_text)

    # Find the paikkalinkki template, if any
    paikkalinkki_template = None
    for template in wikicode.filter_templates():
        if template.name.matches("paikkalinkki"):
            paikkalinkki_template = template
            break

    # Extract lat, lon, geohack_name
    if paikkalinkki_template:
        if paikkalinkki_template.has(1):
            location_data["lat"] = str(paikkalinkki_template.get(1).value.strip())
        if paikkalinkki_template.has(2):
            location_data["lon"] = str(paikkalinkki_template.get(2).value.strip())
        if paikkalinkki_template.has("nimi"):
            location_data["geohack_name"] = str(paikkalinkki_template.get("nimi").value.strip())

    return location_data

def parse_designer_cell(cell_contents: str) -> (str, str):
    """
    Parse the designer cell:
      - designer_name: the visible text
      - designer_link: the wikilink (if present)
    """
    wikicode = mwparserfromhell.parse(cell_contents)
    links = wikicode.filter_wikilinks()
    
    designer_name = None
    designer_link = None

    if links:
        link = links[0]
        designer_link = link.title.strip()
        # if there's custom link text (e.g. [[Name|Text]]), prefer that
        designer_name = link.text.strip() if link.text else link.title.strip()
    else:
        designer_name = clean_text(cell_contents)
    
    return designer_name, designer_link

def parse_am_cell(cell_contents: str) -> Dict[str, str]:
    """
    Parse the 'AM' cell containing something like:
      [[Tiedosto:Commons-logo.svg|30px|link=:Commons:Category:Kuninkaanportti]]<br>
      [[Tiedosto:Wikidata-logo.svg|30px|link=:d:Q5495335]]
    We'll extract:
      - am_commons: the link (if "link=:Commons:Category:...") 
      - am_wikidata: the link (if "link=:d:Q...")
    Returns a dict:
      {
        "am_commons": ":Commons:Category:Kuninkaanportti",
        "am_wikidata": ":d:Q5495335"
      }
    """
    wikicode = mwparserfromhell.parse(cell_contents)
    am_data = {
        "am_commons": None,
        "am_wikidata": None
    }
    
    # Look for image wikilinks:
    # e.g. [[Tiedosto:Commons-logo.svg|30px|link=:Commons:Category:Kuninkaanportti]]
    links = wikicode.filter_wikilinks()
    for link in links:
        # link.title might be: "Tiedosto:Commons-logo.svg|30px|link=:Commons:Category:Kuninkaanportti"
        parts = link.title.split("|")
        
        # We want the piece that starts with "link="
        for part in parts:
            part = part.strip()
            if part.startswith("link="):
                link_value = part.replace("link=", "").strip()
                # Check if it's a Commons or Wikidata link
                if link_value.lower().startswith(":commons:"):
                    am_data["am_commons"] = link_value
                elif link_value.lower().startswith(":d:"):
                    am_data["am_wikidata"] = link_value
    
    return am_data

def parse_suomenlinna_table() -> List[Dict]:
    """Parse the Suomenlinna buildings table from Wikipedia."""
    # Initialize pywikibot
    site = pywikibot.Site('fi', 'wikipedia')
    page = pywikibot.Page(site, 'Luettelo Suomenlinnan rakennuksista')
    
    # Get the page content
    wikicode = mwparserfromhell.parse(page.text)
    
    # Find all tables
    tables = wikicode.filter_tags(matches=lambda node: node.tag == 'table')
    
    buildings = []
    
    for table in tables:
        if 'wikitable sortable' in str(table.attributes):
            rows = table.contents.filter_tags(matches=lambda node: node.tag == 'tr')
            
            # Skip the header row
            for row in list(rows)[1:]:
                cells = row.contents.filter_tags(matches=lambda node: node.tag == 'td')
                if cells:
                    # Convert cells to list for easier access
                    cell_list = list(cells)
                    
                    # Example table structure might have 8 columns now:
                    #   0: Name
                    #   1: Image
                    #   2: Location
                    #   3: Built
                    #   4: Designer
                    #   5: Info
                    #   6: Reference
                    #   7: AM (the new column)
                    if len(cell_list) < 8:
                        # Not enough cells, skip
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
                    
                    # (7) Reference
                    building['reference'] = parse_reference(str(cell_list[6].contents))
                    
                    # (8) AM column
                    building['am']=str(cell_list[7].contents)
                    #building['am_commons'] = am_data.get('am_commons')
                    #building['am_wikidata'] = am_data.get('am_wikidata')
                    
                    buildings.append(building)
    
    return buildings

def main():
    try:
        buildings = parse_suomenlinna_table()
        
        # Print the parsed data
        for building in buildings:
            print("\nBuilding Details:")
            print("-" * 50)
            for key, value in building.items():
                print(f"{key.capitalize()}: {value}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

