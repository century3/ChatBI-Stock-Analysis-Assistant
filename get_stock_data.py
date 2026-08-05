"""
按系统当前日期更新股票历史数据到 stock_data.db。

默认增量模式：从库内各股票最新交易日的次日拉取到今天，upsert 写入 stock_history。
可用 --full 从 2020-01-01 全量重拉。

数据源：
- 默认 auto：优先 akshare（无需 token），失败时可再试 tushare
- --source tushare：需要环境变量 TUSHARE_TOKEN（仅 A 股；美股始终走 akshare）
- --source akshare：仅用 akshare

代码约定：
- A股：600519.SH / 000858.SZ
- 美股：COHR.US / IPSC.US / GOOG.US / NVDA.US（裸代码也会规范为 *.US）
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

# A股用 .SH/.SZ；美股用 .US（如 COHR.US）
STOCK_LIST = {
    '600519.SH': '贵州茅台',
    '000858.SZ': '五粮液',
    '601211.SH': '国泰君安',
    '688981.SH': '中芯国际',
    'COHR.US': 'Coherent',
    'IPSC.US': 'Century Therapeutics',
    'GOOG.US': 'Alphabet',
    'NVDA.US': 'NVIDIA',
}

HISTORY_COLS = [
    'ts_code', 'trade_date', 'open', 'high', 'low', 'close',
    'pre_close', 'change', 'pct_chg', 'vol', 'amount', 'stock_name',
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'stock_data.db')

# 助手内自动刷新节流：同一进程内避免频繁打行情接口
_LAST_ENSURE_TS = 0.0
_LAST_ENSURE_RESULT: Optional[dict] = None


def _to_ymd(date_str: str) -> str:
    """统一成 YYYYMMDD。"""
    s = str(date_str).replace('-', '')
    return s[:8]


def _to_iso(date_str: str) -> str:
    """统一成 YYYY-MM-DD。"""
    s = _to_ymd(date_str)
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}'


def is_us_stock(ts_code: str) -> bool:
    """判断是否为美股代码（以 .US 结尾，或纯 ASCII 字母 ticker）。"""
    if not ts_code:
        return False
    code = ts_code.strip().upper()
    if code.endswith('.US'):
        return True
    # 仅 ASCII 字母才视为裸美股代码，避免「美股COHR」等中文混写误判
    return '.' not in code and code.isascii() and code.isalpha()


def _extract_ticker_candidate(text: str) -> Optional[str]:
    """从嘈杂输入中提取可能的股票代码/名称片段。"""
    import re

    if not text:
        return None
    raw = text.strip()

    # 已是标准代码
    m = re.search(r'\b([0-9]{6}\.(?:SH|SZ)|[A-Za-z]{1,10}\.US)\b', raw, re.I)
    if m:
        return m.group(1).upper()

    # 去掉常见中文修饰后取美股 ticker
    cleaned = re.sub(
        r'(美股|股票|股价|代码|预测|收盘价|未来|分析|查询)',
        '',
        raw,
        flags=re.I,
    )
    cleaned = cleaned.strip().upper()
    m = re.search(r'\b([A-Z]{1,10})\b', cleaned)
    if m:
        return m.group(1)
    m = re.search(r'\b([0-9]{6})\b', cleaned)
    if m:
        return m.group(1)
    return None


def normalize_ts_code(ts_code: str, db_path: Optional[str] = None) -> str:
    """
    规范化股票代码：支持名称、裸美股代码（COHR -> COHR.US）、嘈杂中文输入、大小写。
    未匹配时尽量从数据库解析；仍失败则原样返回（去掉首尾空白）。
    """
    import unicodedata

    if not ts_code:
        return ts_code
    raw = unicodedata.normalize('NFKC', str(ts_code)).strip()
    upper = raw.upper()

    if upper in STOCK_LIST:
        return upper
    if raw in STOCK_LIST:
        return raw

    for code, name in STOCK_LIST.items():
        if name == raw or name.upper() == upper:
            return code

    candidate = _extract_ticker_candidate(raw) or upper

    # 标准后缀
    if candidate in STOCK_LIST:
        return candidate
    for code, name in STOCK_LIST.items():
        if name.upper() == candidate:
            return code

    # 裸美股 ticker：COHR -> COHR.US
    if candidate.isascii() and candidate.isalpha():
        us_code = f'{candidate}.US'
        if us_code in STOCK_LIST:
            return us_code
        if _resolve_code_from_db(us_code, db_path):
            return us_code
        resolved = _resolve_code_from_db(candidate, db_path)
        if resolved:
            # 若库里只有裸代码别名，仍返回规范 .US（若存在）
            return us_code if _resolve_code_from_db(us_code, db_path) else resolved
        return us_code

    # A股 6 位：优先从库里找完整 ts_code
    if candidate.isdigit() and len(candidate) == 6:
        resolved = _resolve_code_from_db(candidate, db_path)
        if resolved:
            return resolved

    resolved = _resolve_code_from_db(raw, db_path) or _resolve_code_from_db(candidate, db_path)
    if resolved:
        return resolved

    return raw


def expand_ts_code_aliases(ts_code: str, db_path: Optional[str] = None) -> list:
    """返回查询时应匹配的全部代码别名，如 COHR -> [COHR.US, COHR]。"""
    canonical = normalize_ts_code(ts_code, db_path=db_path)
    aliases = []
    for code in (canonical, ts_code, str(ts_code or '').strip().upper()):
        if code and code not in aliases:
            aliases.append(code)
    if canonical.endswith('.US'):
        bare = canonical[:-3]
        if bare and bare not in aliases:
            aliases.append(bare)
    elif canonical.isascii() and canonical.isalpha() and '.' not in canonical:
        us_code = f'{canonical}.US'
        if us_code not in aliases:
            aliases.insert(0, us_code)
    return aliases


def sync_us_ticker_aliases(db_path: Optional[str] = None) -> int:
    """
    为美股写入裸代码别名行，使 ts_code='COHR' 与 'COHR.US' 都能查到。
    返回新写入的行数。
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return 0
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    us_codes = conn.execute(
        "SELECT DISTINCT ts_code FROM stock_history WHERE ts_code LIKE '%.US'"
    ).fetchall()
    inserted = 0
    for (ts_code,) in us_codes:
        bare = ts_code[:-3]
        if not bare:
            continue
        cur = conn.execute(
            '''
            INSERT OR IGNORE INTO stock_history (
                ts_code, trade_date, open, high, low, close,
                pre_close, change, pct_chg, vol, amount, stock_name
            )
            SELECT ?, trade_date, open, high, low, close,
                   pre_close, change, pct_chg, vol, amount, stock_name
            FROM stock_history
            WHERE ts_code = ?
            ''',
            (bare, ts_code),
        )
        inserted += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    conn.commit()
    conn.close()
    return inserted


