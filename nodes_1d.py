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
class Leaf:
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    data: ID         # 数据id
    nbr1: Optional[ID] = None   # 非同父邻叶id（左邻/右邻，由0叶/1叶决定）


# =============================================================================
# 构造函数
# =============================================================================
def new_node(up: Optional[ID] = NULL,
             d0: Optional[ID] = NULL,
             d1: Optional[ID] = NULL) -> Node:
    return Node(nid=new_id(), up=up, d0=d0, d1=d1)


def new_leaf(up: Optional[ID] = NULL,
             data: Optional[ID] = NULL,
             nbr1: Optional[ID] = NULL) -> Leaf:
    return Leaf(nid=new_id(), up=up, data=data, nbr1=nbr1)


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
    """向下建一个子节点，挂到 parent 的指定口，返回子节点。"""
    slot = 1 if d < 0 else 0
    child = Leaf(nid=new_id(), up=parent.nid, data=None)
    if slot == 0:
        parent.d0 = child.nid
    else:
        parent.d1 = child.nid
    return child
