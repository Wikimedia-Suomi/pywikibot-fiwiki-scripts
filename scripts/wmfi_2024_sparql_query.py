"""
COMP.CS.100 ohjelmointi 1 : johdatus ohjelmointiin
tekijä: Mika Virtanen, ohjelmoijatunnus aurorakiitäjä
ohjaaja: zache, wikimedia Suomi ry
opiskelijanumero: tuni.fi: 152475826
sähköposti: mika.p.virtanen@tuni.fi
tehtävä: harjoitus_sparql_query.py, wmfi_2024_sparql_query.py
         toisto eri tietokoneessa (ms windows)
         ohjelmadokumentaatio suomeksi
         päivitystehtävä ominaisuus P2186 eli RKY museoaluekartta Suomi
"""

# -*- coding: utf-8 -*-
import pywikibot
from pywikibot import pagegenerators
import sys

"""
Iteroi SPARQL-kyselyn kautta saadut kohteet ja päivittää tarvittaessa.
"""

QUERY = """
SELECT ?item
WHERE
{
  ?item wdt:P4009 ?RKY.
  FILTER NOT EXISTS { ?item wdt:P2186 ?value. }
}
ORDER BY ?item
LIMIT 33


"""

def main():
    # Ohjelman suorittamat käskyt tästä alkavat tästä
    print("uusi ohjelma wmfi_2024_sparql_query.py")
    print("sivusto on pywikibot.Site ja yritetään tehdä site.login()")
    print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - -")

    # Määritetään sivusto ja tallennetaan data-repository
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # Kirjaudutaan sisään
    site.login()

    generator = pagegenerators.PreloadingEntityGenerator(
        pagegenerators.WikidataSPARQLPageGenerator(QUERY, site=repo)
    )

    for item in generator:
        if 'fi' in item.labels:
            label = item.labels['fi']
        else:
            label = item.labels.get('en', '')

        # Tarkistetaan, onko kohteella P4009-ominaisuutta
        if 'P4009' in item.claims:
            claims = item.claims['P4009']
            # Jos P4009-arvoja on useita, keskeytetään ohjelma
            if len(claims) > 1:
                print(
                    f"{label}: Useita P4009-arvoja löydetty, ohjelma keskeytetään.")
                sys.exit()
            else:
                # Haetaan P4009-arvo
                p4009_value = claims[0].getTarget()
                p4009_value_str = str(p4009_value)
                print(f"{label}: P4009 = {p4009_value_str}")
        else:
            print(f"{label}: P4009 ei löydy")
            continue  # Siirrytään seuraavaan kohteeseen

        # Tarkistetaan, onko kohteella jo P2186-ominaisuutta
        if 'P2186' in item.claims:
            print(f"{label}: P2186 on jo olemassa")
        else:
            # Kysytään vahvistus ennen muokkaamista
            confirm = input(
                f"Haluatko lisätä P2186-ominaisuuden kohteeseen '{label}'? (k/e): ").lower()
            if confirm == 'k':
                # Luodaan uusi P2186-ominaisuus arvolla "P4009/$P4009"
                new_value = f"P4009/{p4009_value_str}"
                claim = pywikibot.Claim(repo,
                                        'P2186')  # Luodaan uusi claim P2186:lle
                claim.setTarget(new_value)

                # Lisätään claim kohteeseen
                item.addClaim(claim, summary='Lisätään P2186-ominaisuus')

                # Lisätään lähdeviite: P4009=$P4009
                ref_claim = pywikibot.Claim(repo,
                                            'P4009')  # Luodaan lähdeviitteen claim
                ref_claim.setTarget(p4009_value)

                # Luodaan lähdeviite
                source = [ref_claim]
                claim.addSources(source,
                                 summary='Lisätään lähdeviite P2186-ominaisuudelle')

                print(f"{label}: Lisätty P2186 arvolla {new_value}")
            else:
                print(f"{label}: Muokkausta ei tehty.")

    print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")
    # ohjelmaa on käytetty git bashissa
    # Asenna pip-paketit ja tee user-config.py
    # $ pip install pywikibot		<enter>

if __name__ == "__main__":
    main()
