#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMP.CS.100 ohjelmointi 1 : johdatus ohjelmointiin
tekijä: Mika Virtanen
opiskelijanumero: tuni.fi: 152475826
sähköposti: mika.p.virtanen@tuni.fi
tehtävä: Kustaanmiekan linnoituksen rakennustunnukset.py
wikipedia: Wikimedia Suomi ry. 12.3.2025 MV
Ohjelman käyttäjä tarvitsee käyttäjätunnuksen myös wikidata-tietokantaan.
"""

import pywikibot
from pywikibot.data.sparql import SparqlQuery
import math
import csv
from pyproj import Transformer

def tallenna_helsingin_rakennustunnus(muuttuja1, muuttuja2):
    """
    Tarkistaa, onko Wikidatassa jo arvo P8355 (Helsingin rakennustunnus).
    Ellei ole, kysyy halutaanko lisätä. Jos on, varoittaa, mikäli arvo poikkeaa
    uudesta, ja kysyy halutaanko arvo korvata.
    """

    # Alustetaan yhteys Wikidataan
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # Poimitaan Q-id muuttuja1-datasta
    item_url = muuttuja1.get('item')
    if not item_url:
        print("Virhe: muuttuja1['item'] puuttuu.")
        return
    # else:
    #    print("muuttuja1.get('item') on  ", item_url)

    item_id = item_url.split('/')[-1]  # esim. 'Q131519923'
    item_page = pywikibot.ItemPage(repo, item_id)

    # Haetaan nykyinen itemin sisältö
    item_page.get()
    # print("Itemin sisältö: ", item_page.get())

    # Poimitaan lisättävä arvo muuttuja2-datasta
    helsingin_rakennustunnus = muuttuja2.get('helsingin_rakennustunnus')
    vtj_prt = muuttuja2.get('vtj_prt')       # oletetaan molempien olevan olemassa jos toinen on
    if not helsingin_rakennustunnus:
        print("Virhe: muuttuja2['helsingin_rakennustunnus'] puuttuu tai on tyhjä.")
        return

    # Katsotaan, onko P8355-ominaisuudesta jo claimia
    claims = item_page.claims.get('P8355', [])

    if not claims:
        # Jos ominaisuutta ei ole lisätty
        print(f"Wikidatassa ei ole vielä Helsingin rakennustunnusta (P8355). ")
        print(f"Uusi arvo olisi: {helsingin_rakennustunnus}")
        vahvistus = input("Tallennetaanko uusi arvo (K/E)? ").strip().lower()
        if vahvistus == 'k':
            claim = pywikibot.Claim(repo, 'P8355')
            claim.setTarget(helsingin_rakennustunnus)

            # Lisätään myös lähde: 'Helsingin pysyvä rakennustunnus RATU {helsingin_rakennustunnus}
            # Malliteksti: P143 = Q175482 tuotu Wikimedia-projektista    suomenkielinen Wikipedia
            # Wikimedia-tuonnin URL (P4656)
            # RATU: P8355 = esim.nro 12345 helsingin_rakennustunnus
            source_claim_P8355 = pywikibot.Claim(repo, 'P8355')
            source_claim_P8355.setTarget(helsingin_rakennustunnus)

            # Lisätään referenssit claimiin
            claim.addSources([source_claim_P8355])

            item_page.addClaim(claim, summary="Lisätään Helsingin rakennustunnus (P8355).")
            print("Arvo tallennettu.")

            # Lähtökohtana on että kun kohteella on RATU niin silloin sillä on myös toinenkin rakennustunnus.
            # pysyvä rakennustunnus VTJ-PRT: P3824
            # 'vtj_prt'
            source_claim_P8355 = pywikibot.Claim(repo, 'P8355')
            source_claim_P8355.setTarget(helsingin_rakennustunnus)

            claim = pywikibot.Claim(repo, 'P3824')
            claim.setTarget(vtj_prt)

            # Lisätään referenssit claimiin
            claim.addSources([source_claim_P8355])

            item_page.addClaim(claim, summary="Lisätään pysyvä rakennustunnus VTJ-PRT (P3824).")
            print("Arvo tallennettu VTJ-PRT.")

        else:
            print("Tallennus peruutettu.")
    else:
        # Ominaisuus on jo olemassa, verrataan arvoja
        nykyinen_arvo = claims[0].getTarget()
        if nykyinen_arvo == helsingin_rakennustunnus:
            print(f"Helsingin rakennustunnus (P8355) on jo asetettu arvoon {nykyinen_arvo}.")
            print("Ei muutoksia.")
        else:
            print("VAROITUS: Wikidatassa on jo arvo "
                  f"{nykyinen_arvo} Helsingin rakennustunnukselle (P8355).")
            print(f"Uusi arvo olisi: {helsingin_rakennustunnus}")
            vahvistus = input("Korvataanko vanha arvo uudella (K/E)? ").strip().lower()
            if vahvistus == 'k':
                claims[0].changeTarget(helsingin_rakennustunnus,
                                       summary="Päivitetään Helsingin rakennustunnus (P8355).")
                print("Arvo päivitetty.")
            else:
                print("Päivitys peruutettu.")

def lue_csv_dict_ja_nayta_sisalto_lisatty_wgs84(tiedoston_nimi, results):
    # Luo koordinaattimuunnin ETRS-GK25FIN (EPSG:3879) -> WGS84 (EPSG:4326)
    transformer = Transformer.from_crs("EPSG:3879", "EPSG:4326", always_xy=True)

    with open(tiedoston_nimi, 'r', encoding='utf-8') as csv_tiedosto:
        # tsv   csv_dictlukija = csv.DictReader(csv_tiedosto, delimiter='\t')
        csv_dictlukija = csv.DictReader(csv_tiedosto, delimiter=';')
        # Tulostetaan ensin otsikkorivit + lisätyt WGS84-sarakkeet
        # (DictReader-olio ei itsessään tallenna otsikoita listana,
        #  mutta voimme muodostaa sen csv_dictlukija.fieldnames:stä)
        alkuperaiset_otsikot = csv_dictlukija.fieldnames
        if alkuperaiset_otsikot is not None:
            # Lisätään uudet sarakeotsikot
            uudet_otsikot = alkuperaiset_otsikot + ['lat_wgs84', 'lon_wgs84']
            print("\t".join(uudet_otsikot))

        for rivi in csv_dictlukija:
            # if 1:
            #    print(rivi)
            #    exit(1)
            # Poimitaan pohjois- ja itäkoordinaatit (koordinaatti_p, koordinaatti_i)
            # ja yritetään muuntaa ne liukuluvuiksi.
            try:
                p = float(rivi['koordinaatti_p'])  # Pohjoinen
                i = float(rivi['koordinaatti_i'])  # Itä
            except (ValueError, TypeError):
                # Jos ei voida muuntaa, oletetaan ettei dataa ole (tai on virheellistä)
                p, i = None, None

            if p is not None and i is not None:
                # Huom! always_xy=True tarkoittaa (x, y) = (longitude, latitude).
                # Mutta ETRS-GK25:ssä "i" = easting (x) ja "p" = northing (y).
                # Siksi välitämme parametreina (i, p).
                lat, lon = transformer.transform(i, p)

                # Tallennetaan tulos
                rivi['lat_wgs84'] = f"{lat:.6f}"
                rivi['lon_wgs84'] = f"{lon:.6f}"
            else:
                rivi['lat_wgs84'] = ""
                rivi['lon_wgs84'] = ""

            # Tulostetaan rivi mukaanlukien uudet sarakkeet
            # Poimitaan rivin arvot alkuperäisten otsikoiden mukaisessa järjestyksessä
            arvot_listana = [rivi[ots] if ots in rivi and rivi[ots] is not None else ""
                             for ots in alkuperaiset_otsikot]

            # Lisätään WGS84-lisäsarakkeet rivin loppuun
            arvot_listana.append(rivi['lon_wgs84'])
            arvot_listana.append(rivi['lat_wgs84'])
            # arvot_listana.append(rivi['lon_wgs84'])

            # Kutsutaan tarkistusfunktiota
            found_building = is_building_in_list(
                results,
                target_address=rivi['osoite_suomeksi'],
                target_lat=lon,
                target_lon=lat,
                max_distance=10
            )
            # print(f"#{rivi['osoite_suomeksi']}#")
            if found_building:
                print(found_building)
                print(rivi)
                # print("\t".join(arvot_listana))
                tallenna_helsingin_rakennustunnus(found_building, rivi)
                # exit(1)

def parse_wikidata_coord(coord_literal: str):
    pass
    """
    Parsii Wikidatasta saadun WKT-muotoisen koordinaatin (Point(lon lat))
    ja palauttaa (lat, lon) float-arvoina.
    Esimerkki: "Point(24.9384 60.1699)" -> (60.1699, 24.9384)
    """
    # Poistetaan alku ja loppu: "Point(" ja ")"
    # Oletusmuodossa: Point(lon lat)
    coords_str = coord_literal.strip("Point()")
    lon_str, lat_str = coords_str.split()

    lon = float(lon_str)
    lat = float(lat_str)
    return (lat, lon)

def haversine_distance(lat1, lon1, lat2, lon2):
    pass
    """
    Palauttaa etäisyyden metreissä kahden pisteen (lat1, lon1) ja (lat2, lon2) välillä
    Haversine-kaavaa käyttäen.
    """
    R = 6371_000  # Maan säde metreissä, likimäärin
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def is_building_in_list(results, target_address, target_lat, target_lon, max_distance=20):
    pass
    """
    Tarkistaa, löytyykö results-listasta item, jolla on:
      1) sama osoite target_address
      2) koordinaatti alle max_distance metrin päässä (target_lat, target_lon)
    Palauttaa True, jos sopiva item löytyy, muuten False tai palauttaa tuloslaskurin,
    kuinka monta löytyi.
    """
    tuloslaskuri = 0
    for row in results:
        osoite = row.get("osoite")
        coords_literal = row.get("coords")

        # Jos osoite puuttuu tai koordinaatit puuttuvat, hypätään yli
        if not osoite or not coords_literal:
            continue

        # Tarkistetaan osoite
        if osoite == target_address:
            # Parsitaan lat/lon
            try:
                lat, lon = parse_wikidata_coord(coords_literal)
            except (ValueError, AttributeError):
                continue  # Jos jotain ongelmaa, jatketaan seuraavaan

            # Lasketaan etäisyys metreissä
            distance = haversine_distance(target_lat, target_lon, lat, lon)
            if distance <= max_distance:
                tuloslaskuri += 1
                print(f"{tuloslaskuri}.    osoite: {osoite}")
                # return True
                currentrow = row

    if tuloslaskuri == 1:
        return currentrow
    else:
        return False

def sparqlhaku():
    # Määritellään haettava SPARQL-kysely
    # tietokanta Susisaari (Q16928377)
    # tietokanta Kustaanmiekka (Q5399296)
    query = """
    SELECT DISTINCT ?place_fi ?coords ?item ?label_fi ?osoite ?kuva ?ratu ?vtjprt ?description_fi ?label_en 
    WHERE
    {
      VALUES ?place { wd:Q5399296 }
      ?item wdt:P17 wd:Q33 .
      ?item (wdt:P131|wdt:P706|wdt:P361|wdt:P276) ?place .
      ?item rdfs:label ?label_fi .

      FILTER (lang(?label_fi) = "fi")
      OPTIONAL { ?place rdfs:label ?place_fi . FILTER (lang(?place_fi) = "fi") }  
      OPTIONAL { ?item rdfs:label ?label_en . FILTER (lang(?label_en) = "en") }
      OPTIONAL { ?item schema:description ?description_fi FILTER (lang(?description_fi) = "fi") }
      OPTIONAL { ?item schema:description ?description_en FILTER (lang(?description_fi) = "en") }                 
      OPTIONAL { ?item wdt:P625 ?coords }
      OPTIONAL { ?item wdt:P6375 ?osoite }
      OPTIONAL { ?item wdt:P18 ?kuva }
      OPTIONAL { ?item wdt:P8355 ?ratu }
      OPTIONAL { ?item wdt:P3824 ?vtjprt }
    }
    """

    # Luodaan SPARQL-olio
    sq = SparqlQuery()

    # Suoritetaan kysely
    results = sq.select(query)

    return results


def main():
    pass

    results = sparqlhaku()
    # Esimerkki: Tarkistetaan, löytyykö listasta osoite "Esimerkkikatu 1" lähellä (60.1699, 24.9384)
    test_address = "Suomenlinna B 1"     # Suomenlinna B 1
    test_lat = 60.1447                 # 60.144738, 24.986561
    test_lon = 24.9865                #
    max_dist = 20 # 20 metriä

    # Kutsutaan tarkistusfunktiota
    found_building = is_building_in_list(
        results,
        target_address=test_address,
        target_lat=test_lat,
        target_lon=test_lon,
        max_distance=max_dist
    )

    if found_building:
        print(
            f"Osoitteella '{test_address}' löytyi rakennus, joka on alle {max_dist} m etäisyydellä annetusta pisteestä.")
    else:
        print(
            f"Osoitteella '{test_address}' ei löytynyt rakennusta alle {max_dist} m etäisyydellä annetusta pisteestä.")

    # Voit halutessasi myös tulostaa kaikki tulokset
    # (kommentoi pois, jos listan tulostus ei ole tarpeen)
    """
    for row in results:
        place_fi = row.get("place_fi", "")
        coords = row.get("coords", "")
        item = row.get("item", "")
        label_fi = row.get("label_fi", "")
        osoite = row.get("osoite", "")
        kuva = row.get("kuva", "")
        ratu = row.get("ratu", "")
        vtjprt = row.get("vtjprt", "")
        description_fi = row.get("description_fi", "")
        label_en = row.get("label_en", "")

        print("-----")
        print(f"place_fi: {place_fi}")
        print(f"coords: {coords}")
        print(f"item: {item}")
        print(f"label_fi: {label_fi}")
        print(f"osoite: {osoite}")
        print(f"kuva: {kuva}")
        print(f"ratu: {ratu}")
        print(f"vtjprt: {vtjprt}")
        print(f"description_fi: {description_fi}")
        print(f"label_en: {label_en}")
    """


if __name__ == "__main__":
    results = sparqlhaku()
    # tiedosto = "Datatabletsv.tsv"         # Datatabletsv.tsv
    tiedosto = "datatable.csv"
    lue_csv_dict_ja_nayta_sisalto_lisatty_wgs84(tiedosto, results)
    # main()

    # funktiolista
    # def lue_csv_dict_ja_nayta_sisalto_lisatty_wgs84(tiedoston_nimi):
    # def parse_wikidata_coord(coord_literal: str):
    # def haversine_distance(lat1, lon1, lat2, lon2):
    # def is_building_in_list(results, target_address, target_lat, target_lon, max_distance=20):
    # def sparqlhaku():
    # def main():
