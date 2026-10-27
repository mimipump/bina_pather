import os
import random
from nodes_2d import new_node, new_leaf
from store_2d import Store2D
from query_2d import query
from nodes_2d import NULL


def leaf_idx(x, y, size=16):
    """按 row-major 计算叶子索引：y * size + x，x 最快"""
    return y * size + x


def build_tree(store, size=16, height=4):
    """建一棵高度为 height 的满四叉树。
    叶子 size×size，坐标范围 [0, size-1]^2。
    size 必须是 2 的幂，height 必须满足 2^height >= size。
    所有层级循环顺序统一为 bx(外)→by(内)，子节点按 slot = lx + 2*ly 严格挂载。
    """
    assert size & (size - 1) == 0, "size 必须是 2 的幂"
    assert 2 ** height >= size, "height 不足以覆盖整个网格"

    total_leaves = size * size
    leaves = [new_leaf(data=f"leaf_{i}".encode()) for i in range(total_leaves)]
    for leaf in leaves:
        store.put_leaf(leaf)

    # ---------- 层1：(size/2)×(size/2) 个父节点，每个挂 4 个叶子（2×2块）----------
    blocks_per_dim = size // 2
    level1 = []
    for by in range(blocks_per_dim):
        for bx in range(blocks_per_dim):
            p = new_node()
            for ly in range(2):
                for lx in range(2):
                    gx = bx * 2 + lx
                    gy = by * 2 + ly
                    li = leaf_idx(gx, gy, size)
                    leaf = leaves[li]
                    leaf.up = p.nid
                    store.put_leaf(leaf)
                    slot = lx + 2 * ly
                    if slot == 0:
                        p.d0 = leaf.nid
                    elif slot == 1:
                        p.d1 = leaf.nid
                    elif slot == 2:
                        p.d2 = leaf.nid
                    else:
                        p.d3 = leaf.nid
            store.put_node(p)
            level1.append(p)

    # ---------- 层2~height-1：递归构建 -----------
    prev_level = level1
    prev_blocks_per_dim = blocks_per_dim
    for level in range(2, height):
        blocks_l = prev_blocks_per_dim // 2
        curr_level = []
        for by2 in range(blocks_l):
            for bx2 in range(blocks_l):
                p = new_node()
                for lby in range(2):
                    for lbx in range(2):
                        gbx = bx2 * 2 + lbx
                        gby = by2 * 2 + lby
                        p_idx = gby * prev_blocks_per_dim + gbx
                        child = prev_level[p_idx]
                        child.up = p.nid
                        store.put_node(child)
                        slot = lbx + 2 * lby
                        if slot == 0:
                            p.d0 = child.nid
                        elif slot == 1:
                            p.d1 = child.nid
                        elif slot == 2:
                            p.d2 = child.nid
                        else:
                            p.d3 = child.nid
                store.put_node(p)
                curr_level.append(p)
        prev_level = curr_level
        prev_blocks_per_dim = blocks_l

    # ---------- 根：挂 4 个顶层节点 -----------
    root = new_node()
    for i, child in enumerate(prev_level):
        child.up = root.nid
        store.put_node(child)
        rbx = i % 2
        rby = i // 2
        slot = rbx + 2 * rby
        if slot == 0:
            root.d0 = child.nid
        elif slot == 1:
            root.d1 = child.nid
        elif slot == 2:
            root.d2 = child.nid
        else:
            root.d3 = child.nid
    store.put_node(root)
    return root, leaves


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
    size = 16
    height = 4
    db_path = "test_2d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store2D(db_path)

    # === 立足叶子测试 ===
    entry_id_1 = store.get_entry_leaf_id()
    assert entry_id_1 is not None
    print(f"[INFO] 立足叶子: {entry_id_1:#x}")

    r = query(store, entry_id_1, 1, 0)
    assert r["found"] is True
    print(f"[INFO] 立足叶子查询 (1,0): target={r['target']:#x}")

    store.close()
    store = Store2D(db_path)
    entry_id_2 = store.get_entry_leaf_id()
    assert entry_id_2 == entry_id_1
    print(f"[INFO] 持久化验证通过: {entry_id_2:#x}")

    root, leaves = build_tree(store, size=size, height=height)

    print(f"\n=== 基础查询（单步，兄弟节点）===")
    tests = [
        ((0, 0), (1, 0)),
        ((1, 0), (-1, 0)),
        ((0, 0), (0, 1)),
        ((0, 1), (0, -1)),
    ]
    for (sx, sy), (dx, dy) in tests:
        src = leaves[leaf_idx(sx, sy, size)]
        dst = leaves[leaf_idx(sx + dx, sy + dy, size)]
        r = query(store, src.nid, dx, dy)
        check(f"L({sx},{sy}) -> ({dx},{dy})", r, expected_target=dst.nid)

    print(f"\n=== 跨层查询（共顶为根，size={size}）===")
    tests = [
        ((0, 0), (15, 0)),
        ((0, 0), (0, 15)),
        ((0, 0), (15, 15)),
        ((15, 15), (-15, -15)),
        ((0, 0), (7, 9)),
        ((15, 15), (-7, -9)),
        ((8, 8), (7, 7)),
        ((7, 7), (-7, -7)),
        ((0, 15), (15, -15)),
        ((15, 0), (-15, 15)),
    ]
    for (sx, sy), (dx, dy) in tests:
        src = leaves[leaf_idx(sx, sy, size)]
        tx, ty = sx + dx, sy + dy
        if 0 <= tx < size and 0 <= ty < size:
            dst = leaves[leaf_idx(tx, ty, size)]
            r = query(store, src.nid, dx, dy)
            check(f"L({sx},{sy}) -> ({dx},{dy})", r, expected_target=dst.nid)
        else:
            r = query(store, src.nid, dx, dy)
            check(f"L({sx},{sy}) -> ({dx},{dy}) 越界扩展", r, expected_found=True)

    print(f"\n=== 边界：自身查询 ===")
    for (x, y) in [(0, 0), (7, 7), (15, 15), (8, 9), (3, 12)]:
        src = leaves[leaf_idx(x, y, size)]
        r = query(store, src.nid, 0, 0)
        check(f"L({x},{y}) -> (0,0) 自身", r, expected_target=src.nid)

    print(f"\n=== 边界：向外扩展（建立新节点）===")
    expand_tests = [
        ((0, 0), (-1, 0)),
        ((15, 0), (1, 0)),
        ((0, 0), (0, -1)),
        ((0, 15), (0, 1)),
        ((0, 0), (-1, -1)),
        ((15, 15), (1, 1)),
        ((0, 15), (-1, 1)),
        ((15, 0), (1, -1)),
        ((7, 7), (-8, -8)),
        ((8, 8), (8, 8)),
    ]
    for (sx, sy), (dx, dy) in expand_tests:
        src = leaves[leaf_idx(sx, sy, size)]
        r = query(store, src.nid, dx, dy)
        check(f"L({sx},{sy}) -> ({dx},{dy}) 扩展", r, expected_found=True)

    print(f"\n=== 随机查询测试（5000 次）===")
    random.seed(42)
    pass_count = 0
    fail_count = 0
    for _ in range(5000):
        sx = random.randint(0, size - 1)
        sy = random.randint(0, size - 1)
        dx = random.randint(-15, 15)
        dy = random.randint(-15, 15)
        src = leaves[leaf_idx(sx, sy, size)]
        r = query(store, src.nid, dx, dy)
        if r["found"]:
            pass_count += 1
        else:
            fail_count += 1
            print(f"  [RANDOM FAIL] L({sx},{sy}) -> ({dx},{dy}): {r.get('reason')}")
    print(f"[INFO] 随机测试: {pass_count} 通过, {fail_count} 失败")

    store.close()
    print("\n全部测试完成")


if __name__ == "__main__":
    main()