def _resolve_code_from_db(token: str, db_path: Optional[str] = None) -> Optional[str]:
    """按 ts_code / stock_name 在库中模糊解析真实代码。"""
    if not token:
        return None
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return None
    token = token.strip()
    upper = token.upper()
    try:
        conn = sqlite3.connect(path)
        # 精确匹配
        row = conn.execute(
            'SELECT ts_code FROM stock_history WHERE UPPER(ts_code)=? OR stock_name=? LIMIT 1',
            (upper, token),
        ).fetchone()
        if row:
            conn.close()
            return row[0]
        # COHR -> COHR.US / 600519 -> 600519.SH
        row = conn.execute(
            'SELECT DISTINCT ts_code FROM stock_history WHERE UPPER(ts_code) LIKE ? LIMIT 2',
            (f'{upper}%',),
        ).fetchall()
        if len(row) == 1:
            conn.close()
            return row[0][0]
        # 名称模糊
        row = conn.execute(
            'SELECT DISTINCT ts_code FROM stock_history WHERE UPPER(stock_name) LIKE ? LIMIT 2',
            (f'%{upper}%',),
        ).fetchall()
        conn.close()
        if len(row) == 1:
            return row[0][0]
    except Exception:
        return None
    return None


def rewrite_sql_stock_codes(sql: str, db_path: Optional[str] = None) -> str:
    """
    将 SQL 中 ts_code 条件里的裸美股代码/别名改写为可命中的 IN 条件。
    例如 ts_code = 'COHR' -> ts_code IN ('COHR.US','COHR')
    不会改写 stock_name、日期等其它字面量。
    """
    import re

    if not sql:
        return sql

    def aliases_sql(literal: str) -> str:
        aliases = expand_ts_code_aliases(literal, db_path=db_path)
        parts = ','.join("'" + a.replace("'", "''") + "'" for a in aliases)
        return f'IN ({parts})'

    # ts_code = 'COHR' / ts_code="COHR" -> ts_code IN (...)
    def repl_eq(match: re.Match) -> str:
        return f"ts_code {aliases_sql(match.group(2))}"

    sql = re.sub(
        r"ts_code\s*=\s*(['\"])([^'\"]+)\1",
        repl_eq,
        sql,
        flags=re.IGNORECASE,
    )

    # ts_code IN ('COHR', 'AAPL') — 展开每个元素的别名
    def repl_in(match: re.Match) -> str:
        inner = match.group(2)
        expanded: list = []

        def repl_item(m: re.Match) -> str:
            for a in expand_ts_code_aliases(m.group(2), db_path=db_path):
                if a not in expanded:
                    expanded.append(a)
            return ''

        re.sub(r"(['\"])([^'\"]+)\1", repl_item, inner)
        if not expanded:
            return match.group(0)
        parts = ','.join("'" + a.replace("'", "''") + "'" for a in expanded)
        return f"{match.group(1)}{parts}{match.group(3)}"

    sql = re.sub(
        r"(ts_code\s+IN\s*\()([^)]*)(\))",
        repl_in,
        sql,
        flags=re.IGNORECASE,
    )
    return sql


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS stock_history (
            ts_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            pre_close REAL,
            change REAL,
            pct_chg REAL,
            vol REAL,
            amount REAL,
            stock_name TEXT NOT NULL,
            UNIQUE(ts_code, trade_date)
        )
        '''
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_trade_date ON stock_history (trade_date)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_ts_code ON stock_history (ts_code)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_history (stock_name)'
    )
    # 旧表可能没有 UNIQUE，补唯一索引（忽略已存在/重复数据导致的失败）
    try:
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_ts_code_trade_date '
            'ON stock_history (ts_code, trade_date)'
        )
    except sqlite3.IntegrityError:
        # 存在重复行时先去重再建索引
        conn.execute(
            '''
            DELETE FROM stock_history
            WHERE rowid NOT IN (
                SELECT MAX(rowid) FROM stock_history
                GROUP BY ts_code, trade_date
            )
            '''
        )
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_ts_code_trade_date '
            'ON stock_history (ts_code, trade_date)'
        )
    conn.commit()


def get_latest_trade_date(conn: sqlite3.Connection, ts_code: str) -> Optional[str]:
    row = conn.execute(
        'SELECT MAX(trade_date) FROM stock_history WHERE ts_code = ?',
        (ts_code,),
    ).fetchone()
    return row[0] if row and row[0] else None


def normalize_frame(df: pd.DataFrame, ts_code: str, stock_name: str) -> pd.DataFrame:
    out = df.copy()
    out['ts_code'] = ts_code
    out['stock_name'] = stock_name
    out['trade_date'] = out['trade_date'].astype(str).map(_to_iso)
    for col in HISTORY_COLS:
        if col not in out.columns:
            out[col] = None
    out = out[HISTORY_COLS]
    out = out.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
    out = out.sort_values('trade_date').reset_index(drop=True)
    return out


def fetch_via_tushare(ts_code: str, start_date: str, end_date: str, token: str) -> pd.DataFrame:
    import tushare as ts

    ts.set_token(token)
    pro = ts.pro_api()
    df = pro.daily(ts_code=ts_code, start_date=_to_ymd(start_date), end_date=_to_ymd(end_date))
    if df is None or df.empty:
        return pd.DataFrame(columns=HISTORY_COLS)
    return df


def _clear_proxy_env() -> None:
    """避免系统代理导致行情接口连接失败。"""
    for key in (
        'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
        'ALL_PROXY', 'all_proxy',
    ):
        os.environ.pop(key, None)
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'


def fetch_via_akshare_us(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    美股日线：优先新浪 stock_us_daily；失败时回退东方财富 stock_us_hist。
    ts_code 形如 COHR.US 或 COHR。
    """
    import akshare as ak

    _clear_proxy_env()
    symbol = ts_code.split('.')[0].upper()
    start_iso = _to_iso(start_date)
    end_iso = _to_iso(end_date)

    raw = None
    try:
        raw = ak.stock_us_daily(symbol=symbol, adjust='')
    except Exception:
        raw = None

    if raw is not None and not raw.empty:
        # 列: date, open, high, low, close, volume
        df = pd.DataFrame({
            'trade_date': pd.to_datetime(raw['date']).dt.strftime('%Y-%m-%d'),
            'open': raw['open'],
            'high': raw['high'],
            'low': raw['low'],
            'close': raw['close'],
            'vol': raw['volume'],  # 美股为股数
            'amount': None,
        })
        df = df[(df['trade_date'] >= start_iso) & (df['trade_date'] <= end_iso)]
        if df.empty:
            return pd.DataFrame(columns=HISTORY_COLS)
        df = df.reset_index(drop=True)
        df['pre_close'] = df['close'].shift(1)
        df['change'] = df['close'] - df['pre_close']
        df['pct_chg'] = (df['change'] / df['pre_close'] * 100).round(4)
        return df

    # 回退：东方财富需带市场前缀的「代码」字段，从 spot 表查找
    spot = ak.stock_us_spot_em()
    code_col = '代码' if '代码' in spot.columns else spot.columns[0]
    name_col = '名称' if '名称' in spot.columns else None
    match = spot[spot[code_col].astype(str).str.upper().str.endswith(symbol)]
    if match.empty and name_col:
        match = spot[spot[name_col].astype(str).str.upper() == symbol]
    if match.empty:
        return pd.DataFrame(columns=HISTORY_COLS)

    em_symbol = str(match.iloc[0][code_col])
    hist = ak.stock_us_hist(
        symbol=em_symbol,
        period='daily',
        start_date=_to_ymd(start_date),
        end_date=_to_ymd(end_date),
        adjust='',
    )
    if hist is None or hist.empty:
        return pd.DataFrame(columns=HISTORY_COLS)

    df = pd.DataFrame({
        'trade_date': pd.to_datetime(hist['日期']).dt.strftime('%Y-%m-%d'),
        'open': hist['开盘'],
        'high': hist['最高'],
        'low': hist['最低'],
        'close': hist['收盘'],
        'change': hist['涨跌额'] if '涨跌额' in hist.columns else None,
        'pct_chg': hist['涨跌幅'] if '涨跌幅' in hist.columns else None,
        'vol': hist['成交量'] if '成交量' in hist.columns else None,
        'amount': (hist['成交额'] / 1000.0) if '成交额' in hist.columns else None,
    })
    if df['change'].isna().all():
        df['pre_close'] = df['close'].shift(1)
        df['change'] = df['close'] - df['pre_close']
        df['pct_chg'] = (df['change'] / df['pre_close'] * 100).round(4)
    else:
        df['pre_close'] = df['close'] - df['change']
    return df


def fetch_via_akshare(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    优先用新浪日线接口（stock_zh_a_daily），比东方财富 hist 更稳；
    失败时再回退 stock_zh_a_hist。美股走 fetch_via_akshare_us。
    """
    if is_us_stock(ts_code):
        return fetch_via_akshare_us(ts_code, start_date, end_date)

    import akshare as ak

    _clear_proxy_env()
    code6 = ts_code.split('.')[0]
    market = 'sh' if ts_code.endswith('.SH') else 'sz'
    sina_symbol = f'{market}{code6}'

    raw = None
    try:
        raw = ak.stock_zh_a_daily(
            symbol=sina_symbol,
            start_date=_to_ymd(start_date),
            end_date=_to_ymd(end_date),
            adjust='',
        )
    except Exception:
        raw = None

    if raw is not None and not raw.empty:
        # 列: date, open, high, low, close, volume, amount, ...
        df = pd.DataFrame({
            'trade_date': pd.to_datetime(raw['date']).dt.strftime('%Y-%m-%d'),
            'open': raw['open'],
            'high': raw['high'],
            'low': raw['low'],
            'close': raw['close'],
            # 新浪 volume 为股，tushare vol 为手
            'vol': raw['volume'] / 100.0,
            # tushare amount 为千元
            'amount': raw['amount'] / 1000.0,
        })
        df['pre_close'] = df['close'].shift(1)
        df['change'] = df['close'] - df['pre_close']
        df['pct_chg'] = (df['change'] / df['pre_close'] * 100).round(4)
        # 第一行没有前收，保留 NaN
        return df

    # 回退东方财富接口
    hist = ak.stock_zh_a_hist(
        symbol=code6,
        period='daily',
        start_date=_to_ymd(start_date),
        end_date=_to_ymd(end_date),
        adjust='',
    )
    if hist is None or hist.empty:
        return pd.DataFrame(columns=HISTORY_COLS)

    df = pd.DataFrame({
        'trade_date': hist['日期'],
        'open': hist['开盘'],
        'high': hist['最高'],
        'low': hist['最低'],
        'close': hist['收盘'],
        'change': hist['涨跌额'],
        'pct_chg': hist['涨跌幅'],
        'vol': hist['成交量'],
        'amount': hist['成交额'] / 1000.0,
    })
    df['pre_close'] = df['close'] - df['change']
    return df


def fetch_stock_data(
    ts_code: str,
    start_date: str,
    end_date: str,
    source: str,
    token: str = '',
) -> pd.DataFrame:
    # 美股：tushare daily 不覆盖，统一走 akshare
    if is_us_stock(ts_code):
        return fetch_via_akshare_us(ts_code, start_date, end_date)
    if source == 'tushare':
        return fetch_via_tushare(ts_code, start_date, end_date, token)
    return fetch_via_akshare(ts_code, start_date, end_date)


def upsert_rows(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    sql = '''
        INSERT INTO stock_history (
            ts_code, trade_date, open, high, low, close,
            pre_close, change, pct_chg, vol, amount, stock_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ts_code, trade_date) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            pre_close=excluded.pre_close,
            change=excluded.change,
            pct_chg=excluded.pct_chg,
            vol=excluded.vol,
            amount=excluded.amount,
            stock_name=excluded.stock_name
    '''
    rows = [
        (
            r.ts_code, r.trade_date, float(r.open), float(r.high), float(r.low), float(r.close),
            None if pd.isna(r.pre_close) else float(r.pre_close),
            None if pd.isna(r.change) else float(r.change),
            None if pd.isna(r.pct_chg) else float(r.pct_chg),
            None if pd.isna(r.vol) else float(r.vol),
            None if pd.isna(r.amount) else float(r.amount),
            r.stock_name,
        )
        for r in df.itertuples(index=False)
    ]
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def resolve_source(preferred: str = 'auto') -> tuple[str, str]:
    token = (os.environ.get('TUSHARE_TOKEN') or '').strip()
    if preferred == 'tushare':
        if not token:
            raise RuntimeError('已指定 --source tushare，但未设置环境变量 TUSHARE_TOKEN')
        return 'tushare', token
    if preferred == 'akshare':
        return 'akshare', ''
    # auto：优先 akshare（更稳、免 token），必要时可再切 tushare
    return 'akshare', token


def _db_max_trade_date() -> Optional[str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute('SELECT MAX(trade_date) FROM stock_history').fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def _any_watched_stock_stale(today: str) -> bool:
    """
    任一关注股票缺失或最新交易日早于 today，则需要刷新。
    避免 A 股已更新到今天时，跳过仍滞后的美股。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        ensure_schema(conn)
        for ts_code in STOCK_LIST:
            latest = get_latest_trade_date(conn, ts_code)
            if not latest or latest < today:
                conn.close()
                return True
        conn.close()
        return False
    except Exception:
        return True


def update_stock_data(
    full: bool = False,
    export_excel: bool = False,
    source: str = 'auto',
    quiet: bool = False,
) -> dict:
    """
    拉取并写入股票数据。
    quiet=True 时减少控制台输出，供助手内自动调用。
    返回汇总 dict：upserted / max_date / skipped / errors 等。
    """
    def log(msg: str = '') -> None:
        if not quiet:
            print(msg)

    os.chdir(SCRIPT_DIR)
    _clear_proxy_env()
    today = datetime.now().strftime('%Y-%m-%d')
    today_ymd = _to_ymd(today)

    data_source, token = resolve_source(source)
    log('股票数据更新工具')
    log('=' * 50)
    log(f'数据库: {DB_PATH}')
    log(f'系统当前日期: {today}')
    log(f'模式: {"全量" if full else "增量"}')
    log(f'数据源: {data_source}')
    log('=' * 50)

    if data_source == 'akshare':
        try:
            import akshare  # noqa: F401
        except ImportError:
            log('未安装 akshare，正在尝试安装...')
            import subprocess
            import sys
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'akshare', '-q'])

    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)

    all_frames: Dict[str, pd.DataFrame] = {}
    total_upserted = 0
    errors: list = []
    skipped = 0

    for ts_code, stock_name in STOCK_LIST.items():
        latest = None
        if full:
            start_date = '2020-01-01'
        else:
            latest = get_latest_trade_date(conn, ts_code)
            if latest:
                start_date = (
                    datetime.strptime(_to_iso(latest), '%Y-%m-%d') + timedelta(days=1)
                ).strftime('%Y-%m-%d')
            else:
                start_date = '2020-01-01'

        if _to_ymd(start_date) > today_ymd:
            log(f'\n{stock_name}({ts_code}) 已是最新，最新交易日={latest}')
            skipped += 1
            continue

        log(f'\n正在获取 {stock_name}({ts_code}) : {start_date} -> {today} ...')
        try:
            try:
                raw = fetch_stock_data(ts_code, start_date, today, data_source, token)
            except Exception as primary_err:
                # auto 模式下 akshare 失败且有 token 时，再试 tushare
                if source == 'auto' and data_source == 'akshare' and token:
                    log(f'  akshare 失败（{primary_err}），回退 tushare ...')
                    raw = fetch_stock_data(ts_code, start_date, today, 'tushare', token)
                elif source == 'auto' and data_source == 'tushare':
                    log(f'  tushare 失败（{primary_err}），回退 akshare ...')
                    raw = fetch_stock_data(ts_code, start_date, today, 'akshare')
                else:
                    raise

            if raw is None or raw.empty:
                log('  无新数据（可能尚未开市/休市）')
                skipped += 1
                continue
            df = normalize_frame(raw, ts_code, stock_name)
            # 增量时再保险过滤一次
            if not full and latest:
                df = df[df['trade_date'] > _to_iso(latest)]
            if df.empty:
                log('  无新数据（过滤后为空）')
                skipped += 1
                continue
            n = upsert_rows(conn, df)
            total_upserted += n
            all_frames[f'{stock_name}({ts_code})'] = df
            log(
                f'  SUCCESS: 写入/更新 {n} 条，'
                f'日期 {df["trade_date"].iloc[0]} ~ {df["trade_date"].iloc[-1]}'
            )
            # 避免免费接口限流
            time.sleep(0.4)
        except Exception as e:
            errors.append(f'{ts_code}: {e}')
            log(f'  ERROR: {e}')

    # 美股裸代码别名：COHR.US 同步出可被 COHR 直接查询的行
    alias_n = 0
    try:
        us_codes = conn.execute(
            "SELECT DISTINCT ts_code FROM stock_history WHERE ts_code LIKE '%.US'"
        ).fetchall()
        for (us_code,) in us_codes:
            bare = us_code[:-3]
            if not bare:
                continue
            cur = conn.execute(
                '''
                INSERT OR IGNORE INTO stock_history (
                    ts_code, trade_date, open, high, low, close,
                    pre_close, change, pct_chg, vol, amount, stock_name
                )
                SELECT ?, trade_date, open, high, low, close,
                       pre_close, change, pct_chg, vol, amount, stock_name
                FROM stock_history
                WHERE ts_code = ?
                ''',
                (bare, us_code),
            )
            if cur.rowcount and cur.rowcount > 0:
                alias_n += cur.rowcount
        conn.commit()
        if alias_n:
            log(f'\n已同步美股裸代码别名 {alias_n} 条（如 COHR.US -> COHR）')
    except Exception as e:
        log(f'\n同步美股别名失败: {e}')

    bounds = conn.execute(
        'SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM stock_history'
    ).fetchone()
    by_stock = conn.execute(
        '''
        SELECT ts_code, stock_name, MIN(trade_date), MAX(trade_date), COUNT(*)
        FROM stock_history
        GROUP BY ts_code, stock_name
        ORDER BY ts_code
        '''
    ).fetchall()
    conn.close()

    if export_excel and all_frames:
        excel_name = f'stock_data_update_{today_ymd}.xlsx'
        excel_path = os.path.join(SCRIPT_DIR, excel_name)
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for sheet_name, data in all_frames.items():
                data.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        log(f'\n本次新增数据已导出: {excel_path}')

    log('\n更新完成')
    log(f'本次写入/更新: {total_upserted} 条')
    log(f'库内总范围: {bounds[0]} ~ {bounds[1]}，共 {bounds[2]} 条')
    for ts_code, name, dmin, dmax, cnt in by_stock:
        log(f'  - {name}({ts_code}): {dmin} ~ {dmax}, {cnt} 条')

    return {
        'upserted': total_upserted,
        'skipped': skipped,
        'errors': errors,
        'min_date': bounds[0],
        'max_date': bounds[1],
        'total': bounds[2],
        'source': data_source,
        'today': today,
    }


def ensure_latest_stock_data(
    force: bool = False,
    min_interval_seconds: int = 1800,
) -> dict:
    """
    供助手自动调用：若库内最新交易日早于系统今天，则增量更新到当前日期。

    - force=True：忽略节流与“是否过期”判断，强制尝试更新
    - min_interval_seconds：同一进程内最小刷新间隔（默认 30 分钟），避免连问多次刷接口
    """
    global _LAST_ENSURE_TS, _LAST_ENSURE_RESULT

    now_ts = time.time()
    today = datetime.now().strftime('%Y-%m-%d')
    max_date = _db_max_trade_date()

    if not force and _LAST_ENSURE_RESULT is not None:
        if now_ts - _LAST_ENSURE_TS < min_interval_seconds:
            return {
                **_LAST_ENSURE_RESULT,
                'action': 'throttled',
                'message': f'距上次自动刷新不足 {min_interval_seconds} 秒，跳过',
            }

    # 最新交易日已到今天（或异常为空时仍尝试更新）
    # 注意：不能只用全局 MAX(trade_date)，否则 A 股已到今天会跳过仍滞后的美股
    if not force and max_date and max_date >= today and not _any_watched_stock_stale(today):
        result = {
            'action': 'fresh',
            'upserted': 0,
            'max_date': max_date,
            'today': today,
            'message': f'数据库已是最新（最新交易日 {max_date}）',
        }
        _LAST_ENSURE_TS = now_ts
        _LAST_ENSURE_RESULT = result
        return result

    try:
        summary = update_stock_data(full=False, export_excel=False, source='auto', quiet=True)
        result = {
            'action': 'updated',
            'message': (
                f"已自动增量更新 {summary.get('upserted', 0)} 条，"
                f"最新交易日 {summary.get('max_date')}"
            ),
            **summary,
        }
    except Exception as e:
        result = {
            'action': 'error',
            'upserted': 0,
            'max_date': max_date,
            'today': today,
            'message': f'自动更新失败: {e}',
            'errors': [str(e)],
        }

    _LAST_ENSURE_TS = now_ts
    _LAST_ENSURE_RESULT = result
    return result


def main():
    parser = argparse.ArgumentParser(description='更新 stock_data.db 到系统当前日期')
    parser.add_argument(
        '--full',
        action='store_true',
        help='全量重拉（从 2020-01-01 到今天），默认增量更新',
    )
    parser.add_argument(
        '--excel',
        action='store_true',
        help='将本次拉取到的数据额外导出为 Excel',
    )
    parser.add_argument(
        '--source',
        choices=['auto', 'tushare', 'akshare'],
        default='auto',
        help='数据源：auto=优先 akshare；tushare 需设置 TUSHARE_TOKEN',
    )
    args = parser.parse_args()
    update_stock_data(full=args.full, export_excel=args.excel, source=args.source)


if __name__ == '__main__':
    main()
