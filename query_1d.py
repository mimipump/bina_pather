from typing import Optional, Dict, Any

from nodes_1d import ID, NULL, Node, Leaf, new_id, new_node, new_leaf
from store_1d import Store1D


def slot_of(parent: Node, child_id: ID) -> int:
    """返回 child 在 parent 中的口号（编号）：0 或 1。
    扫描父节点的 d0/d1，找到匹配 child_id 的口。
    全不匹配说明数据不一致（悬空引用）。
    """
    if parent.d0 == child_id:
        return 0
    if parent.d1 == child_id:
        return 1
    raise ValueError(
        f"子节点 {child_id:#x} 不在父节点 {parent.nid:#x} 的任何口中，数据不一致"
    )


def query(store: Store1D, knowed_node_id: ID, d: int) -> Dict[str, Any]:
    """一维查询：从已知叶子节点出发，索引距离 d 处的目标叶子。

    返回字典：
        g          - 共顶层数（break 时的 i）
        uppath     - 从叶子到共顶的位图（g+1 位）
        map_val    - 从共顶到目标的二进制地图（g+1 位）
        common_top - 共顶节点 id
        target     - 目标叶子 id
    """
    sumD = 0
    uppath = 0
    g = -1
    max_iter = 1 << 30   # 一个很大且合理的数

    this_node_id = knowed_node_id

    # 载入起点节点（叶子或普通节点）
    this_node = store.get_node(this_node_id)
    if this_node is None:
        this_node = store.get_leaf(this_node_id)
        if this_node is None:
            raise ValueError(f"未知节点 {knowed_node_id:#x}")

    for i in range(max_iter):
        # --- 确保 this_node 有上级 ---
        if this_node.up is None:
            # 没有上级，建立一个合法上级，把当前节点挂到指定口
            # slot 由 d 的方向决定：d<0 时放右口(1)，d>=0 时放左口(0)
            slot = 1 if d < 0 else 0
            parent = new_node(up=None, d0=None, d1=None)
            if slot == 0:
                parent.d0 = this_node_id
            else:
                parent.d1 = this_node_id
            store.put_node(parent)
            if isinstance(this_node, Leaf):
                this_node.up = parent.nid
                store.put_leaf(this_node)
            else:
                this_node.up = parent.nid
                store.put_node(this_node)
            parent_node = parent
        else:
            parent_node = store.get_node(this_node.up)
            if parent_node is None:
                raise ValueError(f"父节点 {this_node.up:#x} 不存在")

        # --- 记录本级编号（uppath 的第 i 位） ---
        bit = slot_of(parent_node, this_node_id)
        uppath |= (bit << i)

        # --- sumD 累加 ---
        if (d < 0) == bit:
            sumD += (1 << i)

        # --- 判断是否到达共顶 ---
        if abs(sumD) >= abs(d):
            g = i
            break

        # --- 上爬到父节点 ---
        this_node_id = parent_node.nid
        this_node = parent_node

    # 循环结束
    if g < 0:
        return {
            "found": False,
            "reason": "循环耗尽，未找到共顶",
            "g": -1,
        }

    # g >= 0：找到了共顶
    # this_node 是第 g 层节点，this_node.up 是第 g+1 层（共顶）
    common_top_id = this_node.up
    common_top = store.get_node(common_top_id)
    if common_top is None:
        common_top = store.get_leaf(common_top_id)

    # uppath 与 d 加和，得到从共顶访问到目标的二进制地图（g+1 位）
    map_val = (uppath + d) & ((1 << (g + 1)) - 1)

    # 从共顶出发，按地图位从高位到低位下行，找到目标叶子
    cur_id = common_top_id
    for bit_pos in range(g, -1, -1):
        bit = (map_val >> bit_pos) & 1
        cur_node = store.get_node(cur_id)
        if cur_node is None:
            cur_node = store.get_leaf(cur_id)
            if cur_node is None:
                raise ValueError(f"下行时节点 {cur_id:#x} 不存在")
        if bit == 0:
            nxt = cur_node.d0 if isinstance(cur_node, Node) else None
        else:
            nxt = cur_node.d1 if isinstance(cur_node, Node) else None
        if nxt is None:
            # 目标口为空：在该处建立新的叶子节点作为目标（向左/右扩展）
            new_leaf_node = new_leaf(up=cur_id, data=None)
            store.put_leaf(new_leaf_node)
            if isinstance(cur_node, Node):
                if bit == 0:
                    cur_node.d0 = new_leaf_node.nid
                else:
                    cur_node.d1 = new_leaf_node.nid
                store.put_node(cur_node)
            else:
                raise ValueError(
                    f"第 {bit_pos} 层节点 {cur_id:#x} 不是内部节点，无法挂载子节点"
                )
            cur_id = new_leaf_node.nid
        else:
            cur_id = nxt

    target_id = cur_id

    return {
        "found": True,
        "g": g,
        "uppath": uppath,
        "map": map_val,
        "common_top": common_top_id,
        "target": target_id,
    }


def demo():
    """快速演示：建一棵小树，做一次查询。"""
    import os

    db_path = "demo_1d.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    store = Store1D(db_path)

    # 建两个叶子作为兄弟，共享同一个父节点
    leaf_a = new_leaf(up=None, data=b"data_A")
    leaf_b = new_leaf(up=None, data=b"data_B")
    store.put_leaf(leaf_a)
    store.put_leaf(leaf_b)

    # 建立父节点，把两个叶子挂上去
    parent = new_node(up=None, d0=leaf_a.nid, d1=leaf_b.nid)
    store.put_node(parent)
    leaf_a.up = parent.nid
    leaf_b.up = parent.nid
    store.put_leaf(leaf_a)
    store.put_leaf(leaf_b)

    # 查询：从 leaf_a 出发，d=1（找右兄弟）
    result = query(store, leaf_a.nid, 1)
    print("查询结果：", result)

    store.close()


if __name__ == "__main__":
    demo()
