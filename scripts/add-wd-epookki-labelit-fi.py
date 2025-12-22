# Purpose: add finnish labels to epochs in wikidata
#
# Running script: python <scriptname>

import pywikibot
import json
from urllib.request import urlopen

#import requests

# todo: force integers as inputs
class SimpleTimestamp:
    def __init__(self):
        self.year = 0
        self.month = 0
        self.day = 0

    def isValidDay(self, iday):
        if (iday < 1 or iday > 31):
            # not a valid day
            return False
        return True

    def isValidMonth(self, imon):
        if (imon < 1 or imon > 12):
            # not a valid month
            return False
        return True

    def isValidYear(self, iyr):
        if (iyr < 1 or iyr > 9999):
            # not a valid year
            return False
        return True
    
    def isValid(self):
        if (self.isValidDay(self.day) == True
            and self.isValidMonth(self.month) == True
            and self.isValidYear(self.year) == True):
            return True
        return False

    def setDate(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

    def zeropaddednum(self, inum, ic):
        if (inum > 9999):
            return ""
        if (inum < 10):
            il = 1
        elif (inum < 100):
            il = 2
        elif (inum < 1000):
            il = 3
        else:
            il = 4
        
        icount = ic-il
        s = ""
        i = 0
        while (i < icount):
            s += "0"
            i = i +1

        s += str(inum)
        return s

    def makeIsodateStr(self):
    # note: needs zero padding for fixed length
    #printf("%4d-%2d-%2d", self.year, self.month, self.day)
    #    str(self.year) + "-" str(self.month) + "-" + str(self.day)
        if (self.isValid() == False):
            return ""
        date = self.zeropaddednum(self.year, 4)
        date += "-"
        date += self.zeropaddednum(self.month, 2)
        date += "-"
        date += self.zeropaddednum(self.day, 2)
        return date

    def isMatchingDate(self, year, month, day):
        if (self.year == year
            and self.month == month
            and self.day == day):
            return True
        return False
    

svmonth = [
    "januari",
    "februari",
    "mars",
    "april",
    "maj",
    "juni",
    "juli",
    "augusti",
    "september",
    "oktober",
    "november",
    "december",
    ]

enmonth = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    ]

frmonth = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juin",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
    ]

fimonth = [
    "tammikuu",
    "helmikuu",
    "maaliskuu",
    "huhtikuu",
    "toukokuu",
    "kesäkuu",
    "heinäkuu",
    "elokuu",
    "syyskuu",
    "lokakuu",
    "marraskuu",
    "joulukuu",
    ]

fimonthcase = [
    "tammikuuta",
    "helmikuuta",
    "maaliskuuta",
    "huhtikuuta",
    "toukokuuta",
    "kesäkuuta",
    "heinäkuuta",
    "elokuuta",
    "syyskuuta",
    "lokakuuta",
    "marraskuuta",
    "joulukuuta",
    ]

def getsubstr(text, begin, end):
    if (end < begin):
        return -1
    return text[begin:end]

def leftstr(text, index):
    return text[:index]

def rightstr(text, index):
    return text[index:]

def leftfrom(text, char):
    index = text.find(char)
    if (index > 0):
        return text[:index]

    return text

# month, day, year
def parse_en_datelabel(label):
    ts = SimpleTimestamp()

    ione = label.find(" ")
    if (ione < 0):
        return ts

    itwo = label.find(" ", ione+1)
    if (itwo < 0):
        return ts

    spp = label.split(" ")
    print("DEBUG: split", spp)
    
    mon = leftstr(label, ione).strip()
    day = getsubstr(label, ione, itwo).strip()
    yr = rightstr(label, itwo).strip()

    print("DEBUG: day", day, "mon", mon, "yr", yr)

    # month string to number
    monnum = 0
    if (mon in enmonth):
        monnum = enmonth.index(mon)+1

    imon = int(monnum)
    if (imon < 1 or imon > 12):
        # not a valid month (should not be possible)
        print("ERROR: invalid month ?", str(imon))
        return ts

    # strip comma from day (if any)
    day = leftfrom(day, ",")

    iday = int(day)
    if (iday < 1 or iday > 31):
        # not a valid day
        print("ERROR: invalid day ?", str(iday))
        return ts

    iyr = int(yr)
    
    ts.setDate(iyr, imon, iday)
    print("DEBUG: to iso: ", ts.makeIsodateStr())
    return ts

