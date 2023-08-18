# -*- coding: latin-1 -*-
import pywikibot
from pywikibot.specialbots import UploadRobot
import urllib
import json
import time
import re
import requests
import imagehash
from PIL import Image
from datetime import date

# Add finna_id's of images already in Commons here
skip_finna_ids = [
'mfa.0422597e-026f-4c2c-9ed8-4152bfa882b2',
'mfa.04d07e52-1f57-4796-969f-c9d98437c7d4',
'mfa.05a25c4f-e375-45db-b4ce-44f9d252963c',
'mfa.0648b2d7-d36d-4f4f-aefc-2141ef289b10',
'mfa.07c36efd-7fe4-40fd-956e-10999b00cf19',
'mfa.08d8439c-6f53-4bdd-94be-009eda861e0e',
'mfa.0e90699a-6f3a-4a10-ace6-187a71d1be91',
'mfa.10a511dd-5dae-4ceb-aae3-510fdebf29e1',
'mfa.153f3f6e-dcd2-4a0f-be1f-bddc580368be',
'mfa.170a8023-868a-4491-82f0-41804f5a6eb8',
'mfa.1e0dc2f7-d835-4f78-9449-5929c286869f',
'mfa.1ffa0598-973c-4663-88a8-a821145aa0f2',
'mfa.22892c91-8ab5-478f-a588-c0a42eb6533b',
'mfa.23d3ec47-20ca-4148-af3d-50aeb11884ce',
'mfa.2676a520-e564-4eed-8169-97cdf4c60704',
'mfa.05a20c48-37ea-47bf-8913-54694d3c9397',
'mfa.1a8c230e-7c24-4602-8be9-4cb42a08f191',
'mfa.269d9489-ccab-42ec-9658-b68a5ebc04f3',
'mfa.2722c0f7-200a-4ca0-8172-7657b255922f',
'mfa.2943c920-026a-440b-8c37-f657ed5c30c3',
'mfa.2a9bce03-c72d-4286-b521-7553a04bd702',
'mfa.2b77a3d5-e7af-4b1c-85e9-e2352e940073',
'mfa.2b79d289-5814-4920-bc72-c39260a71b3d',
'mfa.2bac4686-430f-421c-819d-86ec65a43011',
'mfa.2e98c676-d3dd-4e70-9959-d18f9a169dc2',
'mfa.2ec90f30-4371-4c1d-ad2c-52cc6741ce05',
'mfa.316ec114-00af-4515-841d-280e1d045099',
'mfa.31844cb3-3fc3-4fb2-952c-6a7625d7d34e',
'mfa.339edab6-d695-4ee0-a95d-2ef4f3c937a5',
'mfa.34517bc9-5aed-4e02-82d1-5c02da780743',
'mfa.3635dd30-b1ff-4c5f-9439-aee8f8b00de3',
'mfa.3ae4a812-9e03-4733-9690-7c1588ea22b4',
'mfa.45274f20-e50b-4414-b37b-b9d71005d57f',
'mfa.45d40193-6bb7-4519-80a2-9f0de63d7e1e',
'mfa.460401ea-fb70-4431-b30d-7fc681ab507a',
'mfa.46813764-831f-49b7-9def-d82cd61e20fc',
'mfa.47a471ed-133b-4f73-806e-002ff19a69b7',
'mfa.4a6a9a68-d7f6-4dd8-bf22-fef35ae157ec',
'mfa.4a7b0a5f-3429-43b9-9013-687afce16773',
'mfa.4bb3b023-8953-47cb-94fe-2da7a6a1a83d',
'mfa.52c1d9fe-eca7-4d3c-a513-6721f27dc589',
'mfa.5514dbf9-8ff0-4918-9e62-b522f5643604',
'mfa.55ff3260-5c56-4da8-b071-ab3060522af6',

]

