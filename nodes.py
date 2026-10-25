import secrets
from dataclasses import dataclass
from typing import Optional

ID = int
NULL = None


def new_id() -> ID:
    return secrets.randbits(128)


@dataclass(slots=True)
class Node1D:
    nid: ID
    up: Optional[ID]
    d0: Optional[ID]
    d1: Optional[ID]


@dataclass(slots=True)
class Leaf1D:
    nid: ID
    up: Optional[ID]
    data: ID
    nbr1: Optional[ID] = None


@dataclass(slots=True)
class Node:
    nid: ID
    up: Optional[ID]
    d0: Optional[ID]
    d1: Optional[ID]
    d2: Optional[ID]
    d3: Optional[ID]


@dataclass(slots=True)
class Leaf:
    nid: ID
    up: Optional[ID]
    data: ID
    nbr1: Optional[ID] = None
    nbr2: Optional[ID] = None


@dataclass(slots=True)
class Node3D:
    nid: ID
    up: Optional[ID]
    d0: Optional[ID]
    d1: Optional[ID]
    d2: Optional[ID]
    d3: Optional[ID]
    d4: Optional[ID]
    d5: Optional[ID]
    d6: Optional[ID]
    d7: Optional[ID]


@dataclass(slots=True)
class Leaf3D:
    nid: ID
    up: Optional[ID]
    data: ID
    nbr1: Optional[ID] = None
    nbr2: Optional[ID] = None
    nbr3: Optional[ID] = None


def new_node1D(up: Optional[ID] = NULL,
               d0: Optional[ID] = NULL,
               d1: Optional[ID] = NULL) -> Node1D:
    return Node1D(nid=new_id(), up=up, d0=d0, d1=d1)


def new_leaf1D(up: Optional[ID] = NULL,
               data: Optional[ID] = NULL,
               nbr1: Optional[ID] = NULL) -> Leaf1D:
    return Leaf1D(nid=new_id(), up=up, data=data, nbr1=nbr1)


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


def new_node3D(up: Optional[ID] = NULL,
               d0: Optional[ID] = NULL,
               d1: Optional[ID] = NULL,
               d2: Optional[ID] = NULL,
               d3: Optional[ID] = NULL,
               d4: Optional[ID] = NULL,
               d5: Optional[ID] = NULL,
               d6: Optional[ID] = NULL,
               d7: Optional[ID] = NULL) -> Node3D:
    return Node3D(nid=new_id(), up=up, d0=d0, d1=d1, d2=d2, d3=d3,
                  d4=d4, d5=d5, d6=d6, d7=d7)


def new_leaf3D(up: Optional[ID] = NULL,
               data: Optional[ID] = NULL,
               nbr1: Optional[ID] = NULL,
               nbr2: Optional[ID] = NULL,
               nbr3: Optional[ID] = NULL) -> Leaf3D:
    return Leaf3D(nid=new_id(), up=up, data=data,
                  nbr1=nbr1, nbr2=nbr2, nbr3=nbr3)
