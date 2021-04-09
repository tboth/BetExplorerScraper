import openpyxl
import sqlite3
import time
import re
from argparse import ArgumentParser
from gooey import Gooey
from constants import DATABASE_PATH, EXPORT_PATH

'''Regex check for YYYY-MM-DD format -> some protection for the database'''
def checkDateString(dateString):
    phrase = re.compile(r"^\d\d\d\d-\d\d-\d\d$")
    result = phrase.match(dateString)
    if result:
        return True
    else: return False

''' Exporting data into an excel file
    The file includes all the records from a chosen day
    The excel file contains the name of the matches, url, odds for team1 and team2,
    over25, under25 and 2 formulas
'''

def exportDataIntoExcel(dateString):
    if checkDateString(dateString):
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()

        cursor.execute('''SELECT teams, url, team1odds, team2odds,
        over25, under25, formula1, formula2 FROM matches WHERE 
        (date=\'{}\')'''.format(dateString))
        validValues = cursor.fetchall()
        if validValues:

            fileExportName = EXPORT_PATH + "daily_report_" + dateString + time.strftime("__%Y_%m_%d_%H%M%S") + ".xlsx"
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
            print(time.strftime("%H:%M:%S -"),"Export completed for ", dateString)

            connection.close()

        else: print("No records for that day!")
    else: print("Invalid format for date!")

'''Creating a quick GUI for the program'''
@Gooey(
    program_name="Daily report"
)
def main():
    parser = ArgumentParser()
    parser.add_argument(
        "-d",
        "--date",
        required=True,
        help="Date in YYYY-MM-DD format"
    )
    args = parser.parse_args()
    exportDataIntoExcel(args.date)

if __name__ == "__main__":
    main()


