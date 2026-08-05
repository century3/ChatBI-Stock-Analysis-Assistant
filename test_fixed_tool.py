import sys
import os
sys.path.append(os.getcwd())

from stock_analysis_assistant import ExcSql

# 创建工具实例
tool = ExcSql()

# 测试SQL查询
params = '{\"sql\": \"SELECT trade_date, open, high, low, close FROM stock_history WHERE ts_code = \\\"600519.SH\\\" AND trade_date >= DATE(\\\"now\\\", \\\"-1 month\\\") ORDER BY trade_date ASC\"}'

print(\"Testing SQL query:\")
print(params)

try:
    result = tool.call(params)
    print('Result:', result)
except Exception as e:
    print(f\"Error occurred: {e}\")
    import traceback
    traceback.print_exc()