import sqlite3
from constants import DATABASE_PATH

'''Dates in the database should be in YYYY-MM-DD format'''
'''Inserted at should be in HH:00 format'''
def createDatabase():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS matches (
		teams TEXT NOT NULL,
        date TEXT NOT NULL,
		url TEXT NOT NULL,
        team1odds REAL NOT NULL,
        team2odds REAL NOT NULL,
        over25 REAL NOT NULL,
        under25 REAL NOT NULL,
        formula1 REAL NOT NULL,
        formula2 REAL NOT NULL,
        team1goals INTEGER,
	    team2goals INTEGER,
        insertedAt TEXT,
        UNIQUE(teams, date));''')
    
    connection.commit()
    cursor.close()

createDatabase()
