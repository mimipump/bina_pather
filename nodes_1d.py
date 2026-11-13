import secrets
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# 基础类型
# =============================================================================
ID = int
NULL = None


def new_id() -> ID:
    return secrets.randbits(128)


# =============================================================================
# 结构体（一维）
# =============================================================================
@dataclass(slots=True)
class Node:
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    d0: Optional[ID] # 下级0id（左口，编号0）
    d1: Optional[ID] # 下级1id（右口，编号1）


@dataclass(slots=True)
class BaseLeaf:
    """基础叶子：无邻居字段，用于不启用 nbr 的树。"""
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    data: ID         # 数据id


@dataclass(slots=True)
class Leaf:
    """带邻居字段的叶子：nbr1 为非同父邻叶id（左邻/右邻，由0叶/1叶决定）。"""
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    data: ID         # 数据id
    nbr1: Optional[ID] = None   # 非同父邻叶id


# =============================================================================
# 构造函数
# =============================================================================
def new_node(up: Optional[ID] = NULL,
             d0: Optional[ID] = NULL,
             d1: Optional[ID] = NULL,
             nid: Optional[ID] = NULL) -> Node:
    return Node(nid=nid, up=up, d0=d0, d1=d1)


def new_base_leaf(up: Optional[ID] = NULL,
                  data: Optional[ID] = NULL,
                  nid: Optional[ID] = NULL) -> BaseLeaf:
    return BaseLeaf(nid=nid, up=up, data=data)


def new_leaf(up: Optional[ID] = NULL,
             data: Optional[ID] = NULL,
             nbr1: Optional[ID] = NULL,
             nid: Optional[ID] = NULL) -> Leaf:
    return Leaf(nid=nid, up=up, data=data, nbr1=nbr1)


# =============================================================================
# 建立上级 / 建立下级
# slot 由 d 决定：d<0 时新节点在右口(1)，d>=0 时新节点在左口(0)
# =============================================================================
def build_parent(child: Node, d: int = 0) -> Node:
    """向上建一个父节点，把 child 挂到指定口，返回父节点。"""
    slot = 1 if d < 0 else 0
    parent = Node(nid=new_id(), up=None, d0=None, d1=None)
    if slot == 0:
        parent.d0 = child.nid
    else:
        parent.d1 = child.nid
    child.up = parent.nid
    return parent


def build_child(parent: Node, d: int = 0) -> Leaf:
    """向下建一个子节点，挂到 parent 的指定口，返回子节点。
    不绑定 nbr（nbr 需在 build_tree 按空间位置正确绑定）。
    """
    slot = 1 if d < 0 else 0
    child = Leaf(nid=new_id(), up=parent.nid, data=None)
    if slot == 0:
        parent.d0 = child.nid
    else:
        parent.d1 = child.nid
    return child


def bind_nbr_1d(store, leaf_a: Leaf, leaf_b: Leaf) -> None:
    """显式绑定两个叶子的 nbr1（非同父邻叶）。

    仅当两叶直接父节点不同（非同父）时才绑定；同父兄弟不绑定。
    """
    if leaf_a.nid == leaf_b.nid:
        return
    if leaf_a.up is not None and leaf_b.up is not None and leaf_a.up == leaf_b.up:
        return  # 同父，不绑定
    leaf_a.nbr1 = leaf_b.nid
    leaf_b.nbr1 = leaf_a.nid
    store.put_leaf(leaf_a)
    store.put_leaf(leaf_b)
