-- SQLite版本 - 股票历史数据表
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
);

-- 创建索引
CREATE INDEX idx_trade_date ON stock_history (trade_date);      -- 交易日期索引
CREATE INDEX idx_ts_code ON stock_history (ts_code);           -- 股票代码索引
CREATE INDEX idx_stock_name ON stock_history (stock_name);     -- 股票名称索引