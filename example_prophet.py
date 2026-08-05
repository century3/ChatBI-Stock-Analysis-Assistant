"""
Prophet 股票周期性分析工具使用示例
"""
import json
from prophet_analysis import ProphetAnalysisTool

def example_usage():
    print("Prophet 股票周期性分析工具使用示例")
    print("=" * 50)
    
    # 创建Prophet分析工具实例
    prophet_tool = ProphetAnalysisTool()
    
    # 示例1: 分析贵州茅台过去一年的周期性
    print("\n示例1: 分析贵州茅台(600519.SH)的周期性")
    params1 = json.dumps({
        "ts_code": "600519.SH",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    })
    
    try:
        result1 = prophet_tool.call(params1)
        if result1 and 'error' not in result1[0]:
            result_data = result1[0]
            print(f"股票代码: {result_data['stock_code']}")
            print(f"分析期间: {result_data['analysis_period']}")
            print(f"数据点数: {result_data['data_points_count']}")
            
            trend_analysis = result_data.get('trend_analysis', {})
            if 'direction' in trend_analysis:
                print(f"趋势分析: {trend_analysis['direction']}，变化率: {trend_analysis['change_percentage']}%")
            
            weekly_analysis = result_data.get('weekly_analysis', {})
            if 'avg_positive_effect' in weekly_analysis:
                print(f"周季节性: 平均正效应 {weekly_analysis['avg_positive_effect']}, 平均负效应 {weekly_analysis['avg_negative_effect']}")
            
            yearly_analysis = result_data.get('yearly_analysis', {})
            if 'highest_month' in yearly_analysis:
                print(f"年季节性: 最高价月份 {yearly_analysis['highest_month']} (均价 {yearly_analysis['highest_month_avg_price']}), 最低价月份 {yearly_analysis['lowest_month']} (均价 {yearly_analysis['lowest_month_avg_price']})")
            
            print(f"组件图表: {result_data['components_chart']}")
            print(f"趋势图表: {result_data['trend_chart']}")
        else:
            print(f"分析失败: {result1[0]['error']}")
    except Exception as e:
        print(f"执行分析时出错: {e}")
    
    print("\n" + "=" * 50)
    print("提示：图表已保存到 image_show 目录中")

if __name__ == "__main__":
    example_usage()