import yfinance as yf
import datetime
import time
import subprocess
import asyncio
from edge_tts import Communicate
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import os
import urllib.request
import stat

USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_PATH = "ivr2:/2/001.wav"
FFMPEG_PATH = "./bin/ffmpeg"

# הורדת ffmpeg אם לא קיים

def ensure_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        print("⬇️ מוריד ffmpeg...")
        os.makedirs("bin", exist_ok=True)
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        archive_path = "bin/ffmpeg.tar.xz"
        urllib.request.urlretrieve(url, archive_path)
        subprocess.run(["tar", "-xf", archive_path, "-C", "bin"])
        folder = next(f for f in os.listdir("bin") if f.startswith("ffmpeg") and os.path.isdir(os.path.join("bin", f)))
        full_path = os.path.join("bin", folder, "ffmpeg")
        os.rename(full_path, FFMPEG_PATH)
        os.chmod(FFMPEG_PATH, stat.S_IRWXU)
        print("✅ ffmpeg הותקן.")

# קבלת ברכה ושעת היום בעברית

def get_greeting():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 10:
        return "בבוקר"
    elif 10 <= hour < 12:
        return "לפני הצהריים"
    elif 12 <= hour < 14:
        return "בצהריים"
    elif 14 <= hour < 18:
        return "אחר הצהריים"
    elif 18 <= hour < 22:
        return "בערב"
    else:
        return "בלילה"

# תיאור מגמה לפי אחוז שינוי

def describe_trend(change):
    if change >= 1.5:
        return "עולה בעוצמה"
    elif change >= 0.5:
        return "מטפס"
    elif change > 0:
        return "עולה"
    elif change > -0.5:
        return "יורד בקלות"
    elif change > -1.5:
        return "יורד"
    else:
        return "צונח"

# שליפת נתוני נייר ערך

def get_data(ticker):
    ticker_obj = yf.Ticker(ticker)
    data = ticker_obj.history(period="5d")
    if len(data) < 2:
        return None
    close = data['Close']
    current = close.iloc[-1]
    prev = close.iloc[-2]
    change = ((current - prev) / prev) * 100
    max_val = close.max()
    rising_today = current >= prev
    near_high = (abs(current - max_val) / max_val < 0.03 and change >= 0)
    return current, change, rising_today, near_high

# בניית טקסט תמונת שוק

def build_market_text():
    now = datetime.datetime.now()
    greeting = get_greeting()
    hour = now.hour
    minute = now.minute
    hour_display = hour if hour <= 12 else hour - 12
    if minute == 0:
        time_text = f"{hour_display}"
    else:
        time_text = f"{hour_display} ו{minute} דקות"
    lines = [f"הנה תמונת השוק נכון לשעה {time_text} {greeting}:"]

    indices = {
        "מדד תל אביב 35": "^TA35.TA",
        "מדד תל אביב 125": "^TA125.TA",
        "מדד האס אנד פי 500": "^GSPC",
        "הנאסדק": "^IXIC",
        "דאו ג'ונס": "^DJI",
        "מדד הפחד": "^VIX",
        "הזהב": "GC=F"
    }

    for name, ticker in indices.items():
        result = get_data(ticker)
        if not result:
            continue
        value, change, rising, near_high = result
        trend = describe_trend(change)
        near_text = " ומתקרב לשיא" if near_high and rising else ""
        if name == "הזהב":
            lines.append(f"{name} {trend} ונסחר במחיר של {value:.0f} דולר לאונקיה.")
        else:
            lines.append(f"{name} {trend} ב־{abs(change):.2f} אחוזים{near_text} ועומד על {value:.0f} נקודות.")

    return "\n".join(lines)

# המרת טקסט ל־MP3

async def text_to_mp3(text, mp3_path):
    communicate = Communicate(text, voice="he-IL-AvriNeural")
    await communicate.save(mp3_path)

# המרת MP3 ל־WAV

def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        FFMPEG_PATH, "-y", "-i", mp3_path,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path
    ])

# העלאה לימות

def upload_to_yemot(wav_path):
    m = MultipartEncoder(fields={
        'token': TOKEN,
        'path': UPLOAD_PATH,
        'file': ('001.wav', open(wav_path, 'rb'), 'audio/wav')
    })
    r = requests.post("https://www.call2all.co.il/ym/api/UploadFile", data=m, headers={'Content-Type': m.content_type})
    print("📡 תגובת השרת:", r.text)

# לולאה

async def loop():
    ensure_ffmpeg()
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = build_market_text()
        print("📄 טקסט תמונת שוק:\n", text)
        await text_to_mp3(text, "market.mp3")
        convert_to_wav("market.mp3", "market.wav")
        upload_to_yemot("market.wav")
        print("✅ הסתיים! ממתין לדקה הבאה...\n")
        time.sleep(60)

asyncio.run(loop())
