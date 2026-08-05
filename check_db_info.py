import sqlite3

def check_db_info():
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()
    
    # 检查股票代码
    cursor.execute("SELECT DISTINCT ts_code FROM stock_history LIMIT 5")
    print('Stock codes:', cursor.fetchall())
    
    # 检查日期范围
    cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_history")
    print('Date range:', cursor.fetchall())
    
    # 检查贵州茅台的数据
    cursor.execute("SELECT COUNT(*) FROM stock_history WHERE ts_code = '600519.SH'")
    print('600519.SH records count:', cursor.fetchall())
    
    # 检查最近的交易日期
    cursor.execute("SELECT MAX(trade_date) FROM stock_history WHERE ts_code = '600519.SH'")
    print('Latest trade date for 600519.SH:', cursor.fetchall())
    
    conn.close()

if __name__ == '__main__':
    check_db_info()