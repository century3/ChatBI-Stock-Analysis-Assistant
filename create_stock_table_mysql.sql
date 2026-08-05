-- MySQL版本 - 股票历史数据表
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

-- 可选：创建视图便于查询
CREATE VIEW v_stock_summary AS
SELECT 
    ts_code,
    stock_name,
    trade_date,
    open,
    close,
    high,
    low,
    change,
    pct_chg,
    vol,
    amount
FROM stock_history;