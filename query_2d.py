from typing import Optional, Dict, Any

from nodes_2d import ID, NULL, Node, Leaf, new_id, new_node, new_leaf
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
    """从 base-4 uppath 中分离出 x、y 两个二进制路径。"""
    x = 0
    y = 0
    for i in range(g + 1):
        slot = (uppath >> (2 * i)) & 3
        x_bit = slot & 1
        y_bit = (slot >> 1) & 1
        x |= x_bit << i
        y |= y_bit << i
    return x, y


def interleave(map_x: int, map_y: int, g: int) -> int:
    """把 x、y 两个二进制地图按位打包成 base-4 地图（无进位）。"""
    result = 0
    for i in range(g + 1):
        x_bit = (map_x >> i) & 1
        y_bit = (map_y >> i) & 1
        result |= (x_bit + 2 * y_bit) << (2 * i)
    return result


def query(store: Store2D, knowed_node_id: ID, dx: int, dy: int) -> Dict[str, Any]:
    """二维查询：从已知叶子节点出发，索引偏移 (dx, dy) 处的目标叶子。

    返回字典：
        g          - 共顶层数（break 时的 i）
        uppath     - 从叶子到共顶的 base-4 位图（g+1 位，每位 2 bit）
        map_val    - 从共顶到目标的 base-4 地图（g+1 位，每位 2 bit）
        common_top - 共顶节点 id
        target     - 目标叶子 id
    """
    sumDx = 0
    sumDy = 0
    uppath = 0
    g = -1
    max_iter = 1 << 30

    this_node_id = knowed_node_id

    this_node = store.get_node(this_node_id)
    if this_node is None:
        this_node = store.get_leaf(this_node_id)
        if this_node is None:
            raise ValueError(f"未知节点 {knowed_node_id:#x}")

    for i in range(max_iter):
        if this_node.up is None:
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

    mask = (1 << (g + 1)) - 1
    uppath_x, uppath_y = deinterleave(uppath, g)
    map_x = (uppath_x + dx) & mask
    map_y = (uppath_y + dy) & mask
    map_val = interleave(map_x, map_y, g)

    cur_id = common_top_id
    for bit_pos in range(g, -1, -1):
        slot = (map_val >> (2 * bit_pos)) & 3
        cur_node = store.get_node(cur_id)
        if cur_node is None:
            cur_node = store.get_leaf(cur_id)
            if cur_node is None:
                raise ValueError(f"下行时节点 {cur_id:#x} 不存在")

        if isinstance(cur_node, Leaf) and bit_pos > 0:
            raise ValueError(
                f"下行时遇到叶子节点 {cur_id:#x}，但还未到达第 {bit_pos} 层，"
                "树结构不完整"
            )

        children = [cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3]
        nxt = children[slot]

        if nxt is None:
            if bit_pos == 0:
                new_leaf_node = new_leaf(up=cur_id, data=None)
                store.put_leaf(new_leaf_node)
                children[slot] = new_leaf_node.nid
                cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3 = children
                store.put_node(cur_node)
                cur_id = new_leaf_node.nid
            else:
                new_node_obj = Node(nid=new_id(), up=cur_id, d0=None, d1=None, d2=None, d3=None)
                store.put_node(new_node_obj)
                children[slot] = new_node_obj.nid
                cur_node.d0, cur_node.d1, cur_node.d2, cur_node.d3 = children
                store.put_node(cur_node)
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
