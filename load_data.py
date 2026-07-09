# import requests
import psycopg2
import finnhub
import os
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv()

CHUNCK_SIZE = 60

PROGRESS_FILE = "progress.json"

# API_KEY= os.getenv("API_KEY")
# URL= os.getenv("URL")

# finnhub_client = finnhub.Client(API_KEY)
# response=requests.get(URL)
# data=response.json()

# Fetch data from API


# Connect to local postgreSQL
def get_db_connection():
    return psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    )


# Create the table in the databases
def create_quotes_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks_data(
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            current_price INTEGER,
            high_price INTEGER,
            low_price INTEGER,
            open_price INTEGER,
            previous_close INTEGER,
            fetched_at TIMESTAMP DEFAULT NOW()
        );

""")

# Create candle table
def create_candles_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks_candles(
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            open_price INTEGER,
            high_price INTEGER,
            low_price INTEGER,
            close_price INTEGER,
            volume BIGINT,
            UNIQUE (symbol, date)
        );

""")


## Fetch and insert the data

def fetch_and_insert(symbol, client, cur):
    try:
        quote = client.quote(symbol)

        if quote.get('c') is None:
            print(f"Aucune donnée pour {symbol}")
            return 
        
        cur.execute("""
            INSERT INTO stocks_data
                (symbol, current_price, high_price, low_price, open_price, previous_close)
            VALUES (%s, %s, %s, %s, %s, %s)

        """,(
            symbol,
            quote['c'],
            quote['h'],
            quote['l'],
            quote['o'],
            quote['pc'],

        ))
        print(f"{symbol} inséré : {quote['c']}")

    except Exception as e:
        print(f"{symbol} : {e}")


## Historical data for a certain period
def fetch_historical(symbol, client, cur, days_back=30, resolution="D"):
    try:
        end=int(time.time())
        start=int((datetime.now() - timedelta(days=days_back)).timestamp())

        candles=  client.stock_candles(symbol, resolution, start, end)

        if candles.get("s") != "ok":
            print(f"Pas de données historiques pour {symbol} : {candles}")
            return
        
        for i in range(len(candles["t"])):
            date = datetime.fromtimestamp(candles["t"][i]).date()
            cur.execute("""
                INSERT INTO stocks_candles(symbol, date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open _price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            """,(
                symbol,
                date,
                candles['o'][i],
                candles['h'][i],
                candles['l'][i],
                candles['c'][i],
                candles['v'][i],
            ))
        
        print(f"{symbol} (historique) : {len(candles['t'])} jours insérés ")
    
    except Exception as e:
        print(f"Erreur historique pour {symbol} : {e}")

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"completed_index":0}

def save_progress(completed_index):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"completed_index": completed_index}, f)


def main():
    finnhub_client = finnhub.Client(api_key=os.getenv("API_KEY"))
    symbols = ["NVDA", "AAPL", "GOOG", "MSFT", "AMZN", "TSM", "SPCX", "AVGO",
    "2222.SR", "META", "TSLA", "005930.KS", "LLY", "MU", "BRK-B",
    "000660.KS", "WMT", "JPM", "AMD", "ASML", "V", "JNJ", "XOM",
    "INTC", "TCEHY", "MA", "AMAT", "CSCO", "ABBV", "CAT", "COST",
    "LRCX", "BAC", "ORCL", "UNH", "601939.SS", "GE", "KO", "CVX",
    "PG", "MS", "RO.SW", "HD", "HSBC", "ARM", "NFLX", "PLTR", "KLAC",
    "IBM", "DELL", "TXN", "PANW", "BABA", "ANET", "MRVL", "QCOM",
    "CRWD", "ADI", "SAP", "APP", "SHOP", "UBER", "AXP", "PEP",
    "GS", "TMO", "MCD", "NOW", "LIN", "PFE", "NVO", "ACN",
    "BKNG", "ISRG", "BLK", "ADBE", "SYK", "RTX", "ETN", "NEE",
    "HON", "BA", "MDT", "C", "SCHW", "VRTX", "GOOGL", "CMCSA",
    "AMGN", "LOW", "TJX", "DE", "CB", "MMC", "BMY", "APD",
    "FI", "LMT", "WM", "MO"
    ]

    total = len(symbols)
    progress = load_progress()
    start = progress["completed_index"]

    if start>= total:
        print(f"Les {total} symboles ont été déjà traités.")
        return
    
    end = min(start + CHUNCK_SIZE, total)
    batch = symbols[start:end]

    conn=get_db_connection()
    cur=conn.cursor()

    try:
        create_quotes_table(cur)
        create_candles_table(cur)
        conn.commit()

        ## Cotation en temps réel
        for symbol in batch:
            fetch_and_insert(symbol, finnhub_client, cur)
        conn.commit()

        ## Donnée historiques
        for symbol in batch:
            fetch_historical(symbol, finnhub_client, cur, days_back=90, resolution="D")
        conn.commit()

        save_progress(end)

        print(f"Terminé.{end}/{total} symboles traités jusqu'à présent")

        if end < total :
            print(f"{total-end} symboles restants - relance le script pour continuer.")
        else:
            print("Tous les symboles ont été traités !")


    finally:
        cur.close()
        conn.close()



if __name__ == "__main__":
    main()











# cur =conn.cursor()

# for item in data:
#     cur.execute(
#         "INSERT INTO users (name, email) VALUES (%s, %s)",
#         (item["name"], item["email"])
#     )


# conn.commit()
# cur.close()
# conn.close()