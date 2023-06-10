from SPARQLWrapper import SPARQLWrapper, JSON
import os
import configparser
import pymysql
import json

# Open database connections to Wikimedia Commons replica
def connect_commonsdb():
    replica_path='wikitech_replica.my.cnf'
    if os.path.exists(replica_path):          #check that the file is found
        config = configparser.ConfigParser()
        config.read(replica_path)
    else:
        print(replica_path + ' file not found')
        exit(1)

    fiwiki_con = pymysql.connect(
        host='localhost',
        port=3306,
        user=config['client']['user'].replace("'", ""),
        password=config['client']['password'].replace("'", ""),
        db='commonswiki_p',
        charset='utf8',
        cursorclass=pymysql.cursors.DictCursor)
    return fiwiki_con

# get category information
def get_categories(titles):
    with commons_con.cursor() as cur:
        sql="SELECT * FROM category WHERE cat_title IN %(titles)s "
        cur.execute(sql, {
            'titles':titles
        })
        rows = cur.fetchall() 
        return rows

# get category information
def get_subcats(titles):
    ret=[]

    with commons_con.cursor() as cur:
        sql="""
SELECT 
   page_title
FROM categorylinks,page 
     LEFT JOIN page_props ON pp_page=page_id AND pp_propname="hiddencat" 
WHERE 
    pp_value IS NULL 
    AND cl_to IN %(titles)s 
    AND cl_from=page_id  
    AND cl_type='subcat' 
    AND page_namespace=14
    GROUP BY page_title
"""
        cur.execute(sql, {
            'titles':titles
        })

        rows = cur.fetchall()
        for row in rows:
            ret.append(row['page_title'])

        return ret

def get_page_ids(titles):
    ret=[]
    with commons_con.cursor() as cur:
        sql="SELECT page_id FROM page, categorylinks,image WHERE img_name=page_title AND img_media_type='BITMAP' AND cl_to IN %(titles)s AND page_id=cl_from AND page_namespace=6"
        cur.execute(sql, {
            'titles':titles
        })

        rows = cur.fetchall()
        for row in rows:
            ret.append(row['page_id'])
        return ret
 

# Initial top categories for country using SPARQL
def get_sparql_categories():
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

    sparql.setQuery("""
    SELECT DISTINCT ?item ?commonscat WHERE {
        {
            ?item (wdt:P971|wdt:P301) ?subitem .
            ?item wdt:P373 ?commonscat .
            ?subitem wdt:P17 wd:Q33
        }
        UNION
        {
            ?item wdt:P17 wd:Q33 .
            ?item wdt:P373 ?commonscat .     
        }
    }
    """)

    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results

commons_con=connect_commonsdb()
sparql_results=get_sparql_categories()
print("Sparql done")
catlevel=[set(), set(), set(), set(), set(),set(),set()]

ret=set()

n=0
todo_items=[]
print(len(sparql_results["results"]["bindings"]))
cats=set()

# Iterate over SPARQL query results
for result in sparql_results["results"]["bindings"]:
    # Access the value of 'commonscat' and clean it up
    category_title_raw = result["commonscat"]["value"]
    category_title_clean = category_title_raw.replace(" ", "_")
    category_title_encoded = category_title_clean.encode('utf-8').strip()

    # Add the cleaned and encoded title to 'todo' list
    todo_items.append(category_title_encoded)

    # If the size of 'todo' list is more than 10,000, process them in batches
    if len(todo_items) > 10000:
        categories = get_categories(todo_items)

        for category in categories:
            ret.add(category['cat_title'])

            if category['cat_subcats'] > 0:
                catlevel[0].add(category['cat_title'])

        # Reset the 'todo' list
        todo_items = []

# If there are any remaining items in the 'todo' list, process them as well
if len(todo_items) > 0:
    remaining_categories = get_categories(todo_items)

    for category in remaining_categories:
        ret.add(category['cat_title'])

        if category['cat_subcats'] > 0:
            catlevel[0].add(category['cat_title'])

rounds = [ 0,1,2 ]

for round in rounds:
    todo_items=[]
    while catlevel[round]:
        cat=catlevel[round].pop()
        todo_items.append(cat)

        if cat not in ret:
            ret.add(cat)

        if len(todo_items)>10000:
            subcats=get_subcats(todo_items)
            for subcat in subcats:
                if subcat not in ret:
                    catlevel[round+1].add(subcat)
            todo_items=[]

    if len(todo_items):
        subcats=get_subcats(todo_items)

        for subcat in subcats:
            if subcat not in ret:
                catlevel[round+1].add(subcat)
        todo_items=[]

    print(len(ret))

ret_ids=[]
todo_items=[]
while ret:
   cat=ret.pop()
   todo_items.append(cat)
   if len(todo_items)>10000:
       print(len(todo_items))
       ids=get_page_ids(todo_items)
       for id in ids:
           ret_ids.append(id)
       todo_items=[]
print(len(todo_items))
if len(todo_items):
    ids=get_page_ids(todo_items)
    for id in ids:
        ret_ids.append(id)
    todo_items=[]

print(len(set(ret_ids)))
