from typing import Optional, Dict, Any

from nodes_2d_base import ID, NULL, Node, BaseLeaf, new_id, new_node, new_base_leaf
from store_2d import Store2D


def slot_of(parent: Node, child_id: ID) -> int:
    """返回 child 在 parent 中的口号（编号）：0~3。
    口号 = x + 2y，x 为最低位。
    """
    if parent.d0 == child_id:
        return 0
    if parent.d1 == child_id:
        return 1
    if parent.d2 == child_id:
        return 2
    if parent.d3 == child_id:
        return 3
    raise ValueError(
        f"子节点 {child_id:#x} 不在父节点 {parent.nid:#x} 的任何口中，数据不一致"
    )


def deinterleave(uppath: int, g: int) -> tuple[int, int]:
    """从 base-4 uppath 中分离出 x、y 两个二进制路径。

    位运算优化版：uppath 位布局为 ... y2 x2 y1 x1 y0 x0，
    每次迭代提取最低两位，x 取 bit0，y 取 bit1，然后右移 2 位。
    """
    x = 0
    y = 0
    m = uppath
    for i in range(g + 1):
        x |= (m & 1) << i
        y |= ((m >> 1) & 1) << i
        m >>= 2
    return x, y


def interleave(map_x: int, map_y: int, g: int) -> int:
    """把 x、y 两个二进制地图按位打包成 base-4 地图（无进位）。

    位运算优化版：每位 x_bit 放到 2*i，y_bit 放到 2*i+1。
    """
    result = 0
    for i in range(g + 1):
        result |= ((map_x >> i) & 1) << (2 * i)
        result |= ((map_y >> i) & 1) << (2 * i + 1)
    return result


def _get_node(store: Store2D, nid: ID) -> Optional[Node | BaseLeaf]:
    node = store.get_node(nid)
    if node is None:
        node = store.get_leaf(nid)
    return node


