import json
import os
import decimal
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.utils
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import time

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


@register_tool('ExcSql')
class ExcSql(BaseTool):
    description = '执行SQL查询并自动生成图表'
    parameters = [
        {
            'name': 'sql',
            'type': 'string',
            'description': '要执行的SQL查询语句',
            'required': True
        }
    ]

    def call(self, params: str, **kwargs) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        :param params: JSON字符串，包含sql参数
        :param kwargs: 其他参数（如messages等）
        :return: 查询结果
        """
        import pymysql
        params_dict = json.loads(params)
        sql = params_dict.get('sql')

        try:
            # 阿里云数据库连接信息
            connection = pymysql.connect(
                host='rm-uf6z891lon6dxuqblqo.mysql.rds.aliyuncs.com',
                port=3306,
                user='student123',
                password='student321',
                database='stock_data',
                charset='utf8mb4'
            )

            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                
                # 获取列名
                columns = [desc[0] for desc in cursor.description]
                
                # 将结果转换为字典列表
                rows = []
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # 将Decimal类型转换为float，以便JSON序列化
                        if isinstance(value, decimal.Decimal):
                            value = float(value)
                        row_dict[col] = value
                    rows.append(row_dict)
                
                # 创建DataFrame并生成图表
                if rows:
                    df = pd.DataFrame(rows)
                    
                    # 自动创建目录
                    save_dir = os.path.join(os.path.dirname(__file__), 'image_show')
                    os.makedirs(save_dir, exist_ok=True)
                    filename = f'chart_{int(time.time() * 1000)}.png'
                    save_path = os.path.join(save_dir, filename)
                    
                    # 生成图表
                    generate_chart_png(df, save_path)
                    
                    # 转换为Markdown格式的图片链接
                    img_path = os.path.join('image_show', filename)
                    img_md = f'![股票数据图表]({img_path})'
                    
                    # 生成markdown表格
                    md = df.to_markdown(index=False) if hasattr(df, 'to_markdown') else str(df)
                    
                    return [{'result': rows, 'count': len(rows), 'table': md, 'chart': img_md}]
                else:
                    md = pd.DataFrame(rows).to_markdown(index=False) if hasattr(pd.DataFrame(rows), 'to_markdown') else str(pd.DataFrame(rows))
                    return [{'result': rows, 'count': len(rows), 'table': md}]
                
        except Exception as e:
            return [{'error': f'执行SQL查询时出错: {str(e)}'}]
        finally:
            if 'connection' in locals():
                connection.close()


def generate_chart_png(df_sql, save_path):
    """
    生成股票收盘价折线图
    """
    # 检查是否有交易日期列和收盘价列
    date_columns = [col for col in df_sql.columns if 'date' in col.lower()]
    close_column = [col for col in df_sql.columns if 'close' in col.lower()]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if date_columns and close_column:
        # 使用交易日期作为X轴，收盘价作为Y轴
        date_col = date_columns[0]
        close_col = close_column[0]
        x_values = df_sql[date_col].apply(str)  # 转换为字符串便于显示
        
        ax.plot(x_values, df_sql[close_col], marker='o', label=f'{close_col}价格', linewidth=2, color='#1f77b4')
        ax.set_xlabel(date_col)
        ax.set_ylabel(close_col)
        ax.set_title('股票收盘价走势图')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
    elif close_column:
        # 如果没有日期列，使用索引作为X轴
        close_col = close_column[0]
        ax.plot(df_sql[close_col], marker='o', label=f'{close_col}价格', linewidth=2, color='#1f77b4')
        ax.set_xlabel('Index')
        ax.set_ylabel(close_col)
        ax.set_title('股票收盘价走势图')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
    else:
        # 如果没有收盘价列，尝试使用第一个数值列
        numeric_columns = df_sql.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_columns:
            first_numeric = numeric_columns[0]
            if date_columns:
                date_col = date_columns[0]
                x_values = df_sql[date_col].apply(str)
                ax.plot(x_values, df_sql[first_numeric], marker='o', label=first_numeric, linewidth=2, color='#1f77b4')
                ax.set_xlabel(date_col)
            else:
                ax.plot(df_sql[first_numeric], marker='o', label=first_numeric, linewidth=2, color='#1f77b4')
                ax.set_xlabel('Index')
            
            ax.set_ylabel(first_numeric)
            ax.set_title('数据走势图')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.6)
    
    # 旋转X轴标签以防重叠
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    # 用您自己的API-KEY和模型
    llm_cfg = {
        'model': 'qwen-max',  # 或其他您可用的模型
        'api_key': os.getenv('DASHSCOPE_API_KEY'),
    }

    system_instruction = '''
    您是一个专业的股票查询和分析助手，能够通过执行SQL查询来获取股票历史数据、分析趋势并比较股票表现，并生成可视化图表。
    
    您可以执行以下操作：
    1. 查询股票历史数据 - 使用ExcSql工具执行SELECT查询
    2. 分析股票趋势 - 使用ExcSql工具执行统计分析查询
    3. 比较股票表现 - 使用ExcSql工具执行多股票比较查询
    
    ExcSql工具会自动根据查询结果生成相应的图表。
    
    以下是股票历史数据表的结构：
    CREATE TABLE stock_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,          -- 股票代码
        trade_date VARCHAR(10) NOT NULL,       -- 交易日期
        `open` DECIMAL(10,3) NOT NULL,           -- 开盘价
        high DECIMAL(10,3) NOT NULL,           -- 最高价
        low DECIMAL(10,3) NOT NULL,            -- 最低价
        `close` DECIMAL(10,3) NOT NULL,          -- 收盘价
        pre_close DECIMAL(10,3),               -- 前收盘价
        `change` DECIMAL(10,3),                  -- 涨跌额
        pct_chg DECIMAL(10,4),                 -- 涨跌幅(%)
        vol BIGINT,                           -- 成交量(手)
        amount DECIMAL(20,2),                  -- 成交额(千元)
        stock_name VARCHAR(100) NOT NULL,      -- 股票名称
        INDEX idx_trade_date (trade_date),      -- 交易日期索引
        INDEX idx_ts_code (ts_code),           -- 股票代码索引
        INDEX idx_stock_name (stock_name)       -- 股票名称索引
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    
    在回答时，请：
    - 提供清晰、准确的数据和分析结果
    - 使用易懂的语言解释复杂的金融概念
    - 在适当的时候提醒投资风险
    - 当数据不足以回答问题时，诚实地告知用户
    - 每当ExcSql工具返回markdown表格和图片时，您必须原样输出工具返回的全部内容（包括图片markdown），不要只总结表格，也不要省略图片。这样用户才能直接看到表格和图片。
    '''

    tools = [
        'ExcSql'
    ]

    bot = Assistant(
        llm=llm_cfg,
        name='股票查询和分析助手',
        description='股票数据查询与分析',
        system_message=system_instruction,  # 使用 system_message 替代 system_instruction
        function_list=tools
    )
    
    # 启动GUI界面
    from qwen_agent.gui import WebUI
    
    # 配置聊天界面建议
    chatbot_config = {
        'prompt.suggestions': [
            '查询贵州茅台最近一个月的股价走势',
            '分析五粮液的开盘价、收盘价变化',
            '比较国泰君安和中芯国际的股价表现',
            '生成最近三个月的股票图表'
        ]
    }
    
    # 启动 WebUI
    WebUI(
        bot,
        chatbot_config=chatbot_config
    ).run()


if __name__ == '__main__':
    main()