# day, month, year
# note: french date has more differences that needs to be parsed
def parse_fr_datelabel(label):
    ts = SimpleTimestamp()

    ione = label.find(" ")
    if (ione < 0):
        return ts

    itwo = label.find(" ", ione+1)
    if (itwo < 0):
        return ts
    
    spp = label.split(" ")
    print("DEBUG: split", spp)
    
    day = leftstr(label, ione).strip()
    mon = getsubstr(label, ione, itwo).strip()
    yr = rightstr(label, itwo).strip()

    print("DEBUG: day", day, "mon", mon, "yr", yr)

    # month string to number
    monnum = 0
    if (mon in frmonth):
        monnum = frmonth.index(mon)+1

    imon = int(monnum)
    if (imon < 1 or imon > 12):
        # not a valid month (should not be possible)
        print("ERROR: invalid month ?", str(imon))
        return ts

    # french date has more differences:
    # "1st" would be written as "1er"
    if (day == "1er"):
        day = "1"
    
    # strip comma from day (if any)
    day = leftfrom(day, ",")
    
    iday = int(day)
    if (iday < 1 or iday > 31):
        # not a valid day
        print("ERROR: invalid day ?", str(iday))
        return ts
    
    iyr = int(yr)
    
    ts.setDate(iyr, imon, iday)
    print("DEBUG: to iso: ", ts.makeIsodateStr())
    return ts

# day, month, year
def parse_sv_datelabel(label):
    ts = SimpleTimestamp()

    ione = label.find(" ")
    if (ione < 0):
        return ts

    itwo = label.find(" ", ione+1)
    if (itwo < 0):
        return ts
    
    spp = label.split(" ")
    print("DEBUG: split", spp)
    
    day = leftstr(label, ione).strip()
    mon = getsubstr(label, ione, itwo).strip()
    yr = rightstr(label, itwo).strip()

    print("DEBUG: day", day, "mon", mon, "yr", yr)

    # month string to number
    monnum = 0
    if (mon in svmonth):
        monnum = svmonth.index(mon)+1

    imon = int(monnum)
    if (imon < 1 or imon > 12):
        # not a valid month (should not be possible)
        print("ERROR: invalid month ?", str(imon))
        return ts

    # strip comma from day (if any)
    day = leftfrom(day, ",")
    
    iday = int(day)
    if (iday < 1 or iday > 31):
        # not a valid day
        print("ERROR: invalid day ?", str(iday))
        return ts
    
    iyr = int(yr)
    
    ts.setDate(iyr, imon, iday)
    print("DEBUG: to iso: ", ts.makeIsodateStr())
    return ts
    
def fromIsodate(label):
    ts = SimpleTimestamp()

    ione = label.find("-")
    if (ione < 0):
        return ts
    itwo = label.find("-", ione+1)
    if (itwo < 0):
        return ts

    spp = label.split("-")
    print("DEBUG: split", spp)

    yr = leftstr(label, ione).strip()
    mon = getsubstr(label, ione+1, itwo).strip()
    day = rightstr(label, itwo+1).strip()

    print("DEBUG: day", day, "mon", mon, "yr", yr)
    
    iyr = int(yr)
    imon = int(mon)
    iday = int(day)

    ts.setDate(iyr, imon, iday)
    print("DEBUG: to iso: ", ts.makeIsodateStr())
    return ts

def make_fi_datelabel(ts : SimpleTimestamp):
    if (ts == None):
        return ""
    
    # must have all three parts, day, mon, yr
    if (ts.isValid() == False):
        return ""
    
    filabel = ""
    filabel += str(ts.day)
    filabel += ". "
    filabel += fimonthcase[ts.month-1]
    filabel += " "
    filabel += str(ts.year)

    print("DEBUG: made date string: ", filabel)
    return filabel

