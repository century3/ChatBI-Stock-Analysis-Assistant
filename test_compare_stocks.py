import sys
import os
sys.path.append('.')

from stock_analysis_assistant import ExcSql

# 创建工具实例
tool = ExcSql()

# 测试SQL查询 - 对比两支股票的涨跌幅
params = '{"sql": "SELECT trade_date, ts_code, stock_name, pct_chg FROM stock_history WHERE (ts_code = \'600519.SH\' OR ts_code = \'688981.SH\') AND trade_date >= \'2024-01-01\' AND trade_date <= \'2024-12-31\' ORDER BY trade_date ASC, ts_code ASC"}'

print("Testing SQL query for comparing two stocks (pct_chg):")
print(params)

try:
    result = tool.call(params)
    print(f'Result count: {result[0]["count"]}')
    print('Table preview:')
    print(result[0]['table'][:800])  # 只打印前800个字符作为预览
    print('Chart generated successfully!')
    if 'chart' in result[0]:
        print(f'Chart saved to: {result[0]["chart"]}')
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()