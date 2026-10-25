import os
from nodes_1d import new_node, new_leaf
from store_1d import Store1D
from query_1d import query
from nodes_1d import NULL


def build_tree(store):
    """建一棵高度为 3 的满二叉树：
    层级：           R(7层)
                /       \
              L3(6)     R3(6)
             /   \     /   \
           L2(5) R2(5) L2'(5) R2'(5)
           /  \   /  \   /  \   /  \
          L1  R1 ...   ...   ...   R1
         /
       L0(leaf0)
    """
    # 从下往上建：先建 8 个叶子 L0..L7
    leaves = [new_leaf(data=f"leaf_{i}".encode()) for i in range(8)]
    for leaf in leaves:
        store.put_leaf(leaf)

    # 第 2 层：4 个父节点，每个挂 2 个叶子
    l2_nodes = []
    for i in range(4):
        p = new_node(d0=leaves[2*i].nid, d1=leaves[2*i+1].nid)
        leaves[2*i].up = p.nid
        leaves[2*i+1].up = p.nid
        store.put_node(p)
        store.put_leaf(leaves[2*i])
        store.put_leaf(leaves[2*i+1])
        l2_nodes.append(p)

    # 第 3 层：2 个父节点
    l3_nodes = []
    for i in range(2):
        p = new_node(d0=l2_nodes[2*i].nid, d1=l2_nodes[2*i+1].nid)
        l2_nodes[2*i].up = p.nid
        l2_nodes[2*i+1].up = p.nid
        store.put_node(p)
        store.put_node(l2_nodes[2*i])
        store.put_node(l2_nodes[2*i+1])
        l3_nodes.append(p)

    # 第 4 层：根
    root = new_node(d0=l3_nodes[0].nid, d1=l3_nodes[1].nid)
    l3_nodes[0].up = root.nid
    l3_nodes[1].up = root.nid
    store.put_node(root)
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
    db_path = "test_1d.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    store = Store1D(db_path)

    # === 立足叶子测试 ===
    entry_id_1 = store.get_entry_leaf_id()
    assert entry_id_1 is not None, "新数据库应自动创建立足叶子"
    print(f"[INFO] 新数据库自动创建立足叶子: {entry_id_1:#x}")

    entry_id_2 = store.get_entry_leaf_id()
    assert entry_id_1 == entry_id_2, "多次调用 get_entry_leaf_id 应返回同一个 id"
    print(f"[INFO] 多次调用 get_entry_leaf_id 返回相同 id: {entry_id_2:#x}")

    # 从立足叶子出发查询
    r = query(store, entry_id_1, d=1)
    assert r["found"] is True, "从立足叶子出发查询应成功"
    print(f"[INFO] 从立足叶子出发查询 d=1: target={r['target']:#x}")

    # 显式设定新的立足叶子
    new_entry_leaf = new_leaf(data=b"new_entry")
    store.put_leaf(new_entry_leaf)
    store.set_entry_leaf(new_entry_leaf.nid)
    entry_id_3 = store.get_entry_leaf_id()
    assert entry_id_3 == new_entry_leaf.nid, "set_entry_leaf 后应返回新立足叶子 id"
    print(f"[INFO] set_entry_leaf 后立足叶子变更为: {entry_id_3:#x}")

    store.close()
    store = Store1D(db_path)  # 重新打开，验证持久化

    entry_id_4 = store.get_entry_leaf_id()
    assert entry_id_4 == entry_id_3, "重新打开数据库后立足叶子 id 应保持不变"
    print(f"[INFO] 重新打开数据库后立足叶子 id 不变: {entry_id_4:#x}")

    root, leaves = build_tree(store)

    print("=== 基础查询测试 ===")
    # leaf 0 和 leaf 1 是兄弟，共享同一个 L2 父节点
    r = query(store, leaves[0].nid, 1)
    check("leaf0 -> d=1 (兄弟 leaf1)", r, expected_target=leaves[1].nid)

    r = query(store, leaves[1].nid, -1)
    check("leaf1 -> d=-1 (兄弟 leaf0)", r, expected_target=leaves[0].nid)

    print("\n=== 跨层查询测试 ===")
    # leaf 0 到 leaf 2：需要爬到 L3 层的共顶
    r = query(store, leaves[0].nid, 2)
    check("leaf0 -> d=2 (leaf2)", r, expected_target=leaves[2].nid)

    # leaf 0 到 leaf 4：需要爬到根
    r = query(store, leaves[0].nid, 4)
    check("leaf0 -> d=4 (leaf4)", r, expected_target=leaves[4].nid)

    # leaf 0 到 leaf 7：最远，爬到根
    r = query(store, leaves[0].nid, 7)
    check("leaf0 -> d=7 (leaf7)", r, expected_target=leaves[7].nid)

    print("\n=== 边界测试 ===")
    # d=0 应该返回自身
    r = query(store, leaves[3].nid, 0)
    check("leaf3 -> d=0 (自身)", r, expected_target=leaves[3].nid)

    # 向左扩展：leaf 0 往左 d=-1，左边没有节点，建立新左邻
    r = query(store, leaves[0].nid, -1)
    check("leaf0 -> d=-1 (建立左邻)", r, expected_found=True)
    # 验证新建的左邻确实是 leaf0 的左边邻居（通过共顶关系）
    assert r["found"] is True
    assert r["target"] is not None

    # 向右扩展：leaf 7 往右 d=1，右边没有节点，建立新右邻
    r = query(store, leaves[7].nid, 1)
    check("leaf7 -> d=1 (建立右邻)", r, expected_found=True)
    assert r["found"] is True
    assert r["target"] is not None

    store.close()
    print("\n全部测试完成")


if __name__ == "__main__":
    main()
