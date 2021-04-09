import lxml
import openpyxl
import requests
import sqlite3
import time
from gooey import Gooey, GooeyParser
from argparse import ArgumentParser
from bs4 import BeautifulSoup as Soup
from constants import EXPORT_PATH, DATABASE_PATH, USER_AGENT, HTTP_STATUS_OK,\
    FORMULA1_MAX_VALUE, FORMULA1_MIN_VALUE, FORMULA2_MAX_VALUE, FORMULA2_MIN_VALUE

def connectToDatabase():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    return connection, cursor

def downloadResults(filename):
    connection, cursor = connectToDatabase()
    counter = 1
    session = requests.Session()

    wb = openpyxl.load_workbook(filename)
    sheet = wb.active

    '''Adding new rows to the excel file'''
    sheet["H1"] = "Hazai gol"
    sheet["I1"] = "Vendeg gol"
    sheet["J1"] = "Osszgol"
    sheet["K1"] = "Bejott"
    sheet["L1"] = "Tippelt odds"

    '''Downloading results and calculaing some formulas'''
    '''
        A match
        ->B team1 odds
        ->C team2 odds
        ->D over25
        ->E under25
        ->F formula1
        ->G formula2
        H home goals
        I guest goals
        J total goals
        K success
        L guessed odds

    '''

    while True:
        counter += 1
        matchFormula = sheet.cell(row=counter, column=1)
        if not matchFormula.value: break

        url = matchFormula.value.split(",")[0][12:-1]
        '''This is just for the user to see that something is happening'''
        print("=>", url)

        try:
            response = session.get(url, headers = USER_AGENT, timeout = 2)
        
            '''Extracting the result from the URL'''
            if response.status_code == HTTP_STATUS_OK:
                soup = Soup(response.content, "lxml")
                raw_results = str(soup.select_one("#js-partial").text).replace(" ","")[1:-1].split(",")
                team1Goals = int(raw_results[0].split(":")[0]) + int(raw_results[1].split(":")[0])
                team2Goals = int(raw_results[0].split(":")[1]) + int(raw_results[1].split(":")[1])
                totalGoals = team1Goals + team2Goals
                cursor.execute("UPDATE matches SET team1goals={}, team2goals={}  WHERE(url=\'{}\')".format(team1Goals, team2Goals, url))

                sheet["H" + str(counter)] = team1Goals
                sheet["I" + str(counter)] = team2Goals
                sheet["J" + str(counter)] = totalGoals

                team1Odds = float(sheet["B" + str(counter)].value)
                team2Odds = float(sheet["C" + str(counter)].value)
                over25 = float(sheet["D" + str(counter)].value)
                under25 = float(sheet["E" + str(counter)].value)
                formula1 = float(sheet["F" + str(counter)].value)
                formula2 = float(sheet["G" + str(counter)].value)

                '''If the 1 <= formula1 <= 1.5 then the bet should be over25 for the particular match,
                   otherwise the bet should be under25
                '''
                if formula1 < FORMULA1_MAX_VALUE:
                    sheet["L" + str(counter)] = over25
                elif formula2 < FORMULA2_MAX_VALUE:
                    sheet["L" + str(counter)] = under25

                '''Chceking whether the bet is won(1) or lost(0)'''
                if (FORMULA1_MIN_VALUE <= formula1 <= FORMULA1_MAX_VALUE and totalGoals > 2) or \
                    (FORMULA2_MIN_VALUE <= formula2 <= FORMULA2_MAX_VALUE and totalGoals < 3):
                    sheet["K" + str(counter)] = 1
                else:
                    sheet["K" + str(counter)] = 0

                time.sleep(0.5)

        except TimeoutError: continue
        except ValueError: continue
        except ConnectionError: continue
        except AttributeError: continue
        except IndexError: continue

    wb.save(filename)
    connection.commit()
    connection.close()
    session.close()

'''Quick GUI'''
@Gooey(
    program_name="Download match results"
)
def main():
    parser = GooeyParser()
    chooser = parser.add_argument_group("Download match results")
    chooser.add_argument(
        "-f",
        "--file",
        required=True,
        help="Select a file. Make sure the selected file is not open during the process.",
        widget="FileChooser",
        gooey_options=dict(wildcard = "*.xlsx", defualt_dir = EXPORT_PATH)
    )

    args = parser.parse_args()
    downloadResults(args.file)

if __name__ == "__main__":
    main()

