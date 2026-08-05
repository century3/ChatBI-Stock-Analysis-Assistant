import sqlite3
from datetime import datetime, timedelta
import calendar

# 测试新实现的日期处理函数
def test_processed_sql():
    # 连接到数据库
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()
    
    # 原始查询
    original_sql = "SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= DATE('now', '-1 month') ORDER BY trade_date ASC"
    
    # 模拟处理后的查询
    now = datetime.now()
    if now.month == 1:
        target_year = now.year - 1
        target_month = 12
    else:
        target_year = now.year
        target_month = now.month - 1
    
    _, last_day = calendar.monthrange(target_year, target_month)
    target_day = min(now.day, last_day)
    target_date = datetime(target_year, target_month, target_day)
    formatted_date = target_date.strftime('%Y%m%d')
    
    processed_sql = f"SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = '600519.SH' AND trade_date >= '{formatted_date}' ORDER BY trade_date ASC"
    
    print(f"Original SQL: {original_sql}")
    print(f"Processed SQL: {processed_sql}")
    
    # 执行处理后的查询
    cursor.execute(processed_sql)
    result = cursor.fetchall()
    print(f"Query result count: {len(result)}")
    print("First few results:", result[:5])
    
    conn.close()

if __name__ == '__main__':
    test_processed_sql()