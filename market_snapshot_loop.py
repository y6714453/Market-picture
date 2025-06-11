import asyncio
import os
import datetime
import pytz
import yfinance as yf
import edge_tts
import subprocess
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

# פרטי הגישה למערכת ימות המשיח
USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"
UPLOAD_URL = "https://www.call2all.co.il/ym/api/UploadFile"
UPLOAD_PATH = "ivr2:/2/market.wav"

# המרות מספרים
def מספר_לטקסט(num):
    return str(num).replace('.', ' נְקוּדָה ')

# המרת שעה
def שעה_לטקסט():
    tz = pytz.timezone('Asia/Jerusalem')
    now = datetime.datetime.now(tz)
    return now.strftime("%H נְקוּדָה %M")

# יצירת טקסט תמונת שוק
async def צור_טקסט():
    טקסט = f"לַיְלָה טוֹב, זוֹ תְּמוּנַת הַשּׁוּק נָכוֹן לְשָׁעָה {שעה_לטקסט()}:\n\n"

    # מדדים ישראליים
    טקסט += "בְּיִשְׂרָאֵל:\n"
    ta125 = yf.Ticker("TA125.TA").history(period="5d")
    ta35 = yf.Ticker("TA35.TA").history(period="5d")

    for שם, מדד in [("תֵּל אָבִיב מֵאָה עֶשְׂרִים וְחָמֵשׁ", ta125), ("תֵּל אָבִיב שְׁלוֹשִׁים וְחָמֵשׁ", ta35)]:
        if len(מדד) >= 2:
            שינוי = round((מדד['Close'][-1] - מדד['Close'][-2]) / מדד['Close'][-2] * 100, 2)
            ערך = round(מדד['Close'][-1])
            מגמה = "עוֹלֶה" if שינוי > 0 else "יוֹרֵד" if שינוי < 0 else "לְלֹא שִׁינּוּי"
            טקסט += f"מָדָד {שם} {מגמה} בְּשִׁעּוּר שֶׁל {מספר_לטקסט(abs(שינוי))} אָחוּז, וְעוֹמֵד עַל {מספר_לטקסט(ערך)} נְקוּדוֹת.\n"

    # מדדים אמריקאיים
    טקסט += "\nבָּעוֹלָם:\n"
    for סמל, שם_מדד in [("^GSPC", "הָאַס אֶנְד פִּי"), ("^IXIC", "הַנָּאסְדָּק"), ("^DJI", "דָּאוּ ג'וֹנְס")]:
        מדד = yf.Ticker(סמל).history(period="5d")
        if len(מדד) >= 2:
            שינוי = round((מדד['Close'][-1] - מדד['Close'][-2]) / מדד['Close'][-2] * 100, 2)
            ערך = round(מדד['Close'][-1])
            מגמה = "עוֹלֶה" if שינוי > 0 else "יוֹרֵד" if שינוי < 0 else "לְלֹא שִׁינּוּי"
            טקסט += f"מָדָד {שם_מדד} {מגמה} בְּשִׁעּוּר שֶׁל {מספר_לטקסט(abs(שינוי))} אָחוּז, וְעוֹמֵד עַל {מספר_לטקסט(ערך)} נְקוּדוֹת.\n"

    # מטבעות קריפטו
    טקסט += "\nבְּגִזְרַת הַקְּרִיפְּטוֹ:\n"
    for סמל, שם in [("BTC-USD", "הַבִּיטְקוֹיְן"), ("ETH-USD", "הָאִתֶרִיוּם")]:
        מטבע = yf.Ticker(סמל).history(period="1d")
        if not מטבע.empty:
            ערך = round(מטבע['Close'][-1])
            טקסט += f"{שם} נִסְחָר בְּשַׁעַר שֶׁל {מספר_לטקסט(ערך)} דּוֹלָר.\n"

    # דולר לשקל
    דולר = yf.Ticker("USDILS=X").history(period="1d")
    if not דולר.empty:
        שער = round(דולר['Close'][-1], 2)
        שינוי = שער - דולר['Close'][0]
        מגמה = "מִתְחַזֵּק" if שינוי > 0 else "נֶחְלָשׁ"
        טקסט += f"\nהַדּוֹלָר {מגמה} מוּל הַשֶּׁקֶל וְנִסְחָר בְּשַׁעַר שֶׁל {מספר_לטקסט(שער)} שְׁקָלִים."

    return טקסט

# שמירת קובץ קול
async def שמור_קובץ(text):
    tts = edge_tts.Communicate(text, voice="he-IL-AvriNeural")
    await tts.save("market.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", "market.mp3", "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", "market.wav"])

# העלאה לימות
def העלה_לימות():
    print("📤 מעלה קובץ לימות המשיח לשלוחה 2...")
    with open("market.wav", 'rb') as f:
        m = MultipartEncoder(fields={
            'token': TOKEN,
            'path': UPLOAD_PATH,
            'file': ('market.wav', f, 'audio/wav')
        })
        r = requests.post(UPLOAD_URL, data=m, headers={'Content-Type': m.content_type})
        print("✅ הועלה לימות המשיח:", r.text)

# הרצת הכל
async def main():
    print("🎤 מייצר תמונת שוק...")
    טקסט = await צור_טקסט()
    print("📄 טקסט תמונת שוק:\n\n" + טקסט + "\n")
    print("🔄 ממיר טקסט ל-MP3...")
    await שמור_קובץ(טקסט)
    העלה_לימות()

if __name__ == "__main__":
    asyncio.run(main())
