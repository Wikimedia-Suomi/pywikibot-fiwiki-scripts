import csv
from pyproj import Transformer


def lue_csv_dict_ja_nayta_sisalto_lisatty_wgs84(tiedoston_nimi):
    # Luo koordinaattimuunnin ETRS-GK25FIN (EPSG:3879) -> WGS84 (EPSG:4326)
    transformer = Transformer.from_crs("EPSG:3879", "EPSG:4326", always_xy=True)

    with open(tiedoston_nimi, 'r', encoding='utf-8') as csv_tiedosto:
        csv_dictlukija = csv.DictReader(csv_tiedosto, delimiter='\t')

        # Tulostetaan ensin otsikkorivit + lisätyt WGS84-sarakkeet
        # (DictReader-olio ei itsessään tallenna otsikoita listana,
        #  mutta voimme muodostaa sen csv_dictlukija.fieldnames:stä)
        alkuperaiset_otsikot = csv_dictlukija.fieldnames
        if alkuperaiset_otsikot is not None:
            # Lisätään uudet sarakeotsikot
            uudet_otsikot = alkuperaiset_otsikot + ['lat_wgs84', 'lon_wgs84']
            print("\t".join(uudet_otsikot))

        for rivi in csv_dictlukija:
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

            print("\t".join(arvot_listana))


if __name__ == "__main__":
    tiedosto = "Datatabletsv.tsv"         # Datatabletsv.tsv
    lue_csv_dict_ja_nayta_sisalto_lisatty_wgs84(tiedosto)
