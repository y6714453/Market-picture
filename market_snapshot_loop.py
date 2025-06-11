import yfinance as yf
import datetime
import time
import os
import asyncio
import subprocess
from edge_tts import Communicate
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

# פרטי ימות המשיח
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_PATH = "ivr2:/2/market.wav"

# ברכה לפי שעה

def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "בּּוקר טוֹב"
    elif 12 <= hour < 18:
        return "צהריים טובים"
    elif 18 <= hour < 22:
        return "ערב טוב"
    else:
        return "לילה טוב"

# פורמט המספר למילים מילולים

def format_number(num):
    return str(num).replace(".", " נקוּדה ")

# שליפת שניים ל-3 ימים

def is_trending(ticker):
    data = yf.Ticker(ticker).history(period="4d")
    if len(data) < 4:
        return ""
    closes = data['Close']
    diffs = closes.diff().dropna()
    if all(d > 0 for d in diffs[-3:]):
        return "ממשיך לעלות"
    elif all(d < 0 for d in diffs[-3:]):
        return "ממשיך לירידה"
    return ""

# שליפה שניים ושער נוכחי

def get_info(name, ticker, is_crypto=False):
    trending = is_trending(ticker)
    data = yf.Ticker(ticker).history(period="2d")
    if len(data) < 2:
        return ""
    prev_close = data['Close'][-2]
    current = data['Close'][-1]
    change = ((current - prev_close) / prev_close) * 100
    formatted_change = format_number(round(abs(change), 2))
    current_str = format_number(round(current, 2))

    phrase = f"{name} "
    if change > 0:
        phrase += f"{trending} עולה בשער של {formatted_change} אחוז"
    elif change < 0:
        phrase += f"{trending} יורד בשער של {formatted_change} אחוז"
    else:
        phrase += "שומר על יציבות"

    if not is_crypto and abs(change) <= 3:
        high = yf.Ticker(ticker).info.get("fiftyTwoWeekHigh", 0)
        if high:
            distance_from_high = ((high - current) / high) * 100
            if distance_from_high <= 3:
                phrase += ", ומתקרב לשיא"

    phrase += f", ועומד על {current_str}"
    phrase += " נקודות" if not is_crypto else " דולר"
    return phrase

# טקסט של תמונת השוק

def build_market_text():
    greeting = get_greeting()
    now = datetime.datetime.now().strftime("%H:%M")
    text = f"{greeting}! זואת תמונת השוק לבוקר, נכון לשעה {now}.\n\n"

    text += "בישראל:\n"
    text += get_info("מדד תל אביב מאה עשרים וחמש", "^TA125.TA") + "\n"
    text += get_info("מדד תל אביב שלושים וחמש", "^TA35.TA") + "\n\n"

    text += "בעולם:\n"
    text += get_info("מדד האס-אנד-פי חמש מאות", "^GSPC") + "\n"
    text += get_info("הנאסדק", "^IXIC") + "\n"
    text += get_info("מדד דאו ג׳ונס", "^DJI") + "\n\n"

    text += "בגזרת הקריפטו:\n"
    text += get_info("הביטקוין", "BTC-USD", is_crypto=True) + "\n"
    text += get_info("האת׳ריום", "ETH-USD", is_crypto=True) + "\n\n"

    usdils = yf.Ticker("ILS=X").history(period="2d")
    if len(usdils) >= 2:
        prev = usdils['Close'][-2]
        curr = usdils['Close'][-1]
        change = curr - prev
        trend = "מתחזק" if change > 0 else "נחלש"
        text += f"הדולר {trend} מול השקל, ונסחר בשער של {format_number(round(curr, 2))} שקל."

    return text

# המרת השמע ועלאה

def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path
    ])

# העלאה לשלוחה

def upload_to_yemot(wav_path):
    m = MultipartEncoder(
        fields={
            'token': TOKEN,
            'path': UPLOAD_PATH,
            'file': (os.path.basename(wav_path), open(wav_path, 'rb'), 'audio/wav')
        }
    )
    r = requests.post("https://www.call2all.co.il/ym/api/UploadFile", data=m, headers={'Content-Type': m.content_type})
    print("העלאה לימות:", r.text)

# הלולאה ראשית

async def loop():
    while True:
        print("\U0001F3A4 מייצר תמונת שוק...")
        text = build_market_text()
        print("\U0001F4C4 טקסט תמונת שוק:\n")
        print(text)

        print("\U0001F504 ממיר טקסט ל-MP3...")
        tts = Communicate(text=text, voice="he-IL-AvriNeural")
        await tts.save("market.mp3")

        print("\U0001F3A7 ממיר ל-WAV בפורמט ימות...")
        convert_to_wav("market.mp3", "market.wav")

        print("\U0001F4E4 מעלה לשלוחה 2...")
        upload_to_yemot("market.wav")

        await asyncio.sleep(60)

# הרצה
if __name__ == "__main__":
    asyncio.run(loop())