# check label:
# * if has finnish label -> skip
# * if has swedish label -> use for checking match
def comparedatelabels(itemfound):
    print("item id, ", itemfound.getID())
    
    mullabel = ""
    svlabel = ""
    frlabel = ""
    enlabel = ""
    tsen = SimpleTimestamp()
    tsfr = SimpleTimestamp()
    tssv = SimpleTimestamp()
    tsiso = SimpleTimestamp()

    for li in itemfound.labels:
        label = itemfound.labels[li]
        if (li == 'fi'):
            print("DEBUG: found label in finnish: ", label)
            # already in finnish -> skip
            return True

        if (li == 'sv'):
            print("DEBUG: found sv label: ", label)
            # check it matches what we want: parse swedish date
            svlabel = label
            tssv = parse_sv_datelabel(svlabel)
            #print("DEBUG: sv to iso: ", tssv.makeIsodateStr())

        if (li == 'en'):
            print("DEBUG: found en label: ", label)
            # check it matches what we want: parse english date
            enlabel = label
            tsen = parse_en_datelabel(enlabel)
            #print("DEBUG: en to iso: ", tsen.makeIsodateStr())

        if (li == 'fr'):
            print("DEBUG: found fr label: ", label)
            # check it matches what we want: parse french date
            frlabel = label
            tsfr = parse_fr_datelabel(svlabel)
            #print("DEBUG: fr to iso: ", tsfr.makeIsodateStr())
            
        if (li == 'mul'):
            print("DEBUG: found mul label: ", label)
            # ISO-date ?
            # check: is it valid ISO-format label in mullabel?
            mullabel = label
            tsiso = fromIsodate(mullabel)
            #print("DEBUG: iso to iso: ", tsiso.makeIsodateStr())


    # at least one instance is known to be valid:
    # detect case where none are defined
    atleastonematch = False

    # compare parsed timestamps:
    # only compare with timestamps that were found and were parsed (some might be missing)
    if (tsiso.isValid() == True and tsen.isValid() == True):
        if (tsiso.isMatchingDate(tsen.year, tsen.month, tsen.day) == False):
            print("WARN: iso and english don't match: ", mullabel, "en:", enlabel)
            return False
        else:
            atleastonematch = True

    if (tsiso.isValid() == True and tssv.isValid() == True):
        if (tsiso.isMatchingDate(tssv.year, tssv.month, tssv.day) == False):
            print("WARN: iso and swedish don't match: ", mullabel, "sv:", svlabel)
            return False
        else:
            atleastonematch = True

    if (tsen.isValid() == True and tssv.isValid() == True):
        if (tsen.isMatchingDate(tssv.year, tssv.month, tssv.day) == False):
            print("WARN: english and swedish don't match: ", enlabel, "sv:", svlabel)
            return False
        else:
            atleastonematch = True

    if (tsiso.isValid() == True and tsfr.isValid() == True):
        if (tsiso.isMatchingDate(tsfr.year, tsfr.month, tsfr.day) == False):
            print("WARN: iso and french don't match: ", mullabel, "fr:", frlabel)
            #return False
        else:
            atleastonematch = True
    if (tsen.isValid() == True and tsfr.isValid() == True):
        if (tsen.isMatchingDate(tsfr.year, tsfr.month, tsfr.day) == False):
            print("WARN: english and french don't match: ", enlabel, "fr:", frlabel)
            #return False
        else:
            atleastonematch = True
    if (tsfr.isValid() == True and tssv.isValid() == True):
        if (tsfr.isMatchingDate(tssv.year, tssv.month, tssv.day) == False):
            print("WARN: french and swedish don't match: ", frlabel, "sv:", svlabel)
            #return False
        else:
            atleastonematch = True

    if (atleastonematch == True):
        print("DEBUG: Found at least one match for timestamps")

    # iso-date should be most reliable if is found
    if (atleastonematch == True and tsiso.isValid() == True):
        return tsiso
    # english is most commonly found
    if (atleastonematch == True and tsen.isValid() == True):
        return tsen
    # swedish is missing in many cases
    if (atleastonematch == True and tssv.isValid() == True):
        return tssv
    # if others are missing there should still be english label..
    if (tsen.isValid() == True):
        return tsen
    return None


def hasfinnishlabel(itemfound):
    print("item id, ", itemfound.getID())

    for li in itemfound.labels:
        label = itemfound.labels[li]
        if (li == 'fi'):
            print("DEBUG: found label in finnish: ", label)
            # already in finnish 
            return True
    return False

def getfinnishlabelfromitem(itemfound):

    print("item id, ", itemfound.getID())

    for li in itemfound.labels:
        label = itemfound.labels[li]
        if (li == 'fi'):
            print("DEBUG: found label in finnish: ", label)
            return label
    return ''

def getfinnishdatelabel(repo, itemqcode):

    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return ''

    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page, skipping")
            return '' # skip for now

    return getfinnishlabelfromitem(itemfound)
   

def getfinnishyearlabel(repo, itemqcode):

    itemfound = pywikibot.ItemPage(repo, itemqcode)
    if (itemfound.isRedirectPage() == True):
        return ''

    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page, skipping")
            return ''# skip for now

    return getfinnishlabelfromitem(itemfound)

# date items are not of single clear instance..
def isDateItem(item):
    isperyeardate = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # tietyn vuoden kalenteripäivämäärä
        
        if (claim.getTarget().id == 'Q47150325'):
            print("instance ok", claim.getTarget().id)
            isperyeardate = True
        
    return isperyeardate

