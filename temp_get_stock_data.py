import tushare as ts
import pandas as pd
from datetime import datetime
import os

def get_stock_data():
    """
    使用tushare获取贵州茅台、五粮液、国泰君安、中芯国际的历史价格
    时间范围：2020-01-01到今天
    结果保存到Excel文件中
    """
    # 设置 tushare token（请用环境变量 TUSHARE_TOKEN，勿把 token 写进代码）
    token = os.getenv('TUSHARE_TOKEN', '').strip()
    if not token:
        raise RuntimeError('请设置环境变量 TUSHARE_TOKEN')
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 股票代码和名称映射
    stock_list = {
        '600519.SH': '贵州茅台',
        '000858.SZ': '五粮液', 
        '601211.SH': '国泰君安',
        '688981.SH': '中芯国际'
    }
    
    # 设定时间范围
    start_date = '20200101'
    end_date = datetime.now().strftime('%Y%m%d')
    
    print(f"正在获取 {start_date[:4]}-{start_date[4:6]}-{start_date[6:]} 到 {end_date[:4]}-{end_date[4:6]}-{end_date[6:]} 的股票数据...")
    
    all_data = {}
    
    for code, name in stock_list.items():
        print(f"\n正在获取{name}({code})的数据...")
        try:
            # 获取股票历史数据
            df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
            
            if df is not None and not df.empty:
                # 添加股票名称列（英文表头）
                df['stock_name'] = name
                
                # 按交易日期排序
                df = df.sort_values(by='trade_date', ascending=True).reset_index(drop=True)
                
                # 将数据存储到字典中
                sheet_name = f"{name}({code[:6]})"
                all_data[sheet_name] = df
                
                print(f"SUCCESS: {name}数据获取完成，共{len(df)}条记录")
                print(f"  日期范围: {df['trade_date'].iloc[-1]} 至 {df['trade_date'].iloc[0]}")
            else:
                print(f"NO DATA: {name}({code})无数据")
        except Exception as e:
            print(f"ERROR: 获取{name}({code})数据时出错: {str(e)}")
    
    # 写入Excel文件
    if all_data:
        excel_filename = f"final_merged_stock_data_{start_date}_to_{end_date}.xlsx"
        
        # 合并所有数据到一个DataFrame
        combined_df = pd.concat(all_data.values(), ignore_index=True)
        # 按交易日期升序排序（从小到大）
        combined_df = combined_df.sort_values(by='trade_date', ascending=True).reset_index(drop=True)
        
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name='Stock_Data', index=False)
        
        print(f"\nALL DATA SAVED TO {excel_filename}")
        print(f"文件位置: {os.path.abspath(excel_filename)}")
        
        # 显示汇总统计
        print(f"\n数据汇总:")
        total_rows = len(combined_df)
        print(f"总记录数: {total_rows}")
        print(f"股票数量: {len(all_data)}")
        
        # 按股票名称统计
        for name in stock_list.values():
            count = len(combined_df[combined_df['stock_name'] == name])
            print(f"- {name}: {count} 条记录")
    else:
        print("\n未能获取到任何股票数据")

if __name__ == "__main__":
    get_stock_data()