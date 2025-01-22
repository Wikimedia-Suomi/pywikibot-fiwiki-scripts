#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pywikibot
from pywikibot.data.sparql import SparqlQuery
import math


def parse_wikidata_coord(coord_literal: str):
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
    return tuloslaskuri


def main():
    # Määritellään haettava SPARQL-kysely
    query = """
    SELECT DISTINCT ?place_fi ?coords ?item ?label_fi ?osoite ?kuva ?ratu ?vtjprt ?description_fi ?label_en 
    WHERE
    {
      VALUES ?place { wd:Q16928377 }
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
    main()
