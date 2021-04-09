import time
import sqlite3
import requests
import lxml
import os
import openpyxl
import json
from bs4 import BeautifulSoup
from constants import *
from messaging import sendTelegramMessage

def getCurrentHour():
    return time.strftime("%H") + "-00"

def getCurrentDate():
    return time.strftime("%Y-%m-%d")

''' this function is for filtering the possible times
    possible times - from current hour-00 minutes to current hour + 2 hours + 55 minutes
    with granularity of 5 minutes
'''
def getAllPossibleTimes(): 
    currentHour = int(time.strftime("%H"))
    baseDate = time.strftime("%#d,%#m,%Y,")
    possibleTimes = []
    for i in range(3):
        for j in range(0,60,5):
            possibleTimes.append(baseDate + str(currentHour + i) + "," + (2 - len(str(j))) * "0" + str(j))

    return possibleTimes


''' creating temporary database in memory '''
def createDatabase():
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()
    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS matches (
		teams TEXT NOT NULL,
		url TEXT NOT NULL,
        team1odds REAL NOT NULL,
        team2odds REAL NOT NULL,
        over25 REAL NOT NULL,
        under25 REAL NOT NULL,
        formula1 REAL NOT NULL,
        formula2 REAL NOT NULL)''')
    
    return connection, cursor


'''Filtering data from the temporary database'''
def filterData(cursor):
    cursor.execute(''' 
    SELECT * FROM matches WHERE 
    (formula1 > {} AND formula1 < {}) OR (formula2 > {} AND formula2 < {})'''.format(
        FORMULA1_MIN_VALUE, FORMULA1_MAX_VALUE, FORMULA2_MIN_VALUE, FORMULA2_MAX_VALUE
    ))
    validValues = cursor.fetchall()
    return validValues

'''H values filtering'''
def filterDataForSending(cursor):
    cursor.execute(''' 
    SELECT url FROM matches WHERE 
    (formula1 >= {} AND formula1 <= {}) AND date=\'{}\' and insertedAt=\'{}\';'''.format(
        METHOD_1_MINIMUM, METHOD_1_MAXIMUM, getCurrentDate(), getCurrentHour()))
    validValues = cursor.fetchall()
    return validValues


'''
sending filtered messages to Telegram 
'''
def messagingService(cursor):
    validValues = filterDataForSending(cursor)
    if validValues:
        for row in validValues:
            sendTelegramMessage("H", row[0])


''' Saving the new matches into the database. The database contains the earliest occurence of every match
    -> it means that if a particular match was selected more times, just the earliest occurence is written
    into the database. This is why there is an IGNORE statement in the query.
'''
def saveIntoDatabase(validValues):
    if validValues:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()

        for x in validValues:
            cursor.execute('''INSERT OR IGNORE INTO matches(teams,date,url,team1odds, team2odds, over25, under25, formula1, formula2, insertedAt) 
            VALUES (\'{}\',\'{}\',\'{}\',{},{},{},{},{},{},\'{}\');'''.format(x[0], getCurrentDate(), x[1], x[2], x[3], x[4], x[5], x[6], x[7], getCurrentHour()))

        connection.commit()
        #messagingService(cursor)
        connection.close()

    else:
        print("Nothing to write into the database!")


'''Exporting currently downloaded matches into and excel file'''
def exportDataIntoExcel(validValues):
    if validValues:
        for x in validValues:
            print(x)

        #fileExportName = os.getcwd()[:-3] + "export\\" + time.strftime("%Y_%m_%d_%H%M%S") + ".xlsx"
        fileExportName = EXPORT_PATH + time.strftime("%Y_%m_%d_%H%M%S") + ".xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        sheet['A1'] = "Match"
        sheet['B1'] = "Team1"
        sheet['C1'] = "Team2"
        sheet['D1'] = "Over25"
        sheet['E1'] = "Under25"
        sheet['F1'] = "(H/V)*O25"
        sheet['G1'] = "(V/H)*U25"

        counter = 2

        for row in validValues:
            sheet['A' + str(counter)] = "=HYPERLINK(\"{}\",\"{}\")".format(row[1],row[0])
            sheet['B' + str(counter)] = row[2]
            sheet['C' + str(counter)] = row[3]
            sheet['D' + str(counter)] = row[4]
            sheet['E' + str(counter)] = row[5]
            sheet['F' + str(counter)] = row[6]
            sheet['G' + str(counter)] = row[7]

            counter += 1

        workbook.save(fileExportName)

    else: print("No matches with valid ranges!")


