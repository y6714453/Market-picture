import asyncio
import datetime
import pytz
import requests
import yfinance as yf
from edge_tts import Communicate
import subprocess

USERNAME = "0733181201"
PASSWORD = "6714453"
TOKEN = f"{USERNAME}:{PASSWORD}"

OUTPUT_MP3 = "market.mp3"
OUTPUT_WAV = "market.wav"
UPLOAD_PATH = "ivr2:/2/market.wav"

TICKERS = {
    "מדד תל אביב 125": "^TA125.TA",
    "מדד תל אביב 35": "^TA35.TA",
    "מדד אס אנד פי חמש מאות": "^GSPC",
    "הנאסדאק": "^IXIC",
    "דאו ג'ונס": "^DJI"
}

CRYPTO = {
    "הביטקוין": "BTC-USD",
    "האתריום": "ETH-USD"
}

USD_ILS = "USDILS=X"

async def convert_to_wav(input_file, output_file):
    subprocess.run([
        "ffmpeg", "-y", "-i", input_file,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le",
        output_file
    ])


def get_heb_time():
    now = datetime.datetime.now(pytz.timezone('Asia/Jerusalem'))
    hour = now.hour
    minute = now.minute
    if minute == 0:
        minute_str = "בדיוק"
    else:
        minute_str = f"וְ{num_to_words(minute)} דַּקּוֹת"

    if 6 <= hour < 12:
        greeting = "בֹּקֶר טוֹב"
    elif 12 <= hour < 18:
        greeting = "צָהֳרַיִם טוֹבִים"
    elif 18 <= hour < 21:
        greeting = "עֶרֶב טוֹב"
    else:
        greeting = "לַיְלָה טוֹב"

    return greeting, f"נָכוֹן לְשָׁעָה {num_to_words(hour)} {minute_str}"


def num_to_words(num):
    import inflect
    p = inflect.engine()
    hebrew_map = {
        "zero": "אֶפֶס", "one": "אֶחָד", "two": "שְׁנַיִם", "three": "שָׁלוֹשׁ", "four": "אַרְבַּע",
        "five": "חָמֵשׁ", "six": "שֵׁשׁ", "seven": "שֶׁבַע", "eight": "שְׁמוֹנֶה", "nine": "תֵּשַׁע",
        "ten": "עֶשֶׂר", "eleven": "אַחַת עֶשְׂרֵה", "twelve": "שְׁתֵּים עֶשְׂרֵה", "thirteen": "שְׁלוֹשׁ עֶשְׂרֵה",
        "fourteen": "אַרְבַּע עֶשְׂרֵה", "fifteen": "חֲמֵשׁ עֶשְׂרֵה", "sixteen": "שֵׁשׁ עֶשְׂרֵה",
        "seventeen": "שְׁבַע עֶשְׂרֵה", "eighteen": "שְׁמוֹנֶה עֶשְׂרֵה", "nineteen": "תֵּשַׁע עֶשְׂרֵה",
        "twenty": "עֶשְׂרִים", "thirty": "שְׁלוֹשִׁים", "forty": "אַרְבָּעִים", "fifty": "חֲמִשִּׁים"
    }
    eng = p.number_to_words(num, andword="")
    return " ".join(hebrew_map.get(word, word) for word in eng.split())


def get_price(ticker):
    try:
        df = yf.Ticker(ticker).history(period="5d")
        if len(df) < 2:
            return None, None, None
        prev_close = df["Close"].iloc[-2]
        current = df["Close"].iloc[-1]
        change = ((current - prev_close) / prev_close) * 100
        return round(current), round(change, 2), df
    except Exception:
        return None, None, None


def generate_market_text():
    greeting, time_phrase = get_heb_time()
    lines = [f"{greeting}, זוֹ תְּמוּנַת הַשּׁוּק {time_phrase}:", "\n", "בְּיִישְׂרָאֵל:"]

    for name, ticker in TICKERS.items():
        price, change, df = get_price(ticker)
        if price is None:
            continue
        trend = "עוֹלֶה" if change > 0 else "יוֹרֵד"
        change_str = f"{trend} בְּשִׁעּוּר שֶׁל {str(abs(change)).replace('.', ' נְקוּדָה ')} אָחוּז"
        price_str = f"וְעוֹמֵד עַל {price} נְקוּדוֹת"
        lines.append(f"{name} {change_str}, {price_str}.")

    lines.append("\nבָּעוֹלָם:")

    for name, ticker in list(TICKERS.items())[2:]:
        price, change, df = get_price(ticker)
        if price is None:
            continue
        trend = "עוֹלֶה" if change > 0 else "יוֹרֵד"
        change_str = f"{trend} בְּשִׁעּוּר שֶׁל {str(abs(change)).replace('.', ' נְקוּדָה ')} אָחוּז"
        price_str = f"וְעוֹמֵד עַל {price} נְקוּדוֹת"
        lines.append(f"{name} {change_str}, {price_str}.")

    lines.append("\nבְּגִזְרַת הַקְּרִיפְּטוֹ:")
    for name, ticker in CRYPTO.items():
        price, change, _ = get_price(ticker)
        if price is not None:
            lines.append(f"{name} נִסְחָר בְּשַׁעַר שֶׁל {price} דּוֹלָר.")

    usd_price, _, _ = get_price(USD_ILS)
    if usd_price:
        trend = "מִתְחַזֵּק" if _ > 0 else "נֶחְלָשׁ"
        lines.append(f"הַדּוֹלָר {trend} מוּל הַשֶּׁקֶל וְנִסְחָר בְּשַׁעַר שֶׁל {str(usd_price).replace('.', ' נְקוּדָה ')} שֶׁקֶל.")

    return "\n".join(lines)


async def loop():
    while True:
        print("🎤 מייצר תמונת שוק...")
        text = generate_market_text()
        print(f"\n📄 טקסט תמונת שוק:\n\n{text}\n")

        communicate = Communicate(text=text, voice="he-IL-AvriNeural")
        await communicate.save(OUTPUT_MP3)
        print(f"✅ נוצר קובץ MP3: {OUTPUT_MP3}")

        await convert_to_wav(OUTPUT_MP3, OUTPUT_WAV)
        print(f"🎛️ ממיר ל-WAV בפורמט ימות...")

        with open(OUTPUT_WAV, 'rb') as f:
            response = requests.post(
                'https://www.call2all.co.il/ym/api/UploadFile',
                files={'file': ("market.wav", f, 'audio/wav')},
                data={'token': TOKEN, 'path': UPLOAD_PATH}
            )
            print(f"⬆️ מעלה לשלוחה: {UPLOAD_PATH} – תוצאה: {response.status_code}, {response.text}")

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(loop())
