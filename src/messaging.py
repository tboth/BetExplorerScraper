import requests
import time
from constants import TELEGRAM_BOT_ID, TELEGRAM_CHAT_ID, HTTP_STATUS_OK

def sendTelegramMessage(type, url):
    response = requests.post("https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={} {}".format(TELEGRAM_BOT_ID, TELEGRAM_CHAT_ID, type, url))
    if response.status_code == HTTP_STATUS_OK:
        print("SENT:",url)
    else:
        time.sleep(0.5)
        response = requests.post("https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={} {}".format(TELEGRAM_BOT_ID, TELEGRAM_CHAT_ID, type, url))
        if response.status_code == HTTP_STATUS_OK:
            print("RETRY SUCCESSFUL:",url)
        else:
            print("NOT SENT:",url)  