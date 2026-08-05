import sys
import os
sys.path.append('.')

from stock_analysis_assistant import ExcSql

# 创建工具实例
tool = ExcSql()

# 测试SQL查询 - 获取较长时间段的数据，这样会有很多日期点
params = '{"sql": "SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = \'600519.SH\' AND trade_date >= \'2025-01-01\' ORDER BY trade_date ASC"}'

print("Testing SQL query with many date points:")
print(params)

try:
    result = tool.call(params)
    print(f'Result count: {result[0]["count"]}')
    print('Chart generated successfully!')
    if 'chart' in result[0]:
        print(f'Chart saved to: {result[0]["chart"]}')
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()