def isDisambiguation(item):
    isdis = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page, skipping")
            isdis = True
            break
        
    return isdis

def addItemLabelInFinnish(item, newlabel):
    
    for li in item.labels:
        label = item.labels[li]
        if (li == 'fi'):
            print("DEBUG: found label in finnish: ", label)
            return True

    isDescriptionMissing = True
    for dscl in item.descriptions:
        description = item.descriptions[dscl]
        if (dscl == 'fi'):
            print("DEBUG: found description in finnish ")
            isDescriptionMissing = False
            break

    new_labels = {'fi': newlabel}
    item.editLabels(labels=new_labels, summary="Adding missing label in Finnish.")

    # kuvausta ei ole myöskään ranskaksi merkitty
    #if (isDescriptionMissing == True):
    #    new_descr = {"fi": "päiväys"}
    #    item.editDescriptions(new_descr, summary="Adding missing description in Finnish.")

    # read back
    item.get()
    
    return True

def getPartOfList(item):
    qlist = list()
    part_of = item.claims.get('P361', [])
    for claim in part_of:
        qid = claim.getTarget().id
        if (qid not in qlist):
            qlist.append(qid)
    return qlist

def getConsistsOfList(item):
    qlist = list()
    consists_of = item.claims.get('P527', [])
    for claim in consists_of:
        qid = claim.getTarget().id
        if (qid not in qlist):
            qlist.append(qid)
    return qlist
    

def addDatewikidatalabel(wdsite, repo, itemqcode, parentqcode):

    dateitem = pywikibot.ItemPage(repo, itemqcode)
    if (dateitem.isRedirectPage() == True):
        return False

    #dictionary = itemfound.get()
    
    if (isDisambiguation(dateitem) == True):
        print("disambiguation page, skipping.")
        return False

    if (isDateItem(dateitem) == False):
        print("not recognized as date item.")
        return False

    # check parent is marked in "part of"
    partoflist = getPartOfList(dateitem)
    if parentqcode not in partoflist:
        print("not part of parent?", parentqcode)
        return None
   
    # already has finnish label -> no need to do anything
    if (hasfinnishlabel(dateitem) == True):
        return True
    
    # check entity type (instance of)
    #instance_of = itemfound.claims.get('P31', [])
    #for claim in instance_of:
    #    if (claim.getTarget().id == 'Q4167410'):
    
    timestamp = comparedatelabels(dateitem)
    if (timestamp == None):
        print("missing date from labels.")
        return False
    if (timestamp.isValid() == False):
        print("mismatching or missing dates in labels.")
        return False
    
    filabel = make_fi_datelabel(timestamp)
    if (filabel == ""):
        print("could not make date label in finnish.")
        return False

    if (addItemLabelInFinnish(dateitem, filabel) == False): 
        print("could not add label in finnish.")
        return False
    
    return True


def itemlistDecadesincentury(wdsite, repo, itemqcode):
    
    centuryitem = pywikibot.ItemPage(repo, itemqcode)
    if (centuryitem.isRedirectPage() == True):
        return None

    if (isDisambiguation(centuryitem) == True):
        print("disambiguation page, skipping.")
        return None

    # check parent is marked in "part of"
    #partoflist = getPartOfList(centuryitem)
    #if parentqcode not in partoflist:
    #    print("not part of parent?", parentqcode)
    
    # instance of vuosisata (Q578)

    iscentury = False
    instance_of = centuryitem.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q578'):
            print("ok, instance of calendar century")
            iscentury = True
            break
    if (iscentury == False):
        print("not calendar century")
        return None
    
    decadeqlist = getConsistsOfList(centuryitem)
    return decadeqlist


def itemlistYearsindecade(wdsite, repo, itemqcode, parentqcode):
    
    decadeitem = pywikibot.ItemPage(repo, itemqcode)
    if (decadeitem.isRedirectPage() == True):
        return None

    if (isDisambiguation(decadeitem) == True):
        print("disambiguation page, skipping.")
        return None

    # check parent is marked in "part of"
    partoflist = getPartOfList(decadeitem)
    if parentqcode not in partoflist:
        print("not part of parent?", parentqcode)
        return None

    # instance of vuosikymmen (Q39911)

    isdecade = False
    instance_of = decadeitem.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q39911'):
            print("ok, instance of calendar decade")
            isdecade = True
            break
    if (isdecade == False):
        print("not calendar decade")
        return None
    
    yearqlist = getConsistsOfList(decadeitem)
    return yearqlist