# Finna author name -> Wikdata id mapping
authors={
'Saarinen, Eliel' : 'Q312028',
'Gesellius, Lindgren & Saarinen' : 'Q2563295',
'Gesellius & Saarinen' : 'Q98150301',
'Hård af Segerstad, Karl': 'Q5820266',
'Gesellius, Herman' : 'Q2562660', # Finnish architect (1874-1916)
'Ehrstr\u00F6m, E. O. W.' : 'Q11858121',
}

# Finna author name -> Creator template mapping
author_creator_templates={
'Saarinen, Eliel' : '{{Creator:Eliel Saarinen}}',
'Gesellius, Lindgren & Saarinen' : '{{Creator:Gesellius, Lindgren & Saarinen}}',
'Gesellius & Saarinen' : '{{Creator:Gesellius & Saarinen}}',
'Hård af Segerstad, Karl' : '{{Creator:Karl Hård af Segerstad}}',
'Gesellius, Herman' : '{{Creator:Herman Gesellius}}',
'Ehrstr\u00F6m, E. O. W.' : '{{Creator:Eric Ehrstr\u00F6m}}'
}

# Finna author name -> Commons cat mapping
author_commonscats={
'Saarinen, Eliel' : '[[Category:Eliel Saarinen]]',
'Gesellius, Lindgren & Saarinen' : '[[Category:Gesellius, Lindgren, Saarinen Architects]]',
'Gesellius & Saarinen' : '[[Category:Gesellius & Saarinen]]',
'Hård af Segerstad, Karl': '[[Category:Karl Hård af Segerstad]]',
'Gesellius, Herman' : '[[Category:Herman Gesellius]]',
'Ehrstr\u00F6m, E. O. W.' : '[[Category:Eric Ehrstr\u00F6m]]'
}

# Finna role name -> Wikidata id mapping
roles= {
'arkkitehti':'Q42973',
'arkkitehtitoimisto':'Q4387609',
'taiteilija':'Q483501'
}

def getFileinfoFromEvent(event, finna_id):
   if "type" in event and event.get("type")=="upload":
      if "comment" in event and finna_id in event.get("comment"):
         if "title" in event and finna_id in event.get("title"):
            ret={}
            ret["page_id"]=event.get("pageid")
            ret["title"]=event.get("title")
            ret["comment"]=event.get("comment")
            ret["mediaitem"]="M" +  str(event.get("pageid"))
            return ret

   print("get_fileinfo_from_event failed")
   for e in event:
      print(e + "\t" + str(event.get(e)))
   return ""


def addSDCPhash(site, media_identifier, phashchecksum, width, height, imagehash_version):
   propertyvalue=phashchecksum
   claim_id=createMediainfoClaim(site, media_identifier, "P9310", propertyvalue)
   setMediainfoQualifier(site, media_identifier, claim_id, "P9310", propertyvalue, "P348", imagehash_version)


   heightvalue={ 'amount': '+' + str(height), 'unit': 'http://www.wikidata.org/entity/Q355198' }
   widthvalue= { 'amount': '+' + str(width), 'unit': 'http://www.wikidata.org/entity/Q355198' }

   setMediainfoQualifier(site, media_identifier, claim_id, "P9310", propertyvalue, "P2048", heightvalue)
   setMediainfoQualifier(site, media_identifier, claim_id, "P9310", propertyvalue, "P2049", widthvalue)

def addSDCSource(site, media_identifier, source_of_file, source_url, operator, publisher):
   propertyvalue={'entity-type':'item','id': source_of_file }
   claim_id=createMediainfoClaim(site, media_identifier, "P7482", propertyvalue)

   setMediainfoQualifier(site, media_identifier, claim_id, "P7482", propertyvalue, "P973", source_url)

   qualifiervalue={'entity-type':'item','id': operator }
   setMediainfoQualifier(site, media_identifier, claim_id, "P7482", propertyvalue, "P137", qualifiervalue)

   qualifiervalue={'entity-type':'item','id': publisher }
   setMediainfoQualifier(site, media_identifier, claim_id, "P7482", propertyvalue, "P123", qualifiervalue)


