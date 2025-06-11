import yfinance as yf
import datetime
import time
import os
import subprocess
import asyncio
from edge_tts import Communicate
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

# 🟡 פרטי המערכת שלך
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"

# 🟡 פונקציה: ברכה לפי שעה
def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "בֹּקֶר טוֹב"
    elif 12 <= hour < 18:
        return "צָהֳרַיִם טוֹבִים"
    elif 18 <= hour < 22:
        return "עֶרֶב טוֹב"
    else:
        return "לַיְלָה טוֹב"

# 🟡 פונקציה: תרגום שינוי אחוזי למילים
def format_trend(change, recent_trend=None):
    base = ""
    if recent_trend == "up":
        base = "מַמְשִׁיךְ לַעֲלוֹת"
    elif recent_trend == "down":
        base = "מַמְשִׁיךְ לָרֵדֵת"
    elif change >= 1.5:
        base = "עוֹלֶה בְּצּוּרָה חַדָּה"
    elif 0.5 <= change < 1.5:
        base = "עוֹלֶה"
    elif 0 < change < 0.5:
        base = "מִטַּפֵּס"
    elif -0.5 < change <= 0:
        base = "יוֹרֵד קַלּוֹת"
    elif -1.5 < change <= -0.5:
        base = "יוֹרֵד"
    else:
        base = "צוֹנֵחַ"
    return base

# 🟡 פונקציה: שליפת נתוני מדד
def get_index_info(ticker):
    index = yf.Ticker(ticker)
    data = index.history(period="5d")
    if len(data) < 2:
        return None, None, None, None
    prev_close = data['Close'][-2]
    current = data['Close'][-1]
    change = ((current - prev_close) / prev_close) * 100
    max_value = data['Close'].max()
    distance_from_high = ((max_value - current) / max_value) * 100

    recent_trend = None
    if all(data['Close'].diff().fillna(0)[-3:] > 0):
        recent_trend = "up"
    elif all(data['Close'].diff().fillna(0)[-3:] < 0):
        recent_trend = "down"

    return current, change, format_trend(change, recent_trend), distance_from_high

# 🟡 פונקציה: המרת מספר לאותיות (פשוט)
def format_number(num):
    return str(round(num, 2)).replace(".", " נְקוּדָה ")

# 🟡 פונקציה: יצירת טקסט תמונת שוק
def generate_market_text():
    greeting = get_greeting()
    now = datetime.datetime.now().strftime("%H:%M")

    indices = {
        "מָדָד תֵּל אָבִיב מֵאָה עֶשְׂרִים וְחָמֵשׁ": "^TA125.TA",
        "מָדָד תֵּל אָבִיב שְׁלוֹשִׁים וְחָמֵשׁ": "^TA35.TA",
        "מָדָד הָאַס אֶנְד פִּי חֲמֵשׁ־מֵאוֹת": "^GSPC",
        "הַנָּאסְדָּק": "^IXIC",
        "דָּאוּ ג׳וֹנְס": "^DJI"
    }

    text = [f"{greeting}, זוֹ תְּמוּנַת הַשּׁוּק נָכוֹן לְשָׁעָה {now}:\n"]
    text.append("בְּיִשְׂרָאֵל:")
    for name in ["מָדָד תֵּל אָבִיב מֵאָה עֶשְׂרִים וְחָמֵשׁ", "מָדָד תֵּל אָבִיב שְׁלוֹשִׁים וְחָמֵשׁ"]:
        value, change, trend, dist = get_index_info(indices[name])
        if value is not None:
            line = f"{name} {trend} בְּשִׁעּוּר שֶׁל {format_number(abs(change))} אָחוּז, וְעוֹמֵד עַל {int(value)} נְקוּדוֹת."
            if dist <= 3:
                line += " מִתְקָרֵב לַשִּׂיא."
            text.append(line)

    text.append("בָּעוֹלָם:")
    for name in ["מָדָד הָאַס אֶנְד פִּי חֲמֵשׁ־מֵאוֹת", "הַנָּאסְדָּק", "דָּאוּ ג׳וֹנְס"]:
        value, change, trend, dist = get_index_info(indices[name])
        if value is not None:
            line = f"{name} {trend} בְּשִׁעּוּר שֶׁל {format_number(abs(change))} אָחוּז, וְעוֹמֵד עַל {int(value)} נְקוּדוֹת."
            if dist <= 3:
                line += " מִתְקָרֵב לַשִּׂיא."
            text.append(line)

    text.append("בְּגִזְרַת הַקְּרִיפְּטוֹ:")
    text.append("הַבִּיטְקוֹיְן נִסְחָר בְּשַׁעַר שֶׁל שִׁשִּׁים וְאַחַת אֶלֶף דּוֹלָר.")
    text.append("הָאִתֶ׳רִיוּם נִסְחָר בְּשַׁעַר שֶׁל שְׁלוֹשֶׁת אֲלָפִים וּמֵאָה דּוֹלָר.")

    text.append("הַדּוֹלָר מִתְחַזֵּק מוּל הַשֶּׁקֶל וְנִסְחָר בְּשַׁעַר שֶׁל שָׁלוֹשׁ נְקוּדָה שִׁשָּׁה שְׁקָלִים.")

    return "\n".join(text)

# 🟡 פונקציה: הפקת MP3 והמרה ל־WAV
async def text_to_speech(text):
    print("🔄 ממיר טקסט ל־MP3...")
    communicate = Communicate(text, "he-IL-HilaNeural")
    await communicate.save("market.mp3")
    print("✅ נוצר קובץ MP3: market.mp3")

    print("🎛️ ממיר ל־WAV בפורמט ימות...")
    subprocess.run(["ffmpeg", "-y", "-i", "market.mp3", "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", "market.wav"])

# 🟡 פונקציה: העלאה לימות
def upload_to_yemot():
    print("📤 מעלה לימות...")
    with open("market.wav", 'rb') as f:
        m = MultipartEncoder(fields={
            'token': TOKEN,
            'path': 'ivr2:/2/market.wav',
            'message': ('market.wav', f, 'audio/wav')
        })
        response = requests.post("https://www.call2all.co.il/ym/api/UploadMessage", data=m, headers={'Content-Type': m.content_type})
        print("🔁 תשובת ימות:", response.text)

# 🔁 לולאה ראשית כל דקה
async def loop():
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = generate_market_text()
        print("📄 טקסט תמונת שוק:\n", text)
        await text_to_speech(text)
        upload_to_yemot()
        await asyncio.sleep(60)

# 🚀 הפעלה
if __name__ == "__main__":
    asyncio.run(loop())
