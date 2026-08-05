import sqlite3
import pandas as pd

def verify_date_format():
    '''验证数据库中的日期格式是否已正确更新'''
    # 连接到数据库
    conn = sqlite3.connect('stock_data.db')
    
    # 检查最新的一些记录
    query = \"SELECT trade_date FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 10\"
    df = pd.read_sql_query(query, conn)
    
    print(\"最新的10条记录的日期格式:\")
    print(df)
    
    # 检查日期格式
    sample_date = df.iloc[0]['trade_date'] if not df.empty else None
    print(f\"\\n示例日期: {sample_date}\")
    print(f\"日期格式正确: {sample_date and '-' in str(sample_date) and len(str(sample_date)) == 10}\")
    
    conn.close()

if __name__ == \"__main__\":
    verify_date_format()