def addSDCInfo(user, authors, licence, finna_id, image_phash, image_width, image_height, imagehash_version, caption):
   logimage=getFileinfoFromEvent(user.last_event, finna_id)

   if (logimage==""):
      return

   addCaption(site, logimage["mediaitem"], "fi", caption)

   if licence == "CC BY 4.0": 
      # P6216 = copyright status
      # Q50423863 = copyrighted
      # P275 = Licence
      # Q20007257 = Creative Commons Attribution 4.0 International

      propertyvalue={'entity-type':'item','id': "Q50423863" }
      claim_id=createMediainfoClaim(site, logimage["mediaitem"], "P6216", propertyvalue)

      propertyvalue={'entity-type':'item','id': "Q20007257" }
      claim_id=createMediainfoClaim(site, logimage["mediaitem"], "P275", propertyvalue)

   # P7482 = source of file : Q74228490 = file available on the internet
   # P973 = described at URL https://www.finna.fi/Record/hkm.HKMS000005:km0000n3de
   # P137 = operator : Q420747 National Library of Finland (Finna.fi)
   # P123 = publisher : Q1418116 Museum of Finnish Architecture
   addSDCSource(site, logimage["mediaitem"], "Q74228490", "https://finna.fi/Record/" + finna_id, "Q420747", "Q1418116")

   # Add imagehash info
   addSDCPhash(site, logimage["mediaitem"], str(image_phash), image_width, image_height, imagehash_version)

   # Add Finna id property
   claim_id=createMediainfoClaim(site, logimage["mediaitem"], "P9478", finna_id)

   #author
   for author in authors:
      propertyvalue={'entity-type':'item','id': author["author_wikidata_id"] }
      claim_id=createMediainfoClaim(site, logimage["mediaitem"], "P170", propertyvalue)
      if claim_id:
         qualifiervalue={'entity-type':'item','id': author["role_wikidata_id"] }
         setMediainfoQualifier(site, logimage["mediaitem"], claim_id, "P170", propertyvalue, "P3831", qualifiervalue)


def setMediainfoQualifier(site, media_identifier, claim_id, property, propertyvalue, qualifier, qualifiervalue):
   exists=getMediainfoClaimId(site, media_identifier, property, propertyvalue, qualifier, qualifiervalue)

   if exists: 
      return exists

   if claim_id=="":
      claim_id=getMediainfoClaimId(site, media_identifier, property, value)
      if not claim_id:
         print("Claim id not found. Adding qualifier failed")
         exit(1)

   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbsetqualifier',
      'format' : u'json',
      'claim' : claim_id,
      'property' : qualifier,
      'snaktype' : 'value',
      'value' : json.dumps(qualifiervalue),
      'token' : csrf_token,
      'bot' : True, # in case you're using a bot account (which you should)
   }

   request = site.simple_request(**payload)
   try:
      ret=request.submit()
      print(ret)
      claim=ret.get("claim")
      if claim:
         return claim.get("id")
      else:
         print("Claim created but there was an unknown problem")
         print(ret)
         exit(1)

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)



def addCaption(site, media_identifier, lang, caption):
#postdata = {u'action' : u'wbeditentity',
#                    u'format' : u'json',
#                    u'id' : mediaid,
#                    u'data' : json.dumps({ u'labels' : labels}),
#                    u'token' : token,
#                    u'summary' : summary,
#                    u'bot' : True,
#                    }

   captions={}
   captions["fi"] = {u'language' : 'fi', 'value' : caption }
   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbeditentity',
      'format' : u'json',
      'id' : media_identifier,
      'data' :  json.dumps({ u'labels' : captions}),
      'token' : csrf_token,
      'bot' : True, # in case you're using a bot account (which you should)
   }
   print(payload)
   request = site.simple_request(**payload)
   try:
      ret=request.submit()
