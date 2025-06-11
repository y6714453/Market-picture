import yfinance as yf
import datetime
import time
import subprocess
import asyncio
from edge_tts import Communicate
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

# 🟡 פרטי ימות המשיח
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_PATH = "ivr2:/2/001.wav"  # שלוחה 2 בתפריט הראשי

# 🤠 ברכה לפי שעה
def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "בוקר טוב"
    elif 12 <= hour < 18:
        return "צהריים טובים"
    elif 18 <= hour < 22:
        return "ערב טוב"
    else:
        return "לילה טוב"

# 🤠 תרגום שינוי אחוזי למילים
def format_trend(change):
    if change >= 1.5:
        return "זינק"
    elif 0.5 <= change < 1.5:
        return "עלה"
    elif 0 < change < 0.5:
        return "טיפס"
    elif -0.5 < change <= 0:
        return "ירד קלות"
    elif -1.5 < change <= -0.5:
        return "ירד"
    else:
        return "צנח"

# 🤠 שליפת נתוני מדד
def get_index_info(ticker):
    index = yf.Ticker(ticker)
    data = index.history(period="2d")
    if len(data) < 2:
        return None, None, None
    prev_close = data['Close'][-2]
    current = data['Close'][-1]
    change = ((current - prev_close) / prev_close) * 100
    return current, change, format_trend(change)

# 🤠 בניית טקסט תמונת השוק
def build_market_text():
    greeting = get_greeting()
    now = datetime.datetime.now().strftime("%H:%M")

    indices = {
        "ת״א 125": "^TA125.TA",
        "ת״א 35": "^TA35.TA",
        "S&P 500": "^GSPC",
        "נאסד״ק": "^IXIC",
        "דאו ג׳ונס": "^DJI"
    }

    lines = [f"{greeting}! הנה תמונת השוק נכון לשעה {now}:"]

    for name, ticker in indices.items():
        value, change, trend = get_index_info(ticker)
        if value is not None:
            lines.append(f"מדד {name} {trend} בּ‏{abs(change):.2f} אחוזים, ועומד על {value:.0f} נקודות.")
        else:
            lines.append(f"לא ניתן למשוך נתונים עבור {name}.")

    return "\n".join(lines)

# 🎙️ טקסט לַMP3 עם edge-tts
async def text_to_mp3(text, mp3_path):
    communicate = Communicate(text, voice="he-IL-AvriNeural")
    await communicate.save(mp3_path)

# 🎹 המרת MP3 ל-WAV
def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path
    ])

# ☁️ העלאה לימות המשיח
def upload_to_yemot(wav_path):
    m = MultipartEncoder(fields={
        'token': TOKEN,
        'path': UPLOAD_PATH,
        'file': ('001.wav', open(wav_path, 'rb'), 'audio/wav')
    })
    response = requests.post("https://www.call2all.co.il/ym/api/UploadFile", data=m, headers={'Content-Type': m.content_type})
    print("⬆️ העלאה ליקון ימות:", response.text)

# 🔁 לולאה כל דקה
async def loop():
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = build_market_text()
        await text_to_mp3(text, "market.mp3")
        convert_to_wav("market.mp3", "market.wav")
        upload_to_yemot("market.wav")
        print("✅ הסתיים! מחכה לדקה הבאה...\n")
        time.sleep(60)

# ▶️ הרצת הלולאה
asyncio.run(loop())
