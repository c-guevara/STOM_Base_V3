
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional


class DatabaseManager:
    def __init__(self):
        DB_PATH = Path(__file__).parent.parent.parent / "_database"
        self.tradelist_db = f"{DB_PATH}/tradelist.db"

    def get_jangolist(self, market: str = "stock") -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.tradelist_db)
        table_name = f"{market}_jangolist"
        try:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            return df.to_dict('records')
        except Exception as e:
            print(f"Position list query error: {e}")
            return []
        finally:
            conn.close()

    def get_chegeollist(self, market: str = "stock", limit: int = 20) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.tradelist_db, check_same_thread=False)
        table_name = f"{market}_chegeollist"
        try:
            # 컬럼명에 백틱 사용하여 특수문자/한글 처리
            query = f'SELECT * FROM "{table_name}" ORDER BY "체결시간" DESC LIMIT ?'
            df = pd.read_sql(query, conn, params=(limit,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Execution list query error: {e}")
            return []
        finally:
            conn.close()

    def get_tradelist(self, market: str = "stock", limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.tradelist_db, check_same_thread=False)
        table_name = f"{market}_tradelist"
        try:
            # 컬럼명에 백틱 사용하여 특수문자/한글 처리
            query = f'SELECT * FROM "{table_name}" ORDER BY "체결시간" DESC LIMIT ?'
            df = pd.read_sql(query, conn, params=(limit,))
            return df.to_dict('records')
        except Exception as e:
            print(f"Trade list query error: {e}")
            return []
        finally:
            conn.close()

    def get_totaltradelist(self, market: str = "stock") -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.tradelist_db)
        table_name = f"{market}_totaltradelist"
        try:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            if len(df) > 0:
                return df.to_dict('records')[0]
            return None
        except Exception as e:
            print(f"Total trade summary query error: {e}")
            return None
        finally:
            conn.close()
