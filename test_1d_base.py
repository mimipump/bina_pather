import os
import time
from nodes_1d_base import new_node, new_base_leaf
from store_1d import Store1D
from query_1d_base import query


def build_tree(store):
    leaves = [new_base_leaf(data=f"leaf_{i}".encode()) for i in range(8)]
    for leaf in leaves:
        store.put_leaf(leaf)

    l2_nodes = []
    for i in range(4):
        p = new_node(d0=leaves[2*i].nid, d1=leaves[2*i+1].nid)
        store.put_node(p)
        leaves[2*i].up = p.nid
        leaves[2*i+1].up = p.nid
        store.put_leaf(leaves[2*i])
        store.put_leaf(leaves[2*i+1])
        l2_nodes.append(p)

    l3_nodes = []
    for i in range(2):
        p = new_node(d0=l2_nodes[2*i].nid, d1=l2_nodes[2*i+1].nid)
        store.put_node(p)
        l2_nodes[2*i].up = p.nid
        l2_nodes[2*i+1].up = p.nid
        store.put_node(l2_nodes[2*i])
        store.put_node(l2_nodes[2*i+1])
        l3_nodes.append(p)

    root = new_node(d0=l3_nodes[0].nid, d1=l3_nodes[1].nid)
    store.put_node(root)
    l3_nodes[0].up = root.nid
    l3_nodes[1].up = root.nid
    store.put_node(l3_nodes[0])
    store.put_node(l3_nodes[1])

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
    db_path = "test_1d_base.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store1D(db_path)

    entry_id_1 = store.get_entry_leaf_id()
    assert entry_id_1 is not None
    print(f"[INFO] 新数据库自动创建立足叶子: {entry_id_1:#x}")

    r = query(store, entry_id_1, d=1)
    assert r["found"] is True
    print(f"[INFO] 从立足叶子出发查询 d=1: target={r['target']:#x}")

    new_entry_leaf = new_base_leaf(data=b"new_entry")
    store.put_leaf(new_entry_leaf)
    store.set_entry_leaf(new_entry_leaf.nid)
    entry_id_3 = store.get_entry_leaf_id()
    assert entry_id_3 == new_entry_leaf.nid
    print(f"[INFO] set_entry_leaf 后立足叶子变更为: {entry_id_3:#x}")

    store.close()
    store = Store1D(db_path)

    entry_id_4 = store.get_entry_leaf_id()
    assert entry_id_4 == entry_id_3
    print(f"[INFO] 重新打开数据库后立足叶子 id 不变: {entry_id_4:#x}")

    root, leaves = build_tree(store)

    print("=== 基础查询测试 ===")
    r = query(store, leaves[0].nid, 1)
    check("leaf0 -> d=1 (兄弟 leaf1)", r, expected_target=leaves[1].nid)

    r = query(store, leaves[1].nid, -1)
    check("leaf1 -> d=-1 (兄弟 leaf0)", r, expected_target=leaves[0].nid)

    print("\n=== 跨层查询测试 ===")
    r = query(store, leaves[0].nid, 2)
    check("leaf0 -> d=2 (leaf2)", r, expected_target=leaves[2].nid)

    r = query(store, leaves[0].nid, 4)
    check("leaf0 -> d=4 (leaf4)", r, expected_target=leaves[4].nid)

    r = query(store, leaves[0].nid, 7)
    check("leaf0 -> d=7 (leaf7)", r, expected_target=leaves[7].nid)

    print("\n=== 边界测试 ===")
    r = query(store, leaves[3].nid, 0)
    check("leaf3 -> d=0 (自身)", r, expected_target=leaves[3].nid)

    r = query(store, leaves[0].nid, -1)
    check("leaf0 -> d=-1 (建立左邻)", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    r = query(store, leaves[7].nid, 1)
    check("leaf7 -> d=1 (建立右邻)", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    store.close()
    print("\n全部测试完成")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    t1 = time.perf_counter()
    print(f"\n[TIMING] 总耗时: {t1 - t0:.4f}s")