'''(H/V)*O25'''
def formula1(team1, team2, over25):
    return (team1 / team2) * over25

'''(V/H)*U25'''
def formula2(team1, team2, under25):
    return (team2 / team1) * under25

if __name__ == "__main__":
    connection, cursor = createDatabase()
    response = requests.get(URL, headers = USER_AGENT)

    ''' Getting the full match list and extracting matches which begin at the current hour, +1, +2 hours, contains odds and all
        the odds are above 1.5
    '''
    print(time.strftime("%Y_%m_%d %H:%M:%S"))
    if response.status_code == HTTP_STATUS_OK:
        site = BeautifulSoup(response.content, "lxml")
        mainTable = site.find(class_ = "table-main js-nrbanner-t")
        matches = mainTable.findAll("tr", {"data-def": "1", "data-dt" : getAllPossibleTimes()})
        
        for match in matches:
            currentMatchUrl = "https://www.betexplorer.com/" + match.find("td", class_="table-main__tt").a["href"]
            matchName = match.find("td", class_="table-main__tt").a.text
            try:
                oddsContainers = match.find_all("td", class_ = "table-main__odds")
                print("----------------------------")
                print(matchName)

                team1Odds = float(oddsContainers[0].a["data-odd"])
                team2Odds = float(oddsContainers[2].a["data-odd"])

                print(team1Odds,team2Odds)

                if team1Odds > TEAM1_MIN_ODDS and team2Odds > TEAM2_MIN_ODDS:
                    currentHeader = {"User-Agent" : UA, "Referer" : currentMatchUrl}

                    ''' If the odds are above 1.5 then the over25 and under25 should be extracted
                        For this a new HTTP request is needed. This requests' response contains a HTML table
                        from which the over25 and under25 odds can be extracted  
                    '''
                    currentResponse = requests.get("https://www.betexplorer.com/match-odds/" + currentMatchUrl.split("/")[-2] + "/0/ou/", headers = currentHeader, timeout=2.00)
                    if currentResponse.status_code == HTTP_STATUS_OK:
                        currentSite = BeautifulSoup(json.loads(currentResponse.content)['odds'], "lxml")
                        counter = 3
                        currentElement = None
                        found = False

                        ''' First we look for a row which contains the 2.5 number in the main__doubleparamater row. This is achievied via iteration.
                            When the 2.5 value is found, we need the current component's parent's parent, ie. the whole table.
                            Then from the table's footer the required values can be easily extracted.
                        '''
                        while not found and counter < 10:
                            currentElement = currentSite.select_one("#sortable-" + str(counter) + " > tbody > tr:nth-child(1) > td.table-main__doubleparameter")
                            found = currentElement.text == "2.5"
                            counter += 1
                                
                        if found:
                            parentElement = currentElement.parent.parent.parent
                            tableFoot = parentElement.find("tfoot")
                            dataTags = tableFoot.find_all("td", class_="table-main__detail-odds")
                            over25 = float(dataTags[0]["data-odd"])
                            under25 = float(dataTags[1]["data-odd"])
                            print(over25, under25)
                            if over25 > OVER25_MIN_ODDS and under25 > UNDER25_MIN_ODDS:

                                '''Writing the new match into the temporary database'''
                                cursor.execute('''INSERT INTO 
                                matches(teams, url, team1odds, team2odds, over25, under25, formula1, formula2) 
                                VALUES (\'{}\',\'{}\',{},{},{},{},{},{});'''.format(
                                    matchName.replace("'","`"), currentMatchUrl, team1Odds, team2Odds, over25, under25, 
                                    formula1(team1Odds,team2Odds,over25), formula2(team1Odds, team2Odds, under25)
                                ))
                                connection.commit()

                time.sleep(0.5)

            except ValueError:
                continue

            except IndexError:
                continue

            except TypeError:
                continue

            except AttributeError:
                continue

            except requests.Timeout:
                continue


    validValues = filterData(cursor)
    exportDataIntoExcel(validValues)
    saveIntoDatabase(validValues)

    connection.close()
