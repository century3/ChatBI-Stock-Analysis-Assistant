import sqlite3

def test_query():
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()
    
    # 检查最近一个月的实际数据
    cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= '2025-11-20' ORDER BY trade_date ASC")
    print('Data from 2025-11-20 onwards:', cursor.fetchall())
    
    # 检查更具体的时间段
    cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date BETWEEN '2025-11-20' AND '2025-12-20' ORDER BY trade_date ASC LIMIT 10")
    print('Data between 2025-11-20 and 2025-12-20:', cursor.fetchall())
    
    # 检查最新的几条记录
    cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 10")
    print('Latest 10 records:', cursor.fetchall())
    
    # 检查是否存在格式问题
    cursor.execute("SELECT DISTINCT substr(trade_date, 1, 4) FROM stock_history WHERE ts_code = '600519.SH' ORDER BY 1 DESC LIMIT 5")
    print('Distinct years:', cursor.fetchall())
    
    conn.close()

if __name__ == '__main__':
    test_query()