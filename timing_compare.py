import os
import time
import random

from nodes_1d import new_node, new_leaf
from store_1d import Store1D
from query_1d import query as q1d, batch_query as batch_q1d

from nodes_2d import new_node as new_node_2d, new_leaf as new_leaf_2d
from store_2d import Store2D
from query_2d import query as q2d, batch_query as batch_q2d

from nodes_3d import new_node as new_node_3d, new_leaf as new_leaf_3d
from store_3d import Store3D
from query_3d import query as q3d, batch_query as batch_q3d


# ============================ 1D ============================
def build_tree_1d(store):
    leaves = [new_leaf(data=f"leaf_{i}".encode()) for i in range(8)]
    for leaf in leaves:
        store.put_leaf(leaf)
    l2_nodes = []
    for i in range(4):
        p = new_node(d0=leaves[2 * i].nid, d1=leaves[2 * i + 1].nid)
        store.put_node(p)
        leaves[2 * i].up = p.nid
        leaves[2 * i + 1].up = p.nid
        store.put_leaf(leaves[2 * i])
        store.put_leaf(leaves[2 * i + 1])
        l2_nodes.append(p)
    l3_nodes = []
    for i in range(2):
        p = new_node(d0=l2_nodes[2 * i].nid, d1=l2_nodes[2 * i + 1].nid)
        store.put_node(p)
        l2_nodes[2 * i].up = p.nid
        l2_nodes[2 * i + 1].up = p.nid
        store.put_node(l2_nodes[2 * i])
        store.put_node(l2_nodes[2 * i + 1])
        l3_nodes.append(p)
    root = new_node(d0=l3_nodes[0].nid, d1=l3_nodes[1].nid)
    store.put_node(root)
    l3_nodes[0].up = root.nid
    l3_nodes[1].up = root.nid
    store.put_node(l3_nodes[0])
    store.put_node(l3_nodes[1])
    return root, leaves


def run_1d():
    db_path = "timing_1d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store1D(db_path)
    root, leaves = build_tree_1d(store)

    random.seed(12345)
    queries = []
    for _ in range(5000):
        src = random.choice(leaves)
        d = random.randint(-8, 8)
        queries.append((src.nid, d))

    # 第一轮
    t0 = time.perf_counter()
    for nid, d in queries:
        q1d(store, nid, d)
    t1 = time.perf_counter()

    # 第二轮（完全相同的查询）
    t2 = time.perf_counter()
    for nid, d in queries:
        q1d(store, nid, d)
    t3 = time.perf_counter()

    print(f"[1D] 第一轮耗时: {t1 - t0:.4f}s, 第二轮耗时: {t3 - t2:.4f}s, "
          f"提升: {(t1 - t0) - (t3 - t2):.4f}s")

    # batch_query 测试
    t4 = time.perf_counter()
    batch_results = batch_q1d(store, queries)
    t5 = time.perf_counter()
    print(f"[1D] batch_query 耗时: {t5 - t4:.4f}s, 结果数: {len(batch_results)}")
    store.close()


# ============================ 2D ============================
def leaf_idx_2d(x, y, size=16):
    return y * size + x


def build_tree_2d(store, size=16, height=4):
    assert size & (size - 1) == 0
    assert 2 ** height >= size
    total = size * size
    leaves = [new_leaf_2d(data=f"leaf_{i}".encode()) for i in range(total)]
    for leaf in leaves:
        store.put_leaf(leaf)
    bpd = size // 2
    level1 = []
    for by in range(bpd):
        for bx in range(bpd):
            p = new_node_2d()
            for ly in range(2):
                for lx in range(2):
                    gx = bx * 2 + lx
                    gy = by * 2 + ly
                    li = leaf_idx_2d(gx, gy, size)
                    leaf = leaves[li]
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
            for ly in range(2):
                for lx in range(2):
                    gx = bx * 2 + lx
                    gy = by * 2 + ly
                    li = leaf_idx_2d(gx, gy, size)
                    leaves[li].up = p.nid
                    store.put_leaf(leaves[li])
            level1.append(p)
    prev = level1
    prev_bpd = bpd
    for level in range(2, height):
        bl = prev_bpd // 2
        curr = []
        for by2 in range(bl):
            for bx2 in range(bl):
                p = new_node_2d()
                children = []
                for lby in range(2):
                    for lbx in range(2):
                        gbx = bx2 * 2 + lbx
                        gby = by2 * 2 + lby
                        p_idx = gby * prev_bpd + gbx
                        child = prev[p_idx]
                        children.append(child)
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
                for child in children:
                    child.up = p.nid
                    store.put_node(child)
                curr.append(p)
        prev = curr
        prev_bpd = bl
    root = new_node_2d()
    store.put_node(root)
    for i, child in enumerate(prev):
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


