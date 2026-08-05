import sqlite3

# 连接到数据库
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

# 检查在指定日期范围内的数据
cursor.execute("SELECT COUNT(*) FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= '20251120' AND trade_date <= '20251220'")
count = cursor.fetchone()[0]
print(f'20251120到20251220之间600519.SH记录数: {count}')

# 实际查询这个范围内的数据
cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= '20251120' ORDER BY trade_date ASC")
results = cursor.fetchall()
print('实际查询结果:')
for row in results:
    print(row)

# 尝试使用SQLite的日期函数格式
print('\n尝试使用strftime函数:')
cursor.execute("SELECT COUNT(*) FROM stock_history WHERE ts_code = '600519.SH' AND strftime('%Y%m%d', trade_date) >= '20251120'")
count2 = cursor.fetchone()[0]
print(f'使用strftime函数的计数: {count2}')

conn.close()