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

# 🟡 פרטי ימות המשיח
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_PATH = "ivr2:/2/001.wav"
FFMPEG_PATH = "./bin/ffmpeg"

# ⬇️ הורדת ffmpeg אם לא קיים
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

# 🧠 ברכה לפי שעה
def get_greeting():
    hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).hour
    if 6 <= hour < 12:
        return "בוקר טוב"
    elif 12 <= hour < 18:
        return "צהריים טובים"
    elif 18 <= hour < 22:
        return "ערב טוב"
    else:
        return "לילה טוב"

# 🧠 שליפת נתוני מדד

def get_index_info(ticker):
    index = yf.Ticker(ticker)
    data = index.history(period="4d")
    if len(data) < 2:
        return None, None, None, None
    prev_close = data['Close'].iloc[-2]
    current = data['Close'].iloc[-1]
    change = ((current - prev_close) / prev_close) * 100
    recent_changes = [((data['Close'].iloc[i] - data['Close'].iloc[i - 1]) / data['Close'].iloc[i - 1]) * 100 for i in range(-3, 0)]
    return current, change, recent_changes, prev_close

# 🧠 פרסינג ניסוח לעלייה/ ירידה / דרמטית

def format_trend(change, recent_changes):
    avg_change = sum(recent_changes) / len(recent_changes)
    if avg_change > 0.5:
        return "ממשיך לעלות דרמטית"
    elif avg_change > 0:
        return "ממשיך לעלות"
    elif avg_change < -0.5:
        return "ממשיך לירידה דרמטית"
    elif avg_change < 0:
        return "ממשיך לירידה"
    elif change > 0:
        return "עולה"
    elif change < 0:
        return "יורד"
    else:
        return "ללא שינוי"

# 🧠 בניית הטקסט

def build_market_text():
    greeting = get_greeting()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%H:%M")
    lines = [f"{greeting}, זוא תמונת השוק נכון לשעה {now}:"]

    indices = {
        "תל אביב 125": "^TA125.TA",
        "תל אביב 35": "TA35.TA",
        "מדד האס אנד פי 500": "^GSPC",
        "הנאסדק": "^IXIC",
        "דאו גונס": "^DJI"
    }

    for name, ticker in indices.items():
        value, change, recent_changes, prev_close = get_index_info(ticker)
        if value is not None:
            trend_text = format_trend(change, recent_changes)
            percent_text = f"{abs(change):.2f}".replace(".", " נקודה ")
            suffix = "."
            if abs(change) <= 3 and abs((value - max(data['Close'])) / max(data['Close'])) < 0.03:
                suffix = " ומתקרב לשיא."
            lines.append(f"מדד {name} {trend_text} בשער של {percent_text} אחוז, ועומד על {value:.0f} נקודות{suffix}")

    usd_ils = yf.Ticker("USDILS=X")
    data = usd_ils.history(period="2d")
    if len(data) >= 2:
        prev = data['Close'].iloc[-2]
        curr = data['Close'].iloc[-1]
        diff = curr - prev
        trend = "מתחזק" if diff > 0 else "נחלש" if diff < 0 else "שומר על יציבות"
        rate = str(round(curr, 2)).replace(".", " נקודה ")
        lines.append(f"הדולר {trend} מול השקל, ונסחר בשער של {rate} שקלים.")

    return "\n".join(lines)

# 🎤 טקסט ל‏MP3
async def text_to_mp3(text, mp3_path):
    communicate = Communicate(text, voice="he-IL-AvriNeural")
    await communicate.save(mp3_path)

# 🎚️ המרת MP3 ל-WAV

def convert_to_wav(mp3_path, wav_path):
    subprocess.run([
        FFMPEG_PATH, "-y", "-i", mp3_path,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path
    ])

# ☁️ העלאה לימות

def upload_to_yemot(wav_path):
    print("⬆️ מעלה לימות...")
    try:
        m = MultipartEncoder(fields={
            'token': TOKEN,
            'path': UPLOAD_PATH,
            'file': ('001.wav', open(wav_path, 'rb'), 'audio/wav')
        })
        response = requests.post("https://www.call2all.co.il/ym/api/UploadFile", data=m, headers={'Content-Type': m.content_type})
        print("📡 תגובת השרת:", response.text)
    except Exception as e:
        print("❌ שגיאה בהעלאה:", str(e))

# 🔁 לולאה כל דקה
async def loop():
    ensure_ffmpeg()
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = build_market_text()
        print("\n📄 טקסט תמונת שוק:\n", text)
        await text_to_mp3(text, "market.mp3")
        convert_to_wav("market.mp3", "market.wav")
        upload_to_yemot("market.wav")
        print("\n✅ נשלח! מחכה לדקה הבאה...\n")
        time.sleep(60)

asyncio.run(loop())
