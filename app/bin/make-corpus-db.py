import sqlite3
import sys

dbfile = "corpus.db"
con = sqlite3.connect(dbfile)
curs = con.cursor()

f = open('corpus.sql', 'r')
curs.executescript(f.read())

con.commit()
con.close()
