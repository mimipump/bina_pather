import os
import random
from nodes_3d import new_node, new_leaf
from store_3d import Store3D
from query_3d import query
from nodes_3d import NULL


def leaf_idx(x, y, z, size=16):
    """按 row-major 计算叶子索引：z最慢，x最快"""
    return z * size * size + y * size + x


def build_tree(store, size=16, height=4):
    """建一棵高度为 height 的满八叉树。
    叶子 size×size×size，坐标范围 [0, size-1]^3。
    size 必须是 2 的幂，height 必须满足 2^height >= size。
    所有层级循环顺序统一为 bx(外)→by(中)→bz(内)，
    子节点按 slot = lx + 2*ly + 4*lz 严格挂载，与 query 下行一致。
    """
    assert size & (size - 1) == 0, "size 必须是 2 的幂"
    assert 2 ** height >= size, "height 不足以覆盖整个网格"

    total_leaves = size * size * size
    leaves = [new_leaf(data=f"leaf_{i}".encode()) for i in range(total_leaves)]
    for leaf in leaves:
        store.put_leaf(leaf)

    blocks_per_dim = size // 2

    # ---------- 层1：(size/2)^3 个父节点，每个挂 8 个叶子（2×2×2块）----------
    level1 = []
    for bx in range(blocks_per_dim):
        for by in range(blocks_per_dim):
            for bz in range(blocks_per_dim):
                p = new_node()
                for lx in range(2):
                    for ly in range(2):
                        for lz in range(2):
                            gx = bx * 2 + lx
                            gy = by * 2 + ly
                            gz = bz * 2 + lz
                            li = leaf_idx(gx, gy, gz, size)
                            leaf = leaves[li]
                            leaf.up = p.nid
                            store.put_leaf(leaf)
                            slot = lx + 2 * ly + 4 * lz
                            if slot == 0:
                                p.d0 = leaf.nid
                            elif slot == 1:
                                p.d1 = leaf.nid
                            elif slot == 2:
                                p.d2 = leaf.nid
                            elif slot == 3:
                                p.d3 = leaf.nid
                            elif slot == 4:
                                p.d4 = leaf.nid
                            elif slot == 5:
                                p.d5 = leaf.nid
                            elif slot == 6:
                                p.d6 = leaf.nid
                            else:
                                p.d7 = leaf.nid
                store.put_node(p)
                level1.append(p)

    # ---------- 层2~height-1：递归构建 -----------
    prev_level = level1
    prev_blocks_per_dim = blocks_per_dim
    for level in range(2, height):
        blocks_l = prev_blocks_per_dim // 2
        curr_level = []
        for bx2 in range(blocks_l):
            for by2 in range(blocks_l):
                for bz2 in range(blocks_l):
                    p = new_node()
                    for lbx in range(2):
                        for lby in range(2):
                            for lbz in range(2):
                                gbx = bx2 * 2 + lbx
                                gby = by2 * 2 + lby
                                gbz = bz2 * 2 + lbz
                                # prev_level 排列：bx*(BPD^2) + by*BPD + bz
                                bp2 = prev_blocks_per_dim * prev_blocks_per_dim
                                p_idx = gbx * bp2 + gby * prev_blocks_per_dim + gbz
                                child = prev_level[p_idx]
                                child.up = p.nid
                                store.put_node(child)
                                slot = lbx + 2 * lby + 4 * lbz
                                if slot == 0:
                                    p.d0 = child.nid
                                elif slot == 1:
                                    p.d1 = child.nid
                                elif slot == 2:
                                    p.d2 = child.nid
                                elif slot == 3:
                                    p.d3 = child.nid
                                elif slot == 4:
                                    p.d4 = child.nid
                                elif slot == 5:
                                    p.d5 = child.nid
                                elif slot == 6:
                                    p.d6 = child.nid
                                else:
                                    p.d7 = child.nid
                    store.put_node(p)
                    curr_level.append(p)
        prev_level = curr_level
        prev_blocks_per_dim = blocks_l

    # ---------- 根：挂 8 个顶层节点 -----------
    root = new_node()
    for i, child in enumerate(prev_level):
        child.up = root.nid
        store.put_node(child)
        rbx = i // 4
        rby = (i % 4) // 2
        rbz = i % 2
        slot = rbx + 2 * rby + 4 * rbz
        if slot == 0:
            root.d0 = child.nid
        elif slot == 1:
            root.d1 = child.nid
        elif slot == 2:
            root.d2 = child.nid
        elif slot == 3:
            root.d3 = child.nid
        elif slot == 4:
            root.d4 = child.nid
        elif slot == 5:
            root.d5 = child.nid
        elif slot == 6:
            root.d6 = child.nid
        else:
            root.d7 = child.nid
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
    db_path = "test_3d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store3D(db_path)

    # === 立足叶子测试 ===
    entry_id_1 = store.get_entry_leaf_id()
    assert entry_id_1 is not None
    print(f"[INFO] 立足叶子: {entry_id_1:#x}")

    r = query(store, entry_id_1, 1, 0, 0)
    assert r["found"] is True
    print(f"[INFO] 立足叶子查询 (1,0,0): target={r['target']:#x}")

    store.close()
    store = Store3D(db_path)
    entry_id_2 = store.get_entry_leaf_id()
    assert entry_id_2 == entry_id_1
    print(f"[INFO] 持久化验证通过: {entry_id_2:#x}")

    root, leaves = build_tree(store, size=size, height=height)
    store.commit()
    print(f"[INFO] 树构建完成并持久化: {size}×{size}×{size}={size**3} 个叶子")

    print(f"\n=== 基础查询（单步，兄弟节点）===")
    tests = [
        ((0, 0, 0), (1, 0, 0)),
        ((1, 0, 0), (-1, 0, 0)),
        ((0, 0, 0), (0, 1, 0)),
        ((0, 1, 0), (0, -1, 0)),
        ((0, 0, 0), (0, 0, 1)),
        ((0, 0, 1), (0, 0, -1)),
    ]
    for (sx, sy, sz), (dx, dy, dz) in tests:
        src = leaves[leaf_idx(sx, sy, sz, size)]
        dst = leaves[leaf_idx(sx + dx, sy + dy, sz + dz, size)]
        r = query(store, src.nid, dx, dy, dz)
        check(f"L({sx},{sy},{sz}) -> ({dx},{dy},{dz})", r, expected_target=dst.nid)

    print(f"\n=== 跨层查询（共顶为根，size={size}）===")
    tests = [
        ((0, 0, 0), (15, 0, 0)),
        ((0, 0, 0), (0, 15, 0)),
        ((0, 0, 0), (0, 0, 15)),
        ((0, 0, 0), (15, 15, 15)),
        ((15, 15, 15), (-15, -15, -15)),
        ((0, 0, 0), (7, 9, 3)),
        ((15, 15, 15), (-7, -9, -3)),
        ((8, 8, 8), (7, 7, 7)),
        ((7, 7, 7), (-7, -7, -7)),
        ((0, 15, 0), (15, -15, 0)),
        ((15, 0, 15), (-15, 0, -15)),
    ]
    for (sx, sy, sz), (dx, dy, dz) in tests:
        src = leaves[leaf_idx(sx, sy, sz, size)]
        tx, ty, tz = sx + dx, sy + dy, sz + dz
        if 0 <= tx < size and 0 <= ty < size and 0 <= tz < size:
            dst = leaves[leaf_idx(tx, ty, tz, size)]
            r = query(store, src.nid, dx, dy, dz)
            check(f"L({sx},{sy},{sz}) -> ({dx},{dy},{dz})", r, expected_target=dst.nid)
        else:
            r = query(store, src.nid, dx, dy, dz)
            check(f"L({sx},{sy},{sz}) -> ({dx},{dy},{dz}) 越界扩展", r, expected_found=True)

    print(f"\n=== 边界：自身查询 ===")
    for (x, y, z) in [(0, 0, 0), (7, 7, 7), (15, 15, 15), (8, 9, 3), (3, 12, 5)]:
        src = leaves[leaf_idx(x, y, z, size)]
        r = query(store, src.nid, 0, 0, 0)
        check(f"L({x},{y},{z}) -> (0,0,0) 自身", r, expected_target=src.nid)

    print(f"\n=== 边界：向外扩展（建立新节点）===")
    expand_tests = [
        ((0, 0, 0), (-1, 0, 0)),
        ((15, 0, 0), (1, 0, 0)),
        ((0, 0, 0), (0, -1, 0)),
        ((0, 15, 0), (0, 1, 0)),
        ((0, 0, 0), (0, 0, -1)),
        ((0, 0, 15), (0, 0, 1)),
        ((0, 0, 0), (-1, -1, -1)),
        ((15, 15, 15), (1, 1, 1)),
        ((0, 15, 0), (-1, 1, -1)),
        ((15, 0, 15), (1, -1, 1)),
        ((7, 7, 7), (-8, -8, -8)),
        ((8, 8, 8), (8, 8, 8)),
    ]
    for (sx, sy, sz), (dx, dy, dz) in expand_tests:
        src = leaves[leaf_idx(sx, sy, sz, size)]
        r = query(store, src.nid, dx, dy, dz)
        check(f"L({sx},{sy},{sz}) -> ({dx},{dy},{dz}) 扩展", r, expected_found=True)

    print(f"\n=== 随机查询测试（5000 次）===")
    random.seed(42)
    pass_count = 0
    fail_count = 0
    for _ in range(5000):
        sx = random.randint(0, size - 1)
        sy = random.randint(0, size - 1)
        sz = random.randint(0, size - 1)
        dx = random.randint(-15, 15)
        dy = random.randint(-15, 15)
        dz = random.randint(-15, 15)
        src = leaves[leaf_idx(sx, sy, sz, size)]
        r = query(store, src.nid, dx, dy, dz)
        if r["found"]:
            pass_count += 1
        else:
            fail_count += 1
            print(f"  [RANDOM FAIL] L({sx},{sy},{sz}) -> ({dx},{dy},{dz}): {r.get('reason')}")
    print(f"[INFO] 随机测试: {pass_count} 通过, {fail_count} 失败")

    store.close()
    print("\n全部测试完成")


if __name__ == "__main__":
    main()
