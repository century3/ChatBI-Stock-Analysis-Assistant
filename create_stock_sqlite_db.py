import sqlite3
import pandas as pd
import os

def create_sqlite_database():
    # 读取Excel文件
    excel_file = 'final_merged_stock_data_20200101_to_20251220.xlsx'
    print(f"正在读取文件: {excel_file}")
    
    # 读取Excel数据
    df = pd.read_excel(excel_file)
    
    # 显示数据基本信息
    print(f"数据形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")
    print("\n前5行数据:")
    print(df.head())
    
    # 连接到SQLite数据库（如果不存在则创建）
    db_file = 'stock_data.db'
    conn = sqlite3.connect(db_file)
    
    # 将数据导入SQLite数据库
    table_name = 'stock_history'
    
    # 删除已存在的表
    conn.execute(f'DROP TABLE IF EXISTS {table_name}')
    
    # 导入数据
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # 关闭连接
    conn.close()
    
    print(f"\n数据已成功导入到 {db_file} 的 {table_name} 表中")
    print(f"共导入 {len(df)} 条记录")

if __name__ == "__main__":
    create_sqlite_database()