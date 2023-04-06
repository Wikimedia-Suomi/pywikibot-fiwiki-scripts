# Script connects to WMF Wikimedia database replicas from local computer via ssh port forward.

# Prerequisites

# Request user to wmflabs
# https://wikitech.wikimedia.org/wiki/Portal:Toolforge/Quickstart

# Create port forwarding: 3306:fiwiki.web.db.svc.wikimedia.cloud:3306
# ssh -L 3306:fiwiki.web.db.svc.wikimedia.cloud:3306 zache-tool@login.toolforge.org

# Copy replica password file to local file
# scp zache-tool@login.toolforge.org:~/replica.my.cnf ./wikitech_replica.my.cnf

# Run application
# python mydatabase_local.py

#/usr/bin/python3

import os
import configparser
import pymysql

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
  db='fiwiki_p',
  charset='utf8',
  cursorclass=pymysql.cursors.DictCursor)

try:
   with fiwiki_con.cursor() as cur:
      cur.execute('SELECT rc_title, rc_user_text FROM recentchanges_compat WHERE rc_namespace=0 LIMIT 10')
      rows = cur.fetchall()
      for row in rows:
         print(row)

finally:
   fiwiki_con.close()
