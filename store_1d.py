import sqlite3
import pickle
import os
from typing import Optional

from nodes_1d import ID, NULL, Node, Leaf, new_id


def _id_to_str(i: Optional[ID]) -> Optional[str]:
    return None if i is None else format(i, "x")


def _id_from_str(s: Optional[str]) -> Optional[ID]:
    return None if s is None else int(s, 16)


class Store1D:
    """SQLite 持久化层：节点表、叶子表、数据表，各自 id|data"""

    def __init__(self, db_path: str = "bina_1d.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                data BLOB
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS leaves (
                id TEXT PRIMARY KEY,
                data BLOB
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS data_table (
                id TEXT PRIMARY KEY,
                data BLOB
            )
        """)
        self.conn.commit()

    # ---------- 节点表 ----------
    def put_node(self, node: Node):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO nodes VALUES (?, ?)",
                  (_id_to_str(node.nid), pickle.dumps(node)))
        self.conn.commit()

    def get_node(self, nid: ID) -> Optional[Node]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM nodes WHERE id = ?", (_id_to_str(nid),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    # ---------- 叶子表 ----------
    def put_leaf(self, leaf: Leaf):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO leaves VALUES (?, ?)",
                  (_id_to_str(leaf.nid), pickle.dumps(leaf)))
        self.conn.commit()

    def get_leaf(self, lid: ID) -> Optional[Leaf]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM leaves WHERE id = ?", (_id_to_str(lid),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    # ---------- 数据表 ----------
    def put_data(self, data_id: ID, payload: bytes):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO data_table VALUES (?, ?)",
                  (_id_to_str(data_id), pickle.dumps(payload)))
        self.conn.commit()

    def get_data(self, data_id: ID) -> Optional[bytes]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM data_table WHERE id = ?",
                  (_id_to_str(data_id),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def close(self):
        self.conn.close()
