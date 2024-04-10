from flask import Flask, render_template, request, jsonify
from forex_python.converter import CurrencyRates
from datetime import datetime, timedelta
import json
import mysql.connector
import numpy as np
 
app = Flask(__name__)
 
# Connect to MySQL database
conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='changeme',
    database='exchange_rates_db'
)
cursor = conn.cursor()
 
def get_historical_exchange_rates(from_currency, to_currency):
    c = CurrencyRates()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    historical_rates = []
    while start_date <= end_date:
        rate = c.get_rate(from_currency, to_currency, start_date)
        date_str = start_date.strftime('%Y-%m-%d')
        historical_rates.append((date_str, from_currency, to_currency, rate))
        start_date += timedelta(days=1)
    return historical_rates
 
def fetch_and_cache_exchange_rate(from_currency, to_currency):
    historical_data = get_historical_exchange_rates(from_currency, to_currency)
    insert_query = "INSERT INTO exchange_rates (date, from_currency, to_currency, rate) VALUES (%s, %s, %s, %s)"
    cursor.executemany(insert_query, historical_data)
    conn.commit()
    return historical_data
 
def calculate_statistics(rates):
    rates_array = np.array(rates)
    max_rate = np.max(rates_array)
    min_rate = np.min(rates_array)
    avg_rate = np.mean(rates_array)
    rate_changes = np.diff(rates_array)
    avg_growth_rate = np.mean(rate_changes[rate_changes > 0])
    avg_decline_rate = np.mean(rate_changes[rate_changes < 0])
    return {
        'max_rate': max_rate,
        'min_rate': min_rate,
        'avg_rate': avg_rate,
        'avg_growth_rate': avg_growth_rate,
        'avg_decline_rate': avg_decline_rate
    }
 
def get_all_currencies():
    c = CurrencyRates()
    return c.get_rates('USD').keys()
 
@app.route('/')
def index():
    currencies = get_all_currencies()
    return render_template('index.html', currencies=currencies)
 
@app.route('/get_exchange_rate', methods=['POST'])
def get_exchange_rate():
    data = request.get_json()
    from_currency = data['from_currency']
    to_currency = data['to_currency']
    select_query = "SELECT date, rate FROM exchange_rates WHERE from_currency = %s AND to_currency = %s"
    cursor.execute(select_query, (from_currency, to_currency))
    result = cursor.fetchall()
    if result:
        dates = [entry[0] for entry in result]
        rates = [entry[1] for entry in result]
        statistics = calculate_statistics(rates)
        return jsonify({'dates': dates, 'rates': rates, 'statistics': statistics})
    else:
        historical_data = fetch_and_cache_exchange_rate(from_currency, to_currency)
        dates = [entry[0] for entry in historical_data]
        rates = [entry[3] for entry in historical_data]
        statistics = calculate_statistics(rates)
        return jsonify({'dates': dates, 'rates': rates, 'statistics': statistics})
 
if __name__ == '__main__':
    app.run(debug=True)