def query(store: Store2D, knowed_node_id: ID, dx: int, dy: int, _commit: bool = True, readonly: bool = False) -> Dict[str, Any]:
    """二维查询（无 nbr 版本）：从已知叶子节点出发，索引偏移 (dx, dy) 处的目标叶子。

    单路径查询：从起点唯一向上爬树，直到两个维度均满足共顶条件，
    再从共顶按 base-4 地图下行到目标叶子。
    内部动态建节点延迟提交，查询结束前统一 commit。

    readonly 为 True 时，不建立任何新节点；缺失路径直接返回 found=False。

    返回字典：
        g          - 共顶层数（break 时的 i）
        uppath     - 从叶子到共顶的 base-4 位图（g+1 位，每位 2 bit）
        map_val    - 从共顶到目标的 base-4 地图（g+1 位，每位 2 bit）
        common_top - 共顶节点 id
        target     - 目标叶子 id
    """
    try:
        if dx == 0 and dy == 0:
            node = _get_node(store, knowed_node_id)
            if node is None:
                return {"found": False, "reason": "未知节点", "g": -1}
            return {
                "found": True,
                "g": 0,
                "uppath": 0,
                "map": 0,
                "common_top": None,
                "target": knowed_node_id,
            }

        sumDx = 0
        sumDy = 0
        uppath = 0
        g = -1
        max_iter = 1 << 30

        this_node_id = knowed_node_id

        # 载入起点节点（节点或叶子），记入全流程本地缓存
        visited: dict[ID, Any] = {}
        this_node = store.get_node(this_node_id)
        if this_node is None:
            this_node = store.get_leaf(this_node_id)
            if this_node is None:
                if readonly:
                    return {"found": False, "reason": "未知节点", "g": -1}
                raise ValueError(f"未知节点 {knowed_node_id:#x}")
        visited[this_node_id] = this_node

        for i in range(max_iter):
            if this_node.up is None:
                if readonly:
                    return {
                        "found": False,
                        "reason": "只读模式：无法建立上级",
                        "g": -1,
                    }
                slot = (1 if dx < 0 else 0) + 2 * (1 if dy < 0 else 0)
                parent = new_node(up=None, d0=None, d1=None, d2=None, d3=None)
                if slot == 0:
                    parent.d0 = this_node_id
                elif slot == 1:
                    parent.d1 = this_node_id
                elif slot == 2:
                    parent.d2 = this_node_id
                else:
                    parent.d3 = this_node_id
                store.put_node(parent, commit=False)
                visited[parent.nid] = parent
                if isinstance(this_node, BaseLeaf):
                    this_node.up = parent.nid
                    store.put_leaf(this_node, commit=False)
                else:
                    this_node.up = parent.nid
                    store.put_node(this_node, commit=False)
                visited[this_node_id] = this_node
                parent_node = parent
                bit = slot
            else:
                parent_node = store.get_node(this_node.up)
                if parent_node is None:
                    if readonly:
                        return {
                            "found": False,
                            "reason": "只读模式：父节点不存在",
                            "g": -1,
                        }
                    raise ValueError(f"父节点 {this_node.up:#x} 不存在")
                visited[parent_node.nid] = parent_node
                visited[this_node_id] = this_node
                bit = slot_of(parent_node, this_node_id)

            uppath |= (bit << (2 * i))

            x_bit = bit & 1
            y_bit = (bit >> 1) & 1
            if (dx < 0) == x_bit:
                sumDx += (1 << i)
            if (dy < 0) == y_bit:
                sumDy += (1 << i)

            if abs(sumDx) >= abs(dx) and abs(sumDy) >= abs(dy):
                g = i
                break

            this_node_id = parent_node.nid
            this_node = parent_node

        if g < 0:
            return {
                "found": False,
                "reason": "循环耗尽，未找到共顶",
                "g": -1,
            }

        common_top_id = this_node.up
        common_top = store.get_node(common_top_id)
        if common_top is None:
            common_top = store.get_leaf(common_top_id)
        if common_top is None:
            if readonly:
                return {
                    "found": False,
                    "reason": "只读模式：共顶节点不存在",
                    "g": -1,
                }
            raise ValueError(f"共顶节点 {common_top_id:#x} 不存在")
        visited[common_top_id] = common_top

        mask = (1 << (g + 1)) - 1
        uppath_x, uppath_y = deinterleave(uppath, g)
        map_x = (uppath_x + dx) & mask
        map_y = (uppath_y + dy) & mask
        map_val = interleave(map_x, map_y, g)

        cur_id = common_top_id
        for bit_pos in range(g, -1, -1):
            slot = (map_val >> (2 * bit_pos)) & 3
            # 优先从本地缓存取，避免重复 SQL 和 pickle 反序列化
            cur_node = visited.get(cur_id)
            if cur_node is None:
                cur_node = store.get_node(cur_id)
                if cur_node is None:
                    cur_node = store.get_leaf(cur_id)
                    if cur_node is None:
                        if readonly:
                            return {
                                "found": False,
                                "reason": "只读模式：下行节点不存在",
                                "g": -1,
                            }
                        raise ValueError(f"下行时节点 {cur_id:#x} 不存在")
                visited[cur_id] = cur_node

            if isinstance(cur_node, BaseLeaf) and bit_pos > 0:
                if readonly:
                    return {
                        "found": False,
                        "reason": "只读模式：树结构不完整",
                        "g": -1,
                    }
                raise ValueError(
                    f"下行时遇到叶子节点 {cur_id:#x}，但还未到达第 {bit_pos} 层，"
                    "树结构不完整"
                )

            children = [cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3]
            nxt = children[slot]

            if nxt is None:
                if readonly:
                    return {
                        "found": False,
                        "reason": "只读模式：目标路径不存在",
                        "g": -1,
                    }
                if bit_pos == 0:
                    new_leaf_node = new_base_leaf(up=cur_id, data=None)
                    store.put_leaf(new_leaf_node, commit=False)
                    visited[new_leaf_node.nid] = new_leaf_node
                    children[slot] = new_leaf_node.nid
                    cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3 = children
                    store.put_node(cur_node, commit=False)
                    visited[cur_node.nid] = cur_node
                    cur_id = new_leaf_node.nid
                else:
                    new_node_obj = Node(nid=None, up=cur_id, d0=None, d1=None, d2=None, d3=None)
                    store.put_node(new_node_obj, commit=False)
                    visited[new_node_obj.nid] = new_node_obj
                    children[slot] = new_node_obj.nid
                    cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3 = children
                    store.put_node(cur_node, commit=False)
                    visited[cur_node.nid] = cur_node
                    cur_id = new_node_obj.nid
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
    finally:
        if _commit:
            store.commit()


def batch_query(store: Store2D, queries: list) -> list:
    """批量二维查询（无 nbr 版本）。

    queries: list of (node_id, dx, dy)
    返回: list of result dict，顺序与 queries 一致。
    内部所有查询共享一次事务提交，避免重复 fsync。
    """
    results = []
    for node_id, dx, dy in queries:
        results.append(query(store, node_id, dx, dy, _commit=False))
    store.commit()
    if store._auto_wal_checkpoint:
        store.wal_checkpoint()
    return results
