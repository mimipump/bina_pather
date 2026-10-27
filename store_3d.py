import sqlite3
import pickle
from typing import Optional

from nodes_3d import ID, NULL, Node, Leaf, new_id


def _id_to_str(i: Optional[ID]) -> Optional[str]:
    return None if i is None else format(i, "x")


def _id_from_str(s: Optional[str]) -> Optional[ID]:
    return None if s is None else int(s, 16)


class Store3D:
    """SQLite 持久化层（三维）：节点表、叶子表、数据表、立足叶子表，各自 id|data"""

    def __init__(self, db_path: str = "bina_3d.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
        self._ensure_entry_leaf()

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
        c.execute("""
            CREATE TABLE IF NOT EXISTS entry_leaf (
                id TEXT PRIMARY KEY
            )
        """)
        self.conn.commit()

    def _ensure_entry_leaf(self):
        """数据库首次创建时，自动生成一个立足叶子并写入 entry_leaf 表。"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM entry_leaf LIMIT 1")
        row = c.fetchone()
        if row is not None:
            return

        from nodes_3d import new_leaf
        leaf = new_leaf(up=None, data=None)
        self.put_leaf(leaf)
        c.execute("INSERT INTO entry_leaf VALUES (?)", (_id_to_str(leaf.nid),))
        self.conn.commit()

    def get_entry_leaf_id(self) -> Optional[ID]:
        c = self.conn.cursor()
        c.execute("SELECT id FROM entry_leaf LIMIT 1")
        row = c.fetchone()
        if row is None:
            return None
        return _id_from_str(row[0])

    def set_entry_leaf(self, nid: ID) -> None:
        c = self.conn.cursor()
        c.execute("DELETE FROM entry_leaf")
        c.execute("INSERT INTO entry_leaf VALUES (?)", (_id_to_str(nid),))
        self.conn.commit()

    def put_node(self, node: Node):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO nodes VALUES (?, ?)",
                  (_id_to_str(node.nid), pickle.dumps(node)))

    def get_node(self, nid: ID) -> Optional[Node]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM nodes WHERE id = ?", (_id_to_str(nid),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def put_leaf(self, leaf: Leaf):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO leaves VALUES (?, ?)",
                  (_id_to_str(leaf.nid), pickle.dumps(leaf)))

    def get_leaf(self, lid: ID) -> Optional[Leaf]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM leaves WHERE id = ?", (_id_to_str(lid),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def put_data(self, data_id: ID, payload: bytes):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO data_table VALUES (?, ?)",
                  (_id_to_str(data_id), pickle.dumps(payload)))

    def get_data(self, data_id: ID) -> Optional[bytes]:
        c = self.conn.cursor()
        c.execute("SELECT data FROM data_table WHERE id = ?", (_id_to_str(data_id),))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()
