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
        return "בַּבֹּקֶר"
    elif 10 <= hour < 12:
        return "לִפְנֵי הַצָּהֳרַיִם"
    elif 12 <= hour < 14:
        return "בַּצָּהֳרַיִם"
    elif 14 <= hour < 18:
        return "אַחַר הַצָּהֳרַיִם"
    elif 18 <= hour < 22:
        return "בָּעֶרֶב"
    else:
        return "בַּלַּיְלָה"

# תיאור מגמה לפי אחוז שינוי

def describe_trend(change):
    if change >= 1.5:
        return "עוֹלֶה בֵּעוֹצְמָה"
    elif change >= 0.5:
        return "עוֹלֶה"
    elif change > 0:
        return "מִטְפֵּס"
    elif change > -0.5:
        return "יוֹרֵד בְּקַלּוּת"
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

# בדיקת האם המסחר פתוח

def is_market_open():
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    if weekday >= 5:
        return False
    if 16 <= hour < 23 or (hour == 23 and minute == 0):
        return True
    return False

# בניית טקסט תמונת שוק

def build_market_text():
    now = datetime.datetime.now()
    greeting = get_greeting()
    hour = now.hour
    minute = now.minute
    hour_display = hour if hour <= 12 else hour - 12
    time_text = f"{hour_display} ו{minute} דַּקּוֹת"
    lines = [f"הִנֵּה תְּמוּנַת הַשּׁוּק נָכוֹן לְשָׁעָה {time_text} {greeting}:"]

    indices = {
        "מָדַד תֵּל אָבִיב 35": "^TA35.TA",
        "מָדַד תֵּל אָבִיב 125": "^TA125.TA",
        "מָדַד הָאָס אֶנְד פִּי 500": "^GSPC",
        "הַנָּאסְדָּק": "^IXIC",
        "דָּאוֹ גּ'וֹנְס": "^DJI",
        "מָדַד הַפַּחַד": "^VIX",
        "הַזָּהָב": "GC=F"
    }

    for name, ticker in indices.items():
        result = get_data(ticker)
        if not result:
            continue
        value, change, rising, near_high = result
        trend = describe_trend(change)
        near_text = " וּמִתְקָרֵב לַשִּׂיא" if near_high and rising else ""
        if name == "הַזָּהָב":
            lines.append(f"{name} {trend} וְנִסְחָר בְּמְחִיר שֶׁל {value:.0f} דּוֹלָר לָאוּנְקִיָּה.")
        else:
            lines.append(f"{name} {trend} בְּ{abs(change):.2f} אָחוּז{near_text} וְעוֹמֵד עַל {value:.0f} נְקֻדּוֹת.")

    # מניות וול סטריט
    stocks = {
        "אַפֶּל": "AAPL",
        "אֵנְבִידְיָה": "NVDA",
        "אַמָּזוֹן": "AMZN",
        "טֶסְלָה": "TSLA",
        "מַיְקְרוֹסוֹפְט": "MSFT",
        "גוּגֵל": "GOOG"
    }
    changes = []
    for name, symbol in stocks.items():
        result = get_data(symbol)
        if not result:
            continue
        value, change, *_ = result
        changes.append((name, value, change))

    if changes:
        rising = [c for c in changes if c[2] > 0]
        falling = [c for c in changes if c[2] < 0]
        majority = "עוֹלוֹת" if len(rising) > len(falling) else "יוֹרְדוֹת"
        trend_general = "נִרְשְׁמוּ עָלִיּוֹת חַדּוֹת" if sum(c[2] for c in changes)/len(changes) > 1 else f"נִרְשְׁמוּ {majority}"
        lines.append(f"בְּווֹל סְטְרִיט {trend_general}:")
        group = rising if majority == "עוֹלוֹת" else falling
        for name, value, change in group:
            line = f"{name} {'עוֹלָה' if change > 0 else 'יוֹרֶדֶת'} בְּ{abs(change):.2f}%"
            if abs(change) > 1:
                line += f" וְנִסְחֶרֶת כָּעֵת בֵּשוֹבִי שֶׁל {value:.0f} דּוֹלָר"
            lines.append(line + ".")
        other_group = falling if majority == "עוֹלוֹת" else rising
        if other_group:
            name, value, change = other_group[0]
            lines.append(f"וְכָל זֹאת בְּעוֹד {name} {'עוֹלָה' if change > 0 else 'יוֹרֶדֶת'} בְּ{abs(change):.2f}%.")

    # קריפטו
    btc = get_data("BTC-USD")
    eth = get_data("ETH-USD")
    if btc and eth:
        _, btc_change, _, _ = btc
        _, eth_change, _, _ = eth
        avg_change = (btc_change + eth_change) / 2
        crypto_trend = describe_trend(avg_change)
        lines.append(f"בְּגִזְרַת הַקְּרִיפְּטוֹ נִרְשָׁמוֹת {crypto_trend}:")
        lines.append(f"הַבִּיטְקוֹיְן נִסְחָר בְּשַׁעַר שֶׁל {btc[0]:,.0f} דּוֹלָר.")
        lines.append(f"הָאֶתֶ'רְיוּם נִסְחָר בְּשַׁעַר שֶׁל {eth[0]:,.0f} דּוֹלָר.")

    # דולר
    usd = get_data("USDILS=X")
    if usd:
        curr, change, _, _ = usd
        trend = "מִתְחַזֵּק" if change > 0 else "נֶחְלָשׁ" if change < 0 else "שׁוֹמֵר עַל יַצִּיבוּת"
        lines.append(f"הַדּוֹלָר {trend} מוּל הַשֶּׁקֶל וְנִסְחָר בְּשַׁעַר שֶׁל {curr:.2f} שְׁקָלִים.")

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
