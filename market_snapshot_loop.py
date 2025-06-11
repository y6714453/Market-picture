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

# קבלת שעת ישראל לפי API

def get_current_israel_time():
    try:
        response = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jerusalem", timeout=5)
        if response.status_code == 200:
            data = response.json()
            dt_str = data["datetime"]
            dt = datetime.datetime.fromisoformat(dt_str[:-6])
            return dt
    except Exception as e:
        print("⚠️ שגיאה בשליפת זמן מישראל:", e)

    # fallback
    return datetime.datetime.now()

# המרת שעה למחרוזת קריאה בעברית

def format_hebrew_time(dt):
    hour = dt.hour
    minute = dt.minute

    if hour >= 12:
        suffix = "בָּעֶרֶב" if hour < 18 else "בַּלַּיְלָה"
    else:
        suffix = "בַּבּוֹקֶר"

    hour_display = hour if hour <= 12 else hour - 12
    hour_text = f"שעה {hour_display}"
    if minute > 0:
        hour_text += f" ו{minute} דַּקּוֹת"
    return f"{hour_text} {suffix}"

# תיאור מגמה לפי אחוז שינוי

def describe_trend(change):
    if change >= 1.5:
        return "עוֹלֶה בְּעוֹצְמָה"
    elif change >= 0.5:
        return "מֵטָפֵּס"
    elif change > 0:
        return "עוֹלֶה"
    elif change > -0.5:
        return "יוֹרֵד קָלוֹת"
    elif change > -1.5:
        return "יוֹרֵד"
    else:
        return "צוֹנֵחַ"

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
    dt = get_current_israel_time()
    time_text = format_hebrew_time(dt)
    lines = [f"הִנֵּה תְּמוּנַת הַשּׁוּק נָכוֹן לְ{time_text}:"]

    indices = {
        "מָדָד תֵל אָבִיב 125": "^TA125.TA",
        "מָדָד תֵל אָבִיב 35": "TA35.TA",
        "מָדָד הָאֵס אֵנְד פִּי 500": "^GSPC",
        "הַנָאסְדָק": "^IXIC",
        "הָדָאוֹ ג'וֹנְס": "^DJI",
        "מָדָד הַפַּחַד": "^VIX",
        "הָזָהָב": "GC=F"
    }

    for name, ticker in indices.items():
        result = get_data(ticker)
        if not result:
            continue
        value, change, rising, near_high = result
        trend = describe_trend(change)
        near_text = " וּמִתְקָרֵב לַשִׁיא" if near_high and rising else ""
        if name == "הָזָהָב":
            lines.append(f"{name} {trend} וְנִסְחָר בְּמְחִיר שֶׁל {value:.0f} דוֹלָר לֵאוֹנְקִיָה.")
        else:
            lines.append(f"{name} {trend} ב{abs(change):.2f} אָחוּזִים{near_text} וְעוֹמֵד עַל {value:.0f} נֵקוּדוֹת.")

    return "\n".join(lines)

# המרת טקסט לMP3

async def text_to_mp3(text, mp3_path):
    communicate = Communicate(text, voice="he-IL-AvriNeural")
    await communicate.save(mp3_path)

# המרת MP3 לWAV

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
    print("📡 תְּגוּבַת הַשָּׁרָת:", r.text)

# לולאה

async def loop():
    ensure_ffmpeg()
    while True:
        print("🎤 מְיַצֵּר תְּמוּנַת שׁוּק...")
        text = build_market_text()
        print("📄 טֶקְסְט תְּמוּנַת שׁוּק:\n", text)
        await text_to_mp3(text, "market.mp3")
        convert_to_wav("market.mp3", "market.wav")
        upload_to_yemot("market.wav")
        print("✅ הִסְתַּיֵּם! מְמַתִּין לַדַּקָּה הַבָּאָה...\n")
        time.sleep(60)

asyncio.run(loop())
