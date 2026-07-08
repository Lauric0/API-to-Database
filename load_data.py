# import requests
import psycopg2
import finnhub
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv


load_dotenv()

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
            date = datetime.fromtimestamp(candles["t"]["i"]).date()
            cur.execute("""
                INSERT INTO stocks_candles(symbol, current_price, high_price, low_price, open_price, previous_close)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    open _price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
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



def main():
    finnhub_client = finnhub.Client(api_key=os.getenv("API_KEY"))
    symbols = ["AAPL","MSFT", "GOOGL", "TSLA","EXCOF", ""]

    conn=get_db_connection()
    cur=conn.cursor()

    try:
        create_quotes_table(cur)
        create_candles_table(cur)
        conn.commit()

        ## Cotation en temps réel
        for symbol in symbols:
            fetch_and_insert(symbol, finnhub_client, cur)
        conn.commit()

        ## Donnée historiques
        for symbols in symbols:
            fetch_historical(symbol, finnhub_client, cur, days_back=90, resolution="D")
        conn.commit()

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