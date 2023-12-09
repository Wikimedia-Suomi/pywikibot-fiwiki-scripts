# parse object-list json to cache

import json
import sqlite3

# -------- CachedFngData
class CachedFngData:
    def opencachedb(self):
        # created if it doesn't yet exist
        self.conn = sqlite3.connect("pwbfngcache.db")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS fngcache(objectid, invnum)")

    def addtocache(self, objectid, invnum):

        sqlq = "INSERT INTO fngcache(objectid, invnum) VALUES ('"+ str(objectid) + "', '"+ str(invnum) + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findbyid(self, objectid):
        sqlq = "SELECT objectid, invnum FROM fngcache WHERE objectid = '" + str(objectid) + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = res.fetchall()
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['objectid'] = row[0]
            dt['invnum'] = row[1]
            #print(dt)
            return dt

        return None

    def findbyacc(self, invnum):
        sqlq = "SELECT objectid, invnum FROM fngcache WHERE invnum = '" + str(invnum) + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = res.fetchall()
        
        #if (len(rset) == 0):
            #return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            #print(row)
            dt = dict()
            dt['objectid'] = row[0]
            dt['invnum'] = row[1]
            #print(dt)
            return dt

        return None

# ----- /CachedFngData


# ---- main()

cachedb = CachedFngData() 
cachedb.opencachedb()


file = open("objects.json")
data = json.load(file)

l = len(data)
print("len: ", str(l))

for j in data:
    if "objectId" not in j:
        continue
    if "inventoryNumber" not in j:
        continue
    oid = j["objectId"]
    acc = j["inventoryNumber"]
    
    if (oid == 0):
        continue
    if (len(acc) == 0):
        continue

    if (cachedb.findbyid(oid) == None and cachedb.findbyacc(acc) == None):
        print("Adding to cache: ", oid, acc)
        cachedb.addtocache(oid, acc)
    else:
        print("already exists in cache: ", oid, acc)

file.close()


