import sqlite3

conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()
cursor.execute("SELECT trade_date FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 5")
result = cursor.fetchall()
print('Date format verification:', result)
conn.close()