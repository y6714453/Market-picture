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

# 🧠 פורמט שינוי אחוזי למילים

def format_trend(change):
    if change >= 1.5:
        return "ממשיך לעלות דרמטית"
    elif 0.5 <= change < 1.5:
        return "ממשיך לעלות"
    elif 0 < change < 0.5:
        return "ממשיך לטפס"
    elif -0.5 < change <= 0:
        return "מרד קלות"
    elif -1.5 < change <= -0.5:
        return "ממשיך לירידה"
    else:
        return "ממשיך לירידה דרמטית"

# 🧠 שליפת נתוני שוק

def get_index_info(ticker):
    index = yf.Ticker(ticker)
    data = index.history(period="5d")
    if len(data) < 4:
        return None, None, None, None
    prev = data['Close'].iloc[-2]
    curr = data['Close'].iloc[-1]
    change = ((curr - prev) / prev) * 100
    last3 = data['Close'].iloc[-3:]
    trend_past = ""
    if all(last3[i] < last3[i + 1] for i in range(2)):
        if change > 1:
            trend_past = "ממשיך לעלות בצורה גבוה"
        else:
            trend_past = "ממשיך לעלות"
    elif all(last3[i] > last3[i + 1] for i in range(2)):
        if abs(change) > 1:
            trend_past = "ממשיך לירידה דרמטית"
        else:
            trend_past = "ממשיך לירידה"
    else:
        trend_past = format_trend(change)
    near_high = abs((curr - max(data['Close'])) / max(data['Close'])) < 0.03
    return curr, change, trend_past, near_high

# 🧠 בניית הטקסט

def build_market_text():
    greeting = get_greeting()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%H:%M")
    lines = [f"{greeting}, זוא תמונת השוק נכון לשעה {now}:"]

    indices = {
        "מדד תל אביב 125": "^TA125.TA",
        "מדד האס אנד פי 500": "^GSPC",
        "מדד הנאסדק": "^IXIC",
        "דאו ג'ונס": "^DJI"
    }

    lines.append("בישראל:")
    name = "מדד תל אביב 125"
    value, change, trend, near_high = get_index_info(indices[name])
    if value:
        line = f"{name} {trend} בשעור של {abs(change):.2f}‏% ועומד על {value:.0f} נקודות."
        if near_high:
            line += " ומתקרב לשיא."
        lines.append(line)

    lines.append("בעולם:")
    for name, ticker in list(indices.items())[1:]:
        value, change, trend, near_high = get_index_info(ticker)
        if value:
            line = f"{name} {trend} בשעור של {abs(change):.2f}‏% ועומד על {value:.0f} נקודות."
            if near_high:
                line += " ומתקרב לשיא."
            lines.append(line)

    # ✳️ קריפטו ודולר
    usd = yf.Ticker("USDILS=X")
    data = usd.history(period="2d")
    if len(data) >= 2:
        prev, curr = data['Close'].iloc[-2], data['Close'].iloc[-1]
        if curr > prev:
            trend = "מתחזק"
        elif curr < prev:
            trend = "נחלש"
        else:
            trend = "שומר על יציבות"
        lines.append(f"הדולר {trend} מול השקל ונסחר בשער של {curr:.2f} שקלים.")

    return "\n".join(lines)

# 🎤 המרת MP3

async def text_to_mp3(text, mp3_path):
    print("🔄 ממיר טקסט לקובץ MP3...")
    communicate = Communicate(text, voice="he-IL-AvriNeural")
    await communicate.save(mp3_path)
    print("✅ נוצר MP3:", mp3_path)

# ♪ מי MP3 לפורמט WAV

def convert_to_wav(mp3_path, wav_path):
    subprocess.run([FFMPEG_PATH, "-y", "-i", mp3_path, "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path])

# ☁️ העלאה לימות

def upload_to_yemot(wav_path):
    print("☁️ מעלה לימות...")
    m = MultipartEncoder(fields={
        'token': TOKEN,
        'path': UPLOAD_PATH,
        'file': ('001.wav', open(wav_path, 'rb'), 'audio/wav')
    })
    r = requests.post("https://www.call2all.co.il/ym/api/UploadFile", data=m, headers={'Content-Type': m.content_type})
    print("📱 תגובת השרת:", r.text)

# ▶️ לולאת הפעלה

async def loop():
    ensure_ffmpeg()
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = build_market_text()
        print("📄 נוסח:", text)
        await text_to_mp3(text, "market.mp3")
        convert_to_wav("market.mp3", "market.wav")
        upload_to_yemot("market.wav")
        time.sleep(60)

asyncio.run(loop())
