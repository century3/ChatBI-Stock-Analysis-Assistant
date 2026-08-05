import sqlite3

def test_query():
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()
    
    # 测试原始SQL查询
    cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= date('now', '-1 month') ORDER BY trade_date ASC LIMIT 5")
    print('Original query result:', cursor.fetchall())
    
    # 测试使用具体日期的查询
    cursor.execute("SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= '2025-11-20' ORDER BY trade_date ASC LIMIT 5")
    print('Specific date query result:', cursor.fetchall())
    
    # 测试当前日期
    cursor.execute("SELECT date('now')")
    print('Current date:', cursor.fetchall())
    
    # 测试日期计算
    cursor.execute("SELECT date('now', '-1 month')")
    print('Date one month ago:', cursor.fetchall())
    
    conn.close()

if __name__ == '__main__':
    test_query()