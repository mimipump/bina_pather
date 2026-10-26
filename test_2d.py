import os
from nodes_2d import new_node, new_leaf
from store_2d import Store2D
from query_2d import query
from nodes_2d import NULL


def build_tree(store):
    """建一棵高度为 2 的满四叉树：
    叶子 16 个 (L0..L15)，按 row-major 排列：
        y=0: L0 L1 L2 L3
        y=1: L4 L5 L6 L7
        y=2: L8 L9 L10 L11
        y=3: L12 L13 L14 L15
    层1：4 个父节点 P0..P3，每个挂 4 个叶子（按 2x2 块）
    层2：根，挂 4 个 P 节点
    """
    leaves = [new_leaf(data=f"leaf_{i}".encode()) for i in range(16)]
    for leaf in leaves:
        store.put_leaf(leaf)

    # 层1：4 个父节点，每个挂 2x2 块
    p_nodes = []
    for p_idx in range(4):
        p = new_node()
        bx = p_idx % 2   # 块在 x 方向的位置 (0=左, 1=右)
        by = p_idx // 2  # 块在 y 方向的位置 (0=上, 1=下)
        for local in range(4):
            lx = local % 2   # 块内 x (0=左, 1=右)
            ly = local // 2  # 块内 y (0=上, 1=下)
            gx = bx * 2 + lx  # 全局 x
            gy = by * 2 + ly  # 全局 y
            leaf_idx = gy * 4 + gx
            leaf = leaves[leaf_idx]
            leaf.up = p.nid
            store.put_leaf(leaf)
            slot = lx + 2 * ly  # 0=d0, 1=d1, 2=d2, 3=d3
            if slot == 0:
                p.d0 = leaf.nid
            elif slot == 1:
                p.d1 = leaf.nid
            elif slot == 2:
                p.d2 = leaf.nid
            else:
                p.d3 = leaf.nid
        store.put_node(p)
        p_nodes.append(p)

    # 根：挂 4 个 P，slot = bx + 2*by
    root = new_node()
    for p_idx, p in enumerate(p_nodes):
        p.up = root.nid
        store.put_node(p)
        bx = p_idx % 2
        by = p_idx // 2
        slot = bx + 2 * by
        if slot == 0:
            root.d0 = p.nid
        elif slot == 1:
            root.d1 = p.nid
        elif slot == 2:
            root.d2 = p.nid
        else:
            root.d3 = p.nid
    store.put_node(root)

    return root, leaves, p_nodes


def check(name, result, expected_target=None, expected_found=True):
    ok = result["found"] == expected_found
    if expected_found and expected_target is not None:
        ok = ok and result["target"] == expected_target
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: found={result['found']}, g={result.get('g')}, "
          f"uppath={result.get('uppath')}, map={result.get('map')}, "
          f"target={result.get('target')}")
    if not ok:
        print(f"  expected found={expected_found}, target={expected_target}")
    return ok


def main():
    db_path = "test_2d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store2D(db_path)

    # === 立足叶子测试 ===
    entry_id_1 = store.get_entry_leaf_id()
    assert entry_id_1 is not None, "新数据库应自动创建立足叶子"
    print(f"[INFO] 新数据库自动创建立足叶子: {entry_id_1:#x}")

    r = query(store, entry_id_1, 1, 0)
    assert r["found"] is True, "从立足叶子出发查询应成功"
    print(f"[INFO] 从立足叶子出发查询 dx=1,dy=0: target={r['target']:#x}")

    store.close()
    store = Store2D(db_path)

    entry_id_2 = store.get_entry_leaf_id()
    assert entry_id_2 == entry_id_1, "重新打开数据库后立足叶子 id 应保持不变"
    print(f"[INFO] 重新打开数据库后立足叶子 id 不变: {entry_id_2:#x}")

    root, leaves, p_nodes = build_tree(store)

    print("\n=== 基础查询测试 ===")
    # L0 和 L1 是兄弟（同 P0），L0 向右 dx=1 -> L1
    r = query(store, leaves[0].nid, 1, 0)
    check("L0 -> (1,0) L1", r, expected_target=leaves[1].nid)

    # L1 向左 dx=-1 -> L0
    r = query(store, leaves[1].nid, -1, 0)
    check("L1 -> (-1,0) L0", r, expected_target=leaves[0].nid)

    # L0 向下 dy=1 -> L4
    r = query(store, leaves[0].nid, 0, 1)
    check("L0 -> (0,1) L4", r, expected_target=leaves[4].nid)

    # L4 向上 dy=-1 -> L0
    r = query(store, leaves[4].nid, 0, -1)
    check("L4 -> (0,-1) L0", r, expected_target=leaves[0].nid)

    print("\n=== 跨层查询测试 ===")
    # L0 -> L2：同行，跨 P0/P1，共顶是根
    r = query(store, leaves[0].nid, 2, 0)
    check("L0 -> (2,0) L2", r, expected_target=leaves[2].nid)

    # L0 -> L8：同列，跨 P0/P2，共顶是根
    r = query(store, leaves[0].nid, 0, 2)
    check("L0 -> (0,2) L8", r, expected_target=leaves[8].nid)

    # L0 -> L15：最远，dx=3,dy=3，共顶是根
    r = query(store, leaves[0].nid, 3, 3)
    check("L0 -> (3,3) L15", r, expected_target=leaves[15].nid)

    # L15 -> L0：dx=-3,dy=-3
    r = query(store, leaves[15].nid, -3, -3)
    check("L15 -> (-3,-3) L0", r, expected_target=leaves[0].nid)

    # L1 -> L6：dx=1,dy=1，L1(1,0) -> L6(2,1)
    r = query(store, leaves[1].nid, 1, 1)
    check("L1 -> (1,1) L6", r, expected_target=leaves[6].nid)

    print("\n=== 边界测试 ===")
    # d=(0,0) 应该返回自身
    r = query(store, leaves[7].nid, 0, 0)
    check("L7 -> (0,0) 自身", r, expected_target=leaves[7].nid)

    # 向左扩展：L0 向左 dx=-1，建立新左邻
    r = query(store, leaves[0].nid, -1, 0)
    check("L0 -> (-1,0) 建立左邻", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    # 向右扩展：L3 向右 dx=1，建立新右邻
    r = query(store, leaves[3].nid, 1, 0)
    check("L3 -> (1,0) 建立右邻", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    # 向下扩展：L12 向下 dy=1，建立新下邻
    r = query(store, leaves[12].nid, 0, 1)
    check("L12 -> (0,1) 建立下邻", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    # 斜向扩展：L0 向左上 dx=-1,dy=-1
    r = query(store, leaves[0].nid, -1, -1)
    check("L0 -> (-1,-1) 建立左上邻", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    store.close()
    print("\n全部测试完成")


if __name__ == "__main__":
    main()
