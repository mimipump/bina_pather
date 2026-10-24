from dataclasses import dataclass
from typing import Optional

ID = int
NULL = None


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