def run_2d():
    db_path = "timing_2d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store2D(db_path)
    root, leaves = build_tree_2d(store)

    size = 16
    random.seed(12345)
    queries = []
    for _ in range(5000):
        sx = random.randint(0, size - 1)
        sy = random.randint(0, size - 1)
        dx = random.randint(-15, 15)
        dy = random.randint(-15, 15)
        src = leaves[leaf_idx_2d(sx, sy, size)]
        queries.append((src.nid, dx, dy))

    t0 = time.perf_counter()
    for nid, dx, dy in queries:
        q2d(store, nid, dx, dy)
    t1 = time.perf_counter()

    t2 = time.perf_counter()
    for nid, dx, dy in queries:
        q2d(store, nid, dx, dy)
    t3 = time.perf_counter()

    print(f"[2D] 第一轮耗时: {t1 - t0:.4f}s, 第二轮耗时: {t3 - t2:.4f}s, "
          f"提升: {(t1 - t0) - (t3 - t2):.4f}s")

    # batch_query 测试
    t4 = time.perf_counter()
    batch_results = batch_q2d(store, queries)
    t5 = time.perf_counter()
    print(f"[2D] batch_query 耗时: {t5 - t4:.4f}s, 结果数: {len(batch_results)}")
    store.close()


# ============================ 3D ============================
def leaf_idx_3d(x, y, z, size=16):
    return z * size * size + y * size + x


def build_tree_3d(store, size=16, height=4):
    assert size & (size - 1) == 0
    assert 2 ** height >= size
    total = size * size * size
    leaves = [new_leaf_3d(data=f"leaf_{i}".encode()) for i in range(total)]
    for leaf in leaves:
        store.put_leaf(leaf)
    bpd = size // 2
    level1 = []
    for bx in range(bpd):
        for by in range(bpd):
            for bz in range(bpd):
                p = new_node_3d()
                leaf_slots = []
                for lx in range(2):
                    for ly in range(2):
                        for lz in range(2):
                            gx = bx * 2 + lx
                            gy = by * 2 + ly
                            gz = bz * 2 + lz
                            li = leaf_idx_3d(gx, gy, gz, size)
                            leaf = leaves[li]
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
                            leaf_slots.append((leaf, slot))
                store.put_node(p)
                for leaf, slot in leaf_slots:
                    leaf.up = p.nid
                    store.put_leaf(leaf)
                level1.append(p)
    prev = level1
    prev_bpd = bpd
    for level in range(2, height):
        bl = prev_bpd // 2
        curr = []
        for bx2 in range(bl):
            for by2 in range(bl):
                for bz2 in range(bl):
                    p = new_node_3d()
                    children = []
                    for lbx in range(2):
                        for lby in range(2):
                            for lbz in range(2):
                                gbx = bx2 * 2 + lbx
                                gby = by2 * 2 + lby
                                gbz = bz2 * 2 + lbz
                                bp2 = prev_bpd * prev_bpd
                                p_idx = gbx * bp2 + gby * prev_bpd + gbz
                                child = prev[p_idx]
                                children.append(child)
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
                    for child in children:
                        child.up = p.nid
                        store.put_node(child)
                    curr.append(p)
        prev = curr
        prev_bpd = bl
    root = new_node_3d()
    store.put_node(root)
    for i, child in enumerate(prev):
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


def run_3d():
    db_path = "timing_3d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store3D(db_path)
    root, leaves = build_tree_3d(store)

    size = 16
    random.seed(12345)
    queries = []
    for _ in range(5000):
        sx = random.randint(0, size - 1)
        sy = random.randint(0, size - 1)
        sz = random.randint(0, size - 1)
        dx = random.randint(-15, 15)
        dy = random.randint(-15, 15)
        dz = random.randint(-15, 15)
        src = leaves[leaf_idx_3d(sx, sy, sz, size)]
        queries.append((src.nid, dx, dy, dz))

    t0 = time.perf_counter()
    for nid, dx, dy, dz in queries:
        q3d(store, nid, dx, dy, dz)
    t1 = time.perf_counter()

    t2 = time.perf_counter()
    for nid, dx, dy, dz in queries:
        q3d(store, nid, dx, dy, dz)
    t3 = time.perf_counter()

    print(f"[3D] 第一轮耗时: {t1 - t0:.4f}s, 第二轮耗时: {t3 - t2:.4f}s, "
          f"提升: {(t1 - t0) - (t3 - t2):.4f}s")

    # batch_query 测试
    t4 = time.perf_counter()
    batch_results = batch_q3d(store, queries)
    t5 = time.perf_counter()
    print(f"[3D] batch_query 耗时: {t5 - t4:.4f}s, 结果数: {len(batch_results)}")
    store.close()


if __name__ == "__main__":
    run_1d()
    run_2d()
    run_3d()
