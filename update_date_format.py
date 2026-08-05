import sqlite3
import pandas as pd
import os
import re

def update_date_format_in_db():
    """
    将数据库中的 trade_date 从 YYYYMMDD 格式转换为 YYYY-MM-DD 格式
    """
    db_file = 'stock_data.db'
    
    # 连接到数据库
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print("正在读取现有数据...")
    
    # 读取所有数据
    df = pd.read_sql_query("SELECT * FROM stock_history", conn)
    
    print(f"数据总数: {len(df)}")
    print(f"当前日期格式示例: {df['trade_date'].head()}")
    
    # 转换日期格式
    def convert_date_format(date_val):
        date_str = str(date_val)
        # 检查是否是 YYYYMMDD 格式（8位数字）
        if re.match(r'^\d{8}$', date_str):
            # 转换为 YYYY-MM-DD 格式
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        # 如果已经是 YYYY-MM-DD 或其他格式，则保持不变
        return date_str
    
    print("正在转换日期格式...")
    df['trade_date'] = df['trade_date'].apply(convert_date_format)
    
    print(f"转换后日期格式示例: {df['trade_date'].head()}")
    
    # 备份原表
    print("正在备份原表...")
    cursor.execute("ALTER TABLE stock_history RENAME TO stock_history_backup")
    
    # 创建具有相同结构的新表
    cursor.execute('''
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
    
    # 创建索引
    cursor.execute("CREATE INDEX idx_trade_date ON stock_history (trade_date)")
    cursor.execute("CREATE INDEX idx_ts_code ON stock_history (ts_code)")
    cursor.execute("CREATE INDEX idx_stock_name ON stock_history (stock_name)")
    
    # 验证转换结果
    print("\n正在验证转换结果...")
    validation_query = "SELECT trade_date FROM stock_history WHERE ts_code = '600519.SH' ORDER BY trade_date DESC LIMIT 5"
    validation_result = pd.read_sql_query(validation_query, conn)
    print("转换后的最新5条记录:")
    print(validation_result)
    
    conn.commit()
    conn.close()
    
    print("\n日期格式已成功从 YYYYMMDD 转换为 YYYY-MM-DD！")

if __name__ == "__main__":
    update_date_format_in_db()