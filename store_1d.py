import sqlite3
import pickle
from typing import Optional

from nodes_1d import ID, NULL, Node, Leaf, new_id


def _id_to_str(i: Optional[ID]) -> Optional[str]:
    return None if i is None else format(i, "x")


def _id_from_str(s: Optional[str]) -> Optional[ID]:
    return None if s is None else int(s, 16)


class Store1D:
    """SQLite 持久化层：节点表、叶子表、数据表、立足叶子表，各自 id|data"""

    def __init__(self, db_path: str = "bina_1d.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        c = self.conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.execute("PRAGMA cache_size=-64000")
        c.execute("PRAGMA temp_store=MEMORY")
        c.execute("PRAGMA mmap_size=268435456")
        self.conn.commit()
        self._init_tables()
        self._node_cache = {}
        self._leaf_cache = {}
        self._auto_wal_checkpoint = True
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
            return  # 已有立足叶子，无需创建

        from nodes_1d import new_leaf
        leaf = new_leaf(up=None, data=None)
        self.put_leaf(leaf)
        c.execute("INSERT INTO entry_leaf VALUES (?)", (_id_to_str(leaf.nid),))
        self.conn.commit()

    # ---------- 立足叶子 ----------
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

    def allocate_id(self) -> ID:
        """分配一个全局唯一 ID，绝对不冲突（不再用递增计数器，避免每次都写 id_counter 表）。"""
        return new_id()

    # ---------- 节点表 ----------
    def put_node(self, node: Node, commit: bool = True):
        if node.nid is None:
            node.nid = self.allocate_id()
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO nodes VALUES (?, ?)",
                  (_id_to_str(node.nid), pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL)))
        if commit:
            self.conn.commit()
        self._node_cache[node.nid] = node

    def get_node(self, nid: ID) -> Optional[Node]:
        if nid in self._node_cache:
            return self._node_cache[nid]
        c = self.conn.cursor()
        c.execute("SELECT data FROM nodes WHERE id = ?", (_id_to_str(nid),))
        row = c.fetchone()
        if row is None:
            return None
        node = pickle.loads(row[0])
        self._node_cache[nid] = node
        return node

    # ---------- 叶子表 ----------
    def put_leaf(self, leaf: Leaf, commit: bool = True):
        if leaf.nid is None:
            leaf.nid = self.allocate_id()
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO leaves VALUES (?, ?)",
                  (_id_to_str(leaf.nid), pickle.dumps(leaf, protocol=pickle.HIGHEST_PROTOCOL)))
        if commit:
            self.conn.commit()
        self._leaf_cache[leaf.nid] = leaf

    def get_leaf(self, lid: ID) -> Optional[Leaf]:
        if lid in self._leaf_cache:
            return self._leaf_cache[lid]
        c = self.conn.cursor()
        c.execute("SELECT data FROM leaves WHERE id = ?", (_id_to_str(lid),))
        row = c.fetchone()
        if row is None:
            return None
        leaf = pickle.loads(row[0])
        self._leaf_cache[lid] = leaf
        return leaf

    # ---------- 数据表 ----------
    def put_data(self, data_id: ID, payload: bytes, commit: bool = True):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO data_table VALUES (?, ?)",
                  (_id_to_str(data_id), pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)))
        if commit:
            self.conn.commit()

    def put_nodes_batch(self, nodes: list, commit: bool = True):
        """批量写入节点，一次性 executemany，减少 Python-SQLite 往返开销。"""
        rows = []
        for node in nodes:
            if node.nid is None:
                node.nid = self.allocate_id()
            rows.append((
                _id_to_str(node.nid),
                pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL),
            ))
            self._node_cache[node.nid] = node
        if rows:
            c = self.conn.cursor()
            c.executemany("INSERT OR REPLACE INTO nodes VALUES (?, ?)", rows)
            if commit:
                self.conn.commit()

    def put_leaves_batch(self, leaves: list, commit: bool = True):
        """批量写入叶子，一次性 executemany，减少 Python-SQLite 往返开销。"""
        rows = []
        for leaf in leaves:
            if leaf.nid is None:
                leaf.nid = self.allocate_id()
            rows.append((
                _id_to_str(leaf.nid),
                pickle.dumps(leaf, protocol=pickle.HIGHEST_PROTOCOL),
            ))
            self._leaf_cache[leaf.nid] = leaf
        if rows:
            c = self.conn.cursor()
            c.executemany("INSERT OR REPLACE INTO leaves VALUES (?, ?)", rows)
            if commit:
                self.conn.commit()

    def wal_checkpoint(self):
        """手动触发 WAL 检查点（TRUNCATE），回收 WAL 文件空间。"""
        c = self.conn.cursor()
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.conn.commit()

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
        if not self._auto_wal_checkpoint:
            self.wal_checkpoint()
        self.conn.close()
