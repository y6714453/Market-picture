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
        return "מְזַנֵּק"
    elif change >= 0.5:
        return "עוֹלֶה"
    elif change > 0:
        return "מִטְפֵּס"
    elif change > -0.5:
        return "יוֹרֵד קַלּוֹת"
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
    now = datetime.datetime.now()
    greeting = get_greeting()
    hour = now.hour % 12 or 12
    minute = now.strftime('%M')
    time_text = f"{hour} ו{minute} דַּקּוֹת"
    lines = [f"הִנֵּה תְּמוּנַת הַשּׁוּק – נְכוֹן לְשָׁעָה {time_text} {greeting}:"]

    indices = {
        "מַדַּד תֵּל אָבִיב שְׁלוֹשִׁים וְחָמֵשׁ": "^TA35.TA",
        "מַדַּד תֵּל אָבִיב מֵאָה וְעֶשְׂרִים וְחָמֵשׁ": "^TA125.TA",
        "מַדַּד הָאַס אַנְד פִּי חֲמֵשׁ מֵאוֹת": "^GSPC",
        "הַנָּאסְדָּ"ק": "^IXIC",
        "דַּאוּ גּ'וֹנְס": "^DJI",
        "מַדַּד הַפַּחַד": "^VIX",
        "הַזָּהָב": "GC=F"
    }

    for name, ticker in indices.items():
        result = get_data(ticker)
        if not result:
            continue
        value, change, rising, near_high = result
        trend = describe_trend(change)
        near_text = " וּמִתְקָרֵב לַשִּׂיא" if near_high and change >= 0 else ""
        if name == "הַזָּהָב":
            lines.append(f"{name} {trend} וְנִסְחָר בְּמְחִיר שֶׁל {value:.0f} דּוֹלָר לְאוּנְקִיָּה.")
        else:
            lines.append(f"{name} {trend} בְּ{abs(change):.2f} אָחוּזִים{near_text}, וְעוֹמֵד עַכְשָׁו עַל {value:.0f} נְקֻדּוֹת.")

    # מניות בולטות
    stocks = {
        "אַפֵּל": "AAPL",
        "אַנְבִּידִיָּה": "NVDA",
        "אַמָּזוֹן": "AMZN",
        "טֶסְלָה": "TSLA",
        "מַיְקְרוֹסוֹפְט": "MSFT",
        "גוּגְל": "GOOG"
    }
    lines.append("עוֹד עַל מַנְיוֹת בּוֹלְטוֹת:")
    for name, ticker in stocks.items():
        result = get_data(ticker)
        if not result:
            continue
        value, change, _, _ = result
        trend = describe_trend(change)
        if abs(change) >= 1:
            lines.append(f"{name} {trend} בְּ{abs(change):.2f} אָחוּזִים, וְנִסְחֶרֶת עַכְשָׁו בְּשֶׁוְויִי שֶׁל {value:.2f} דּוֹלָר.")
        else:
            lines.append(f"{name} {trend} בְּ{abs(change):.2f} אָחוּזִים.")

    # קריפטו
    btc = get_data("BTC-USD")
    eth = get_data("ETH-USD")
    if btc and eth:
        _, btc_change, _, _ = btc
        _, eth_change, _, _ = eth
        avg_change = (btc_change + eth_change) / 2
        crypto_trend = describe_trend(avg_change)
        lines.append(f"בִּגְזֶרֶת הַקְּרִיפְּטוֹ – נִרְשָׁמוֹת {crypto_trend}:")
        lines.append(f"הַבִּיטְקוֹיְן נִסְחָר בִּשְׁעַר שֶׁל {btc[0]:,.0f} דּוֹלָר.")
        lines.append(f"הָאֵתֶ'רְיוּם נִסְחָר בִּשְׁעַר שֶׁל {eth[0]:,.0f} דּוֹלָר.")

    # דולר
    usd = get_data("USDILS=X")
    if usd:
        curr, change, _, _ = usd
        trend = "מִתְחַזֵּק" if change > 0 else "נֶחְלָשׁ" if change < 0 else "שׁוֹמֵר עַל יַצִּיבוּת"
        lines.append(f"הַדּוֹלָר {trend} מוּל הַשֶּׁקֶל וְנִסְחָר בִּשְׁעַר שֶׁל {curr:.2f} שֶׁקֶל.")

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
        print("✅ הסתיים! מְחַכֶּה לַדַּקָּה הַבָּאָה...\n")
        time.sleep(60)

asyncio.run(loop())
