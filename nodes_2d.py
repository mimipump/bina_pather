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
# 结构体（二维，口号 = x + 2y，x位为最低位）
# =============================================================================
@dataclass(slots=True)
class Node:
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    d0: Optional[ID] # 下级0id（口号0）
    d1: Optional[ID] # 下级1id（口号1）
    d2: Optional[ID] # 下级2id（口号2）
    d3: Optional[ID] # 下级3id（口号3）


@dataclass(slots=True)
class Leaf:
    nid: ID          # 本级id
    up: Optional[ID] # 上级id
    data: ID         # 数据id
    nbr1: Optional[ID] = None   # 非同父邻叶1id（x轴方向）
    nbr2: Optional[ID] = None   # 非同父邻叶2id（y轴方向）


# =============================================================================
# 构造函数
# =============================================================================
def new_node(up: Optional[ID] = NULL,
             d0: Optional[ID] = NULL,
             d1: Optional[ID] = NULL,
             d2: Optional[ID] = NULL,
             d3: Optional[ID] = NULL) -> Node:
    return Node(nid=new_id(), up=up, d0=d0, d1=d1, d2=d2, d3=d3)


def new_leaf(up: Optional[ID] = NULL,
             data: Optional[ID] = NULL,
             nbr1: Optional[ID] = NULL,
             nbr2: Optional[ID] = NULL) -> Leaf:
    return Leaf(nid=new_id(), up=up, data=data, nbr1=nbr1, nbr2=nbr2)


# =============================================================================
# 建立上级 / 建立下级
# slot = (dx<0 ? 1 : 0) + 2 * (dy<0 ? 1 : 0)
# =============================================================================
def build_parent(child: Node, dx: int = 0, dy: int = 0) -> Node:
    """向上建一个父节点，把 child 挂到指定口，返回父节点。"""
    slot = (1 if dx < 0 else 0) + 2 * (1 if dy < 0 else 0)
    parent = Node(nid=new_id(), up=None, d0=None, d1=None, d2=None, d3=None)
    slots = [parent.d0, parent.d1, parent.d2, parent.d3]
    slots[slot] = child.nid
    parent.d0, parent.d1, parent.d2, parent.d3 = slots
    child.up = parent.nid
    return parent


def build_child(parent: Node, dx: int = 0, dy: int = 0) -> Leaf:
    """向下建一个子节点，挂到 parent 的指定口，返回子节点。"""
    slot = (1 if dx < 0 else 0) + 2 * (1 if dy < 0 else 0)
    child = Leaf(nid=new_id(), up=parent.nid, data=None)
    slots = [parent.d0, parent.d1, parent.d2, parent.d3]
    slots[slot] = child.nid
    parent.d0, parent.d1, parent.d2, parent.d3 = slots
    return child
