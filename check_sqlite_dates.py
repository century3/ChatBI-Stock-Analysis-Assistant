import sqlite3

# 连接到数据库
conn = sqlite3.connect('stock_data.db')
cursor = conn.cursor()

# 检查600519.SH股票数据
cursor.execute("SELECT COUNT(*) FROM stock_history WHERE ts_code = '600519.SH'")
count = cursor.fetchone()[0]
print(f'600519.SH 总记录数: {count}')

# 检查日期范围
cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_history WHERE ts_code = '600519.SH'")
date_range = cursor.fetchone()
print(f'日期范围: {date_range}')

# 检查最近的一些数据
cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 5")
recent_data = cursor.fetchall()
print('最近5条数据:')
for row in recent_data:
    print(row)

# 测试当前日期函数
cursor.execute("SELECT date('now')")
current_date = cursor.fetchone()[0]
print(f'当前日期 (SQLite): {current_date}')

# 测试日期计算
cursor.execute("SELECT date('now', '-1 month')")
one_month_ago = cursor.fetchone()[0]
print(f'一个月前 (SQLite): {one_month_ago}')

conn.close()