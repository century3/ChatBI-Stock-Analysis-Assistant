import json
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 测试Prophet分析功能是否能够正确导入
try:
    from prophet_analysis import ProphetAnalysisTool
    if ProphetAnalysisTool:
        print("Prophet分析工具成功导入！")
    else:
        print("警告：Prophet分析工具导入失败")
except ImportError as e:
    print(f"导入Prophet分析工具时出错: {e}")

# 测试是否可以正常访问SQLite数据库
import sqlite3
try:
    conn = sqlite3.connect('stock_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"数据库中的表: {tables}")
    
    # 尝试查询一些数据
    cursor.execute("SELECT ts_code, COUNT(*) FROM stock_history GROUP BY ts_code LIMIT 5;")
    sample_data = cursor.fetchall()
    print(f"股票代码样本及数据量: {sample_data}")
    
    conn.close()
    print("数据库连接测试成功！")
except Exception as e:
    print(f"数据库连接测试失败: {e}")

# 尝试检查是否有Prophet库
try:
    from prophet import Prophet
    print("Prophet库已安装")
except ImportError:
    print("警告：Prophet库未安装。请运行 'pip install prophet' 安装")