#      claim=ret.get("claim")
#      if claim:
#         return claim.get("id")
#      else:
#         print("Claim created but there was an unknown problem")
#         print(ret)
#         exit(1)

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)



def createMediainfoClaim(site, media_identifier, property, value):
   exists=getMediainfoClaimId(site, media_identifier, property, value)
   if exists: 
      return exists

   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbcreateclaim',
      'format' : u'json',
      'entity' : media_identifier,
      'property' : property,
      'snaktype' : 'value',
      'value' : json.dumps(value),
      'token' : csrf_token,
      'bot' : True, # in case you're using a bot account (which you should)
   }
   print(payload)
   request = site.simple_request(**payload)
   try:
      ret=request.submit()
      claim=ret.get("claim")
      if claim:
         return claim.get("id")
      else:
         print("Claim created but there was an unknown problem")
         print(ret)
         exit(1)

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)


def getMediainfoClaims(site, media_identifier, property):
   payload = {
      'action' : 'wbgetclaims',
      'format' : u'json',
      'entity' : media_identifier,
      'property' : property,
   }
   request = site.simple_request(**payload)
   try:
      ret=request.submit()
      return ret

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)



def testSnak(snak, snakvalue):
   if snak:
      datavalue=snak.get("datavalue")
      if datavalue:
         if datavalue["type"]=="wikibase-entityid":
            value=datavalue.get("value")
            if value and value.get("id")==snakvalue:
               return True
         elif datavalue["type"]=="string":
            if datavalue.get("value")==snakvalue:
               return True
         elif datavalue["type"]=="quantity":
            value=datavalue.get("value")
            if value.get("amount")==snakvalue:
               return True
         else:
            print("ERROR: Unknown datavalue type")
            print(datavalue)
            exit(1)
   return False


def getMediainfoClaimId(site, media_identifier, property, propertyvalue="", qualifier="", qualifiervalue="" ):
   claims=getMediainfoClaims(site, media_identifier, property)
   property_found=False
   if ('entity-type' in propertyvalue and propertyvalue.get('entity-type')=='item'):
      propertyvalue=propertyvalue.get('id')

   if ('entity-type' in qualifiervalue and qualifiervalue.get('entity-type')=='item'):
      qualifiervalue=qualifiervalue.get('id')

   if ('amount' in propertyvalue):
      propertyvalue=propertyvalue.get('amount')

   if ('amount' in qualifiervalue):
      qualifiervalue=qualifiervalue.get('amount')

   claimlist=claims.get('claims')
   if claimlist:
      properties=claimlist.get(property)
      if properties:
         for property in properties:
            if propertyvalue=="":
               property_found=True
            else:
               qualifiers=property.get("qualifiers")
               property_found=testSnak(property.get("mainsnak"), propertyvalue)

            if qualifier=="" and property_found:
               print(json.dumps(property))
               return property["id"]
            elif property_found:
               qualifiers=property.get("qualifiers")
               if qualifiers and qualifiers.get(qualifier):
                  if qualifiervalue=="":
                     return property["id"]
                  else:
                     for qualifierSnak in qualifiers.get(qualifier):
                        qualifier_found=testSnak(qualifierSnak, qualifiervalue)
                        if qualifier_found:
                           return property["id"]
   return False

def addAuthorQid(self, mediaid, currentdata, authorqid):
   """
   Add an author that has a qid
   :param mediaid:
   :param currentdata:
   :return:
   """
   if currentdata.get('statements') and currentdata.get('statements').get('P170'):
      return False
   return self.addClaimJson(mediaid, 'P170', authorqid)

