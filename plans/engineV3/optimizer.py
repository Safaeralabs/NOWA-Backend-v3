from typing import List, Dict, Any
import math

def _dist2(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    dx = a["lat"] - b["lat"]
    dy = a["lng"] - b["lng"]
    return dx*dx + dy*dy

def order_stops_nearest_neighbor(stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(stops) <= 2:
        return stops
    remaining = stops[:]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nxt_i = min(range(len(remaining)), key=lambda i: _dist2(last, remaining[i]))
        ordered.append(remaining.pop(nxt_i))
    return ordered