def itemlistMonthsinyear(wdsite, repo, itemqcode, parentqcode):
    
    # list items in property P527 for each month of the year:
    # .. august 2025, september 2025 ..

    #repo = wdsite.data_repository()
    
    yearitem = pywikibot.ItemPage(repo, itemqcode)
    if (yearitem.isRedirectPage() == True):
        return None

    #dictionary = itemfound.get()

    if (isDisambiguation(yearitem) == True):
        print("disambiguation page, skipping.")
        return None

    # check parent is marked in "part of"
    partoflist = getPartOfList(yearitem)
    if parentqcode not in partoflist:
        print("not part of parent?", parentqcode)
        return None
    
    # instance of kalenterivuosi (Q3186692)

    isyear = False
    instance_of = yearitem.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q3186692'):
            print("ok, instance of calendar year")
            isyear = True
            break
    if (isyear == False):
        print("not calendar year")
        return None
    
    monthqlist = getConsistsOfList(yearitem)
    return monthqlist


def itemlistDaysinmonth(wdsite, repo, itemqcode, parentqcode):
    
    # list items in property P527 for each day of the month:
    # .. august 1, 2025, august 2, 2025 ..

    #repo = wdsite.data_repository()
    
    monthitem = pywikibot.ItemPage(repo, itemqcode)
    if (monthitem.isRedirectPage() == True):
        return None

    #dictionary = itemfound.get()

    if (isDisambiguation(monthitem) == True):
        print("disambiguation page, skipping.")
        return None

    # check parent is marked in "part of"
    partoflist = getPartOfList(monthitem)
    if parentqcode not in partoflist:
        print("not part of parent?", parentqcode)
        return None

    # instance of tietyn vuoden kalenterikuukausi (Q47018478)

    ismonth = False
    instance_of = monthitem.claims.get('P31', [])
    for claim in instance_of:
        
        if (claim.getTarget().id == 'Q47018478'):
            print("ok, instance of calendar month")
            ismonth = True
            break
    if (ismonth == False):
        print("not calendar month")
        return None

    dayqlist = getConsistsOfList(monthitem)
    return dayqlist


## main()


wdsite = pywikibot.Site('wikidata', 'wikidata')
wdsite.login()
repo = wdsite.data_repository()

# ensimmäinen vuosituhat (Q25868)
# toinen vuosituhat (Q25860)
# kolmas vuosituhat (Q26224)

#centuryqcode = "Q6955" # 1800-luku
centuryqcode = "Q6927" # 1900-luku
#centuryqcode = "Q6939" # 2000-luku 

print("checking century by code", centuryqcode)
decadelist = itemlistDecadesincentury(wdsite, repo, centuryqcode)
for decadeqcode in decadelist:

    #decadeqcode = "Q35024" # 2000-vuosikymmen
    #decadeqcode = "Q19022" # 2010-luku
    #decadeqcode = "Q534495" # 2020-luku

    print("checking decade by code", decadeqcode)
    yearlist = itemlistYearsindecade(wdsite, repo, decadeqcode, centuryqcode)
    for yearqcode in yearlist:

        # huom, 2026 vuodelle puuttuu labeleitä myös muilla kielillä
        #yearqcode = "Q49616" # 2025

        #yearqcode = "Q25245" # 2016 # check, some oddities
        #yearqcode = "Q25291" # 2018 # check, some oddities

        print("checking year by code", yearqcode)

        monthlist = itemlistMonthsinyear(wdsite, repo, yearqcode, decadeqcode)
        for monthqcode in monthlist:

            #monthqcode = "Q61312921" # marraskuu 2025
            #monthqcode = "Q19249071" # toukokuu 2016 # check, some oddities
            #monthqcode = "Q29110086" # heinäkuu 2018 # check, some oddities

            print("checking month by code", monthqcode)

            daylist = itemlistDaysinmonth(wdsite, repo, monthqcode, yearqcode)
            for dayqcode in daylist:

                # dayqcode = "Q69307710" # 1. marraskuuta 2025
                print("checking day by code", dayqcode)

                if (addDatewikidatalabel(wdsite, repo, dayqcode, monthqcode) == False):
                    print("Failed to add label, exiting.")
                    exit()

                print("day done by code", dayqcode)

            print("month done by code", monthqcode)

        print("year done by code", yearqcode)

    print("decade done by code", decadeqcode)

print("century done by code", centuryqcode)

#pywikibot.info('----')
#pywikibot.showDiff(oldtext, temptext,2)
#pywikibot.info('Edit summary: {}'.format(summary))

if wdsite.userinfo['messages']:
    print("Warning: Talk page messages. Exiting.")
    #exit()