def addClaimJson(self, mediaid, pid, qid):
   """
   Add a claim to a mediaid
   :param mediaid: The mediaid to add it to
   :param pid: The property P id (including the P)
   :param qid: The item Q id (including the Q)
   :param summary: The summary to add in the edit
   :return: Nothing, edit in place
   """
   toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': pid,
                                 'datavalue': { 'value': { 'numeric-id': qid.replace(u'Q', u''),
                                                           'id' : qid,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
   return [toclaim,]


def addQualifierValue(site, claimid, property, value, snaktype, summary):
   csrf_token = site.tokens['csrf']
   payload = {
      'action' : 'wbsetqualifier',
      'format' : u'json',
      'claim' : claimid,
      'property' : property,
      'value' : json.dumps(value),
      'token' : csrf_token,
      'summary' : summary,
      'snaktype' : snaktype,
      'bot' : True, # in case you're using a bot account (which you should)
   }
   request = site.simple_request(**payload)
   try:
      ret=request.submit()
      return ret

   except pywikibot.data.api.APIError as e:
      print('Got an error from the API, the following request were made:')
      print(request)
      print('Error: {}'.format(e))
      exit(1)

def get_licence_template(str): 
   if (str=="CC BY 4.0"):
      return "{{cc-by-4.0}}"
   else:
      print("get_licence_template failed")
      exit(1)

def get_institution_template(str):
   if (str=="0/MFA/"):
      return "{{Institution:Museum of Finnish Architecture}}"
   else:
      print("get_institution_template failed")
      exit(1)

def get_institution_category(str):
   if (str=="0/MFA/"):
      return "[[Category:Files from Museum of Finnish Architecture]]";
   else:
      print("get_institution_category failed")
      exit(1)

def get_institution(record, defaultValue="", expectedValue=0, mandatory=0):
   if "buildings" in record:
      if expectedValue and record.get("buildings")[0]["value"] != expectedValue:
         print("ERROR: get_institution failed")
         print("expected: " + expectedValue)
         print("got: " + record.get("buildings")[0]["value"])
         exit(1)
      else:
         return record.get("buildings")[0]["value"]
   elif mandatory:
      print("ERROR: get_institution failed:")
      print("value missing: ")
      exit(1)
   else:
      return defaultValue

def get_licence(record, expectedValue=0):
   if "imageRights" in record:
      if expectedValue and record.get("imageRights")["copyright"] != expectedValue:
         print("ERROR: get_licence failed")
         print("expected: " + expectedValue)
         print("got: " + record.get("imageRights")["copyright"])
         exit(1)
      else:
         return record.get("imageRights")["copyright"]
   else:
      print("ERROR: get_licence failed:")
      print("value missing: ")
      exit(1)


def test_tif_fileformat(record):
   tmp=record
   if "imagesExtended" in tmp:
      for tmp in record["imagesExtended"]:
         s="imagesExtended"
         if "highResolution" in tmp:
            s="highResolution"

            tmp=tmp["highResolution"]

            if "original" in tmp:
               s="original"

               tmp=tmp["original"][0]
               if "format" in tmp:
                  if tmp["format"]=='tif':
                      return tmp["url"]
   print("File format failed: " + s)
   print(json.dumps(tmp, indent=4, sort_keys=True))
   exit(1)
   


def parse_authors(record):
   if ("nonPresenterAuthors" in record):
      rows=[]
      for author in record["nonPresenterAuthors"]:
         row={}
         print(author)
         # Read Finna author name
         if "name" in author:
            row["finna_name"]=author["name"]
         else:
            print("parse_authors failed: author_name missing")
            exit(1)

         # Read wikidata id
         if row["finna_name"] in authors:
            row["author_wikidata_id"]=authors[row["finna_name"]]
         else:
            print("parse_authors failed: author_wikidata_id missing")
            print(row["finna_name"]);
            print(authors);
            exit(1)

         # Read author_commons_category
         if row["finna_name"] in author_commonscats:
            row["author_commonscat"]=author_commonscats[row["finna_name"]]
         else:
            print("parse_authors failed: author_commonscat missing")
            exit(1)

         # Read author_creator_template
         if row["finna_name"] in author_creator_templates:
            row["author_creator_template"]=author_creator_templates[row["finna_name"]]
         else:
            print("parse_authors failed: author_creator_template missing")
            exit(1)

         # Read Finna author role
         if "role" in author:
            row["finna_role"]=author["role"]
         else:
            print("parse_authors failed: author_role missing")
            exit(1)

         # Read wikidata id
         if row["finna_role"] in roles:
            row["role_wikidata_id"]=roles[row["finna_role"]]
         else:
            print("parse_authors failed: role_wikidata_id missing")
            exit(1)
         rows.append(row)

   else:
      print("nonPrsenterAuthors missing")
      exit(1)

   return rows

def downloadFile(url):
    local_filename = "tmp/file_to_commons.tif"
    r = requests.get(url)
    f = open(local_filename, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024): 
        if chunk: # filter out keep-alive new chunks
            f.write(chunk)
    f.close()
    return local_filename



def replace_or_die(old, new, text):
   newtext=text.replace(old, new)
   if (newtext==text):
      print("Replace_or_die failed:" + old +"\t" + new)
      exit(1)

   return newtext


def get_wikitext(out):
   creator_templates=""
   creator_categories=""

   for row in out["authors"]:
      if ("author_commonscat" in row):
         creator_categories+="\n" + row["author_commonscat"]
      if ("author_creator_template" in row):
         creator_templates+="\n" + row["author_creator_template"]

   creator_templates=creator_templates.strip()
   creator_categories=creator_categories.strip()

   template="""
== {{int:filedesc}} ==
{{Photograph
 |photographer       = ___CREATOR_TEMPLATE___
 |title              = ___TITLE___
 |description        = ___DESCRIPTION___
 |depicted people    =
 |depicted place     = ___PLACE___
 |date               = ___DATE___
 |medium             =
 |dimensions         =
 |institution        = ___INSTITUTION_TEMPLATE___
 |department         = 
 |references         =
 |object history     =
 |exhibition history =
 |credit line        =
 |inscriptions       =
 |notes              =
 |accession number   = ___IDENTIFIER___
 |source             = ___SOURCE___
 |permission         = ___PERMISSION_DISCLAIMER___ ''___PERMISSION___''
 |other_versions     =
 |wikidata           =
 |camera coord       = ___COORD___
}}

== {{int:license-header}} ==
___LICENCE_TEMPLATE___
___FOOTER_TEMPLATE___
___INSTITUTION_CATEGORY___
___CREATOR_CATEGORY___
___TRACKING_CATEGORY___
___YEAR_CATEGORY___
___PLACE_CATEGORY___
"""

   params={
      'CREATOR_TEMPLATE': creator_templates,
      'TITLE': out["title"],
      'DESCRIPTION': out["description"],
      'PLACE': "",
      'DATE': "",
      'LICENCE_TEMPLATE': get_licence_template(out["licence"]),
      'PERMISSION' : "; ".join(out["imageRights"]["description"]),
      'PERMISSION_DISCLAIMER' : ("Kuvan k\u00E4ytt\u00F6oikeusteksti Finnassa ") + str(date.today()) +":", 
      'SOURCE': "Finna: [https://finna.fi/Record/" + out["finna_id"] + " " + out["finna_id"]  + "]",
      'IDENTIFIER': out["identifierString"],
      'INSTITUTION_TEMPLATE': get_institution_template(out["institution"]),
      'COORD': "",
      'FOOTER_TEMPLATE': "{{FinnaReview}}",
      'INSTITUTION_CATEGORY': get_institution_category(out["institution"]),
      'CREATOR_CATEGORY': creator_categories,
      'TRACKING_CATEGORY': "[[Category:Files uploaded by FinnaUploadBot]]",
      'YEAR_CATEGORY': "",
      'PLACE_CATEGORY':""
   }

   for key in params:
      fullkey="___" + key + "___"
      template=replace_or_die(fullkey, params[key], template)

   return re.sub('\n+', '\n', template.strip())


def finnaApiParameter(name, value):
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)


def finna_exists(id):
    url='https://imagehash.toolforge.org/finnasearch?finna_id=' + str(id)
    print(url)
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    print(data)
    if len(data):
        return True
    else:
        return False

##################################
# Main()
#

pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")
site.login()
user = pywikibot.User(site, site.user())
repo = site.data_repository()

url="https://api.finna.fi/v1/search?" 
url+= finnaApiParameter('filter[]', '~format_ext_str_mv:"0/Image/"') 
url+= finnaApiParameter('filter[]', 'free_online_boolean:"1"') 
url+= finnaApiParameter('filter[]', '~building:"0/MFA/"') 
url+= finnaApiParameter('filter[]', '~usage_rights_str_mv:"usage_B"') 
url+= finnaApiParameter('type','AllFields')
url+= finnaApiParameter('field[]', 'geoLocations')
url+= finnaApiParameter('field[]', 'id')
url+= finnaApiParameter('field[]', 'title')
url+= finnaApiParameter('field[]', 'subTitle')
url+= finnaApiParameter('field[]', 'summary')
url+= finnaApiParameter('field[]', 'buildings')
url+= finnaApiParameter('field[]', 'formats')
url+= finnaApiParameter('field[]', 'imageRights')
url+= finnaApiParameter('field[]', 'images')
url+= finnaApiParameter('field[]', 'imagesExtended')
url+= finnaApiParameter('field[]', 'onlineUrls')
url+= finnaApiParameter('field[]', 'openUrl')
url+= finnaApiParameter('field[]', 'nonPresenterAuthors')
url+= finnaApiParameter('field[]', 'onlineUrls')
url+= finnaApiParameter('field[]', 'subjects')
url+= finnaApiParameter('field[]', 'classifications')
url+= finnaApiParameter('field[]', 'events')
url+= finnaApiParameter('field[]', 'identifierString')
url+= finnaApiParameter('limit','100') 

print(url)

with urllib.request.urlopen(url) as file:
    data = json.loads(file.read().decode())

    if ("status" in data and data.get("status")=="OK"):
       records=data.get("records")
       for record in records:
          original_url=test_tif_fileformat(record)
          if not original_url:
             continue

          # Manual skip lists for files already in Commons
          if record["id"] in skip_finna_ids:
             continue

   
          if finna_exists(record['id']):
              continue

          out={}
          out["institution"]=get_institution(record, "", "0/MFA/", 1)
          out["title"]=record["title"]
          out["description"]=record["summary"][0]
          out["finna_id"]=record["id"]
          out["identifierString"]=record["identifierString"]
          out["imageRights"]=record["imageRights"]
          out["licence"]=get_licence(record, "CC BY 4.0")
          out["original_url"]=original_url
          out["authors"]=parse_authors(record)

          wikitext=get_wikitext(out)
          summary="Uploading " + out["licence"] + " licenced file from https://finna.fi/Record/" + out["finna_id"];
          filename=out["title"] + " (" + out["finna_id"] +").tif"

          print("\n")

          print("Downloading file " + out["original_url"] +"\n")
          local_file= downloadFile(out["original_url"])

          im = Image.open(local_file)
          out["image_phash"] = imagehash.phash(im)
          image_width, image_height = im.size
          imagehash_version= "Imagehash " + str(imagehash.__version__)

          keep_filename = bool(re.search(";", filename))!=True

          # https://github.com/wikimedia/pywikibot/blob/master/pywikibot/specialbots/_upload.py
          bot = UploadRobot(
                   local_file,
                   description=wikitext,
                   summary=summary,
                   use_filename=filename,
                   target_site=site,
                   verify_description=False,
                   keep_filename=keep_filename
                   )

          bot.run()

          addSDCInfo(user, out["authors"], out["licence"], out["finna_id"], out["image_phash"], image_width, image_height, imagehash_version, out["title"])



