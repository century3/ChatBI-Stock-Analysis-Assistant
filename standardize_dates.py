import sqlite3
import pandas as pd
import os
from datetime import datetime

def standardize_date_format():
    """
    将数据库中的日期格式从YYYYMMDD转换为YYYY-MM-DD
    """
    # 连接到现有数据库
    db_file = 'stock_data.db'
    conn = sqlite3.connect(db_file)
    
    # 读取现有数据
    df = pd.read_sql_query("SELECT * FROM stock_history", conn)
    
    print(f"原始数据形状: {df.shape}")
    print(f"原始trade_date格式示例: {df['trade_date'].head()}")
    
    # 检查当前日期格式
    sample_date = df['trade_date'].iloc[0] if not df.empty else None
    print(f"示例日期: {sample_date} (类型: {type(sample_date)})")
    
    # 将YYYYMMDD格式的日期转换为YYYY-MM-DD格式
    def convert_date_format(date_val):
        date_str = str(date_val)
        if '-' not in date_str and len(date_str) == 8:  # 是YYYYMMDD格式
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str  # 已经是标准格式或其他格式
    
    df['trade_date'] = df['trade_date'].apply(convert_date_format)
    
    print(f"转换后trade_date格式示例: {df['trade_date'].head()}")
    
    # 重新创建表并插入转换后的数据
    conn.execute('DROP TABLE IF EXISTS stock_history')
    
    # 创建新表结构
    conn.execute('''
        CREATE TABLE stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code TEXT NOT NULL,          -- 股票代码
            trade_date TEXT NOT NULL,       -- 交易日期
            open REAL NOT NULL,             -- 开盘价
            high REAL NOT NULL,             -- 最高价
            low REAL NOT NULL,              -- 最低价
            close REAL NOT NULL,            -- 收盘价
            pre_close REAL,                 -- 前收盘价
            change REAL,                    -- 涨跌额
            pct_chg REAL,                   -- 涨跌幅(%)
            vol INTEGER,                    -- 成交量(手)
            amount REAL,                    -- 成交额(千元)
            stock_name TEXT NOT NULL        -- 股票名称
        )
    ''')
    
    # 插入转换后的数据
    df.to_sql('stock_history', conn, if_exists='append', index=False)
    
    # 关闭连接
    conn.close()
    
    print(f"日期格式已标准化并保存到 {db_file}")
    
    # 验证转换结果
    conn = sqlite3.connect(db_file)
    check_df = pd.read_sql_query("SELECT trade_date FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 5", conn)
    print("验证转换结果（最新的5条记录）:")
    print(check_df)
    conn.close()


if __name__ == "__main__":
    standardize_date_format()