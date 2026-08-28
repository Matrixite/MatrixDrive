#!/usr/bin/env python3
"""Create a preliminary six-signal-layer route for MatrixDrive Rev B.

This grid router is intentionally deterministic and auditable.  Six signal
layers alternate preferred directions and through vias change layers.  In1.Cu
and In6.Cu remain continuous GND and 3V3 planes respectively.

The result is suitable for inspection and DRC iteration in KiCad.  It does not
turn the logical placeholder package maps into fabrication-approved pinouts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path
import json
import math

from generate_kicad_project import (
    HW, PROJECT, Component, Pin, assign_pcb_positions, build_components,
    net_table, safe_name,
)


STEP = 0.25
X_MIN, X_MAX = 0.75, 99.25
Y_MIN, Y_MAX = 0.75, 64.25
NX = int(round((X_MAX - X_MIN) / STEP)) + 1
NY = int(round((Y_MAX - Y_MIN) / STEP)) + 1
F_CU, IN2_CU, IN3_CU, IN4_CU, IN5_CU, B_CU = range(6)
ROUTE_LAYERS = (F_CU, IN2_CU, IN3_CU, IN4_CU, IN5_CU, B_CU)
PRIMARY_LAYERS = (F_CU, IN2_CU, IN3_CU, IN4_CU, B_CU)
LAYER_NAME = {F_CU: "F.Cu", IN2_CU: "In2.Cu", IN3_CU: "In3.Cu",
              IN4_CU: "In4.Cu", IN5_CU: "In5.Cu", B_CU: "B.Cu"}
SIGNAL_WIDTH = 0.15
POWER_WIDTH = 0.25
VIA_SIZE = 0.40
VIA_DRILL = 0.20
PLANE_NETS = {"GND", "3V3"}
POWER_NETS = {"CART_5V_IN", "CART_5V", "USB_VBUS", "SYS_5V", "1V1",
              "VREG_SW", "VREG_AVDD", "ADC_AVDD"}
CONSTRAINED_ORDER = (
    "PAUSE_GATE",
    "ROM_A12", "ROM_A13", "VD3",
    "MEM_D4", "ROM_A8", "STAGE_MISO",
    "MEM_D3", "MEM_D11", "ROM_A18", "ROM_A2", "LED_RED", "CART_A15",
    "STAGE_MOSI",
    "TIME_N", "MRES_N", "MEM_D2", "USB_DM", "VD7", "STAGE_CS_N",
    "CART_A11", "USB_DP", "ROM_A9", "VA5", "VD1", "CART_A19",
    "CAS2_3V3",
)
CONSTRAINED_RANK = {net: rank for rank, net in enumerate(CONSTRAINED_ORDER)}


@dataclass(frozen=True)
class Terminal:
    ref: str
    pin: str
    net: str
    x: float
    y: float
    sx: float
    sy: float
    layers: tuple[int, ...]
    ax: float
    ay: float


def rotate(x: float, y: float, angle: float) -> tuple[float, float]:
    if not angle:
        return x, y
    rad = math.radians(angle)
    return x * math.cos(rad) - y * math.sin(rad), x * math.sin(rad) + y * math.cos(rad)


def local_pad_geometry(c: Component) -> list[tuple[Pin, float, float, float, float, tuple[int, ...]]]:
    pins = c.pins
    result = []
    if c.ref == "J1":
        lookup = {p.number: p for p in pins}
        for i in range(32):
            x = 10.63 + i * 2.54
            result.append((lookup[f"B{i+1}"], x, 61.5, 1.8, 7.0, (F_CU,)))
            result.append((lookup[f"A{i+1}"], x, 61.5, 1.8, 7.0, (B_CU,)))
        return result
    if len(pins) == 1:
        return [(pins[0], 0, 0, 1.2, 1.2, (F_CU,))]
    if len(pins) == 2:
        return [(pins[0], -1, 0, 1.0, 1.1, (F_CU,)),
                (pins[1], 1, 0, 1.0, 1.1, (F_CU,))]
    if c.ref in ("J3", "J4"):
        for i, p in enumerate(pins):
            result.append((p, (i % 2) * 1.27 - 0.635,
                           (i // 2) * 1.27 - 2.54, 1.0, 1.0, (F_CU, B_CU)))
        return result
    if c.ref == "J2":
        for i, p in enumerate(pins):
            row = 0 if i < 8 else 1
            col = i if i < 8 else i - 8
            result.append((p, (col - 3.5) * 0.5,
                           -1.5 if row == 0 else 1.5, 0.28, 1.0, (F_CU,)))
        return result
    half = (len(pins) + 1) // 2
    pitch = max(0.5, min(0.75, 10.0 / max(half, 1)))
    for i, p in enumerate(pins):
        if i < half:
            px = -2.35
            py = (i - (half - 1) / 2) * pitch
        else:
            right = len(pins) - half
            j = i - half
            px = 2.35
            py = (j - (right - 1) / 2) * pitch
        result.append((p, px, py, 0.65, 0.32, (F_CU,)))
    return result


def terminals_for(cs: list[Component], positions) -> list[Terminal]:
    terminals = []
    for c in cs:
        ox, oy, angle = positions[c.ref]
        for pad_index, (pin, px, py, sx, sy, layers) in enumerate(local_pad_geometry(c)):
            if pin.net is None:
                continue
            rx, ry = rotate(px, py, angle)
            if c.ref == "J1":
                # The A/B edge fingers share x coordinates on opposite board
                # faces but often carry different nets.  Stagger their fanout
                # anchors so a through-via from one side cannot occupy the
                # other side's escape point.
                lateral = 0.50 if pin.number.startswith("A") else -0.50
                edx, edy = rotate(lateral, -4.25, angle)
            elif len(c.pins) == 1:
                edx, edy = 0.0, 0.0
            elif c.ref == "J2":
                # Route both USB-C rows into the board and stagger adjacent
                # pins so their fanout vias do not form a 0.5 mm-pitch line.
                escape = 0.75 + 0.50 * (pad_index % 2)
                edx, edy = rotate(0, escape, angle)
            else:
                # Fine-pitch logical perimeter pads need a checkerboard via
                # fanout.  Alternating the escape length prevents adjacent
                # 0.5 mm-pitch pads from demanding through-vias in one column.
                escape = 0.75
                if len(c.pins) > 2 and c.ref not in ("J3", "J4"):
                    escape += 0.50 * (pad_index % 2)
                edx, edy = rotate(math.copysign(escape, px), 0, angle)
            terminals.append(Terminal(c.ref, pin.number, pin.net,
                                      ox + rx, oy + ry, sx, sy, layers,
                                      ox + rx + edx, oy + ry + edy))
    return terminals


def to_grid(x: float, y: float) -> tuple[int, int]:
    ix = max(0, min(NX - 1, int(round((x - X_MIN) / STEP))))
    iy = max(0, min(NY - 1, int(round((y - Y_MIN) / STEP))))
    return ix, iy


def from_grid(ix: int, iy: int) -> tuple[float, float]:
    return X_MIN + ix * STEP, Y_MIN + iy * STEP


class Router:
    def __init__(self, terminals: list[Terminal], nets: dict[str, int]):
        self.terminals = terminals
        self.nets = nets
        self.pad_occupancy = [defaultdict(set) for _ in ROUTE_LAYERS]
        self.track_occupancy = [{} for _ in ROUTE_LAYERS]
        self.via_occupancy = {}
        self.segments: list[tuple[str, int, float, float, float, float, float]] = []
        self.vias: list[tuple[str, float, float, bool]] = []
        self.connections = 0
        self.expansions = 0
        self._mark_pads()
        self._reserve_terminal_escapes()

    def _mark_pads(self) -> None:
        margin = 0.10
        for t in self.terminals:
            for layer in t.layers:
                x0, y0 = to_grid(t.x - t.sx / 2 - margin, t.y - t.sy / 2 - margin)
                x1, y1 = to_grid(t.x + t.sx / 2 + margin, t.y + t.sy / 2 + margin)
                for ix in range(min(x0, x1), max(x0, x1) + 1):
                    for iy in range(min(y0, y1), max(y0, y1) + 1):
                        self.pad_occupancy[layer][(ix, iy)].add(t.net)

    def _reserve_terminal_escapes(self) -> None:
        """Reserve and draw short fanout traces before global routing.

        Without this pass, an early bus trace can cross the only corridor out
        of a later fine-pitch logical pad.  The reserved escape is part of the
        finished route and makes every terminal independently reachable.
        """
        for t in self.terminals:
            if t.net in PLANE_NETS:
                continue
            ix0, iy0 = to_grid(t.x, t.y)
            ix1, iy1 = to_grid(t.ax, t.ay)
            cells = []
            ix, iy = ix0, iy0
            cells.append((ix, iy))
            while ix != ix1:
                ix += 1 if ix1 > ix else -1
                cells.append((ix, iy))
            while iy != iy1:
                iy += 1 if iy1 > iy else -1
                cells.append((ix, iy))
            for layer in t.layers:
                for cell in cells:
                    existing = self.track_occupancy[layer].get(cell)
                    if existing is None or existing == t.net:
                        self.track_occupancy[layer][cell] = t.net
                gx0, gy0 = from_grid(ix0, iy0)
                gx1, gy1 = from_grid(ix1, iy1)
                width = POWER_WIDTH if t.net in POWER_NETS else SIGNAL_WIDTH
                if (t.x, t.y) != (gx0, gy0):
                    self.segments.append((t.net, layer, t.x, t.y, gx0, gy0, width))
                if (gx0, gy0) != (gx1, gy1):
                    self.segments.append((t.net, layer, gx0, gy0, gx1, gy1, width))
            if len(t.layers) == 1:
                # Pre-fanout every SMD signal terminal before global routing.
                # This guarantees access to the reserved rescue layer and
                # prevents later nets from consuming the only legal via site.
                gx1, gy1 = from_grid(ix1, iy1)
                self.vias.append((t.net, gx1, gy1, False))
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        cell=(ix1+dx,iy1+dy)
                        existing=self.via_occupancy.get(cell)
                        if existing is None or existing == t.net:
                            self.via_occupancy[cell]=t.net

    def blocked(self, state: tuple[int, int, int], net: str,
                exempt: set[tuple[int, int, int]]) -> bool:
        ix, iy, layer = state
        if not (0 <= ix < NX and 0 <= iy < NY):
            return True
        if state in exempt:
            return False
        pad_nets = self.pad_occupancy[layer].get((ix, iy), ())
        if any(other != net for other in pad_nets):
            return True
        track_net = self.track_occupancy[layer].get((ix, iy))
        if track_net is not None and track_net != net:
            return True
        via_net = self.via_occupancy.get((ix, iy))
        return via_net is not None and via_net != net

    def astar(self, starts: set[tuple[int, int, int]],
              goals: set[tuple[int, int, int]], net: str,
              allowed_layers: tuple[int, ...] = ROUTE_LAYERS):
        starts = {state for state in starts if state[2] in allowed_layers}
        goals = {state for state in goals if state[2] in allowed_layers}
        if not starts or not goals:
            return None
        if starts & goals:
            return [next(iter(starts & goals))]
        goal_xy = {(x, y) for x, y, _ in goals}
        min_gx = min(x for x, _ in goal_xy); max_gx = max(x for x, _ in goal_xy)
        min_gy = min(y for _, y in goal_xy); max_gy = max(y for _, y in goal_xy)

        def heuristic(ix, iy):
            dx = 0 if min_gx <= ix <= max_gx else min(abs(ix-min_gx), abs(ix-max_gx))
            dy = 0 if min_gy <= iy <= max_gy else min(abs(iy-min_gy), abs(iy-max_gy))
            return dx + dy

        exempt = starts | goals
        open_heap = []
        best = {}
        parent = {}
        serial = 0
        for s in starts:
            best[s] = 0.0
            heappush(open_heap, (heuristic(s[0], s[1]), 0.0, serial, s))
            serial += 1
        local_expansions = 0
        # The complete six-layer routing grid contains roughly 604k states.
        # Allow a difficult connection to explore all of them before declaring
        # a net unroutable; the lower cap used by the first prototype produced
        # false failures late in dense bus routes.
        while open_heap and local_expansions < 650000:
            _, cost, _, state = heappop(open_heap)
            if cost != best.get(state):
                continue
            if state in goals:
                path = [state]
                while state in parent:
                    state = parent[state]
                    path.append(state)
                path.reverse()
                self.expansions += local_expansions
                return path
            local_expansions += 1
            ix, iy, layer = state
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt = (ix+dx, iy+dy, layer)
                if self.blocked(nxt, net, exempt):
                    continue
                horizontal = layer in (F_CU, IN3_CU, IN5_CU)
                preferred = (horizontal and dy == 0) or (not horizontal and dx == 0)
                step_cost = 1.0 if preferred else 1.35
                new = cost + step_cost
                if new < best.get(nxt, 1e30):
                    best[nxt] = new; parent[nxt] = state
                    heappush(open_heap, (new + heuristic(nxt[0], nxt[1]), new, serial, nxt))
                    serial += 1
            for other_layer in allowed_layers:
                if other_layer == layer:
                    continue
                other = (ix, iy, other_layer)
                if not self.blocked(other, net, exempt):
                    new = cost + 8.0 + abs(other_layer-layer)
                    if new < best.get(other, 1e30):
                        best[other] = new; parent[other] = state
                        heappush(open_heap, (new + heuristic(ix, iy), new, serial, other))
                        serial += 1
        self.expansions += local_expansions
        return None

    def mark_path(self, net: str, path) -> None:
        for ix, iy, layer in path:
            self.track_occupancy[layer][(ix, iy)] = net
        for a, b in zip(path, path[1:]):
            if a[2] != b[2]:
                ix, iy, _ = a
                self.vias.append((net, *from_grid(ix, iy), False))
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        cell=(ix+dx,iy+dy)
                        existing=self.via_occupancy.get(cell)
                        if existing is None or existing == net:
                            self.via_occupancy[cell]=net

        # Convert each same-layer run into a small number of KiCad segments.
        i = 0
        width = POWER_WIDTH if net in POWER_NETS else SIGNAL_WIDTH
        while i < len(path)-1:
            if path[i][2] != path[i+1][2]:
                i += 1
                continue
            start = i
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]
            layer = path[i][2]
            i += 1
            while (i < len(path)-1 and path[i][2] == layer and
                   path[i+1][2] == layer and
                   path[i+1][0]-path[i][0] == dx and
                   path[i+1][1]-path[i][1] == dy):
                i += 1
            x0,y0=from_grid(path[start][0],path[start][1])
            x1,y1=from_grid(path[i][0],path[i][1])
            if (x0,y0)!=(x1,y1):
                self.segments.append((net,layer,x0,y0,x1,y1,width))

    def add_plane_vias(self, grouped: dict[str, list[Terminal]]) -> None:
        for net in sorted(PLANE_NETS):
            seen=set()
            for t in grouped[net]:
                key=(round(t.x,3),round(t.y,3))
                if key in seen: continue
                seen.add(key)
                self.vias.append((net,t.x,t.y,True))

    def route(self):
        grouped=defaultdict(list)
        for t in self.terminals:
            grouped[t.net].append(t)
        route_names=[n for n,ts in grouped.items() if n not in PLANE_NETS and len(ts)>1]

        def span(name):
            xs=[t.x for t in grouped[name]]; ys=[t.y for t in grouped[name]]
            return (max(xs)-min(xs))+(max(ys)-min(ys))
        def route_priority(name):
            if name in POWER_NETS:
                return (0, 0, -len(grouped[name]), -span(name), name)
            if name in CONSTRAINED_RANK:
                return (1, CONSTRAINED_RANK[name], -len(grouped[name]), -span(name), name)
            return (2, 0, -len(grouped[name]), -span(name), name)
        route_names.sort(key=route_priority)
        routed=set(); failed_work={}

        def terminal_states(t):
            ix,iy=to_grid(t.ax,t.ay)
            layers=ROUTE_LAYERS if len(t.layers) == 1 else t.layers
            return {(ix,iy,layer) for layer in layers}

        def connect_remaining(net, tree, remaining, allowed_layers):
            remaining=list(remaining)
            while remaining:
                def distance(t):
                    tx,ty=to_grid(t.ax,t.ay)
                    return min(abs(tx-x)+abs(ty-y) for x,y,_ in tree)
                candidates=sorted(remaining,key=distance)
                chosen=None; path=None
                for t in candidates:
                    starts=terminal_states(t)
                    path=self.astar(starts,tree,net,allowed_layers)
                    if path is not None:
                        chosen=t; break
                if path is None:
                    return remaining
                self.mark_path(net,path)
                tree.update(path)
                remaining.remove(chosen)
                self.connections += 1
            return []

        for net in route_names:
            terms=grouped[net]
            first=terms[0]
            tree=terminal_states(first)
            remaining=connect_remaining(net,tree,terms[1:],PRIMARY_LAYERS)
            if remaining:
                failed_work[net]=(tree,remaining)
            else:
                routed.add(net)

        # In5.Cu is intentionally untouched by the primary pass.  Retry only
        # incomplete nets with access to that reserved rescue layer.
        failed={}
        for net,(tree,remaining) in failed_work.items():
            remaining=connect_remaining(net,tree,remaining,ROUTE_LAYERS)
            if remaining:
                failed[net]=[f"{t.ref}.{t.pin}" for t in remaining]
            else:
                routed.add(net)
        self.add_plane_vias(grouped)
        return grouped,routed,failed


def pcb_route_text(router: Router, nets: dict[str,int]) -> str:
    out=[]
    for net,layer,x0,y0,x1,y1,width in router.segments:
        out.append(f'  (segment (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) '
                   f'(width {width:.3f}) (layer "{LAYER_NAME[layer]}") (net {nets[net]}))\n')
    seen=set()
    for net,x,y,plane in router.vias:
        key=(net,round(x,3),round(y,3))
        if key in seen: continue
        seen.add(key)
        out.append(f'  (via (at {x:.3f} {y:.3f}) (size {VIA_SIZE:.3f}) '
                   f'(drill {VIA_DRILL:.3f}) (layers "F.Cu" "B.Cu") (net {nets[net]}))\n')
    return "".join(out)


def main() -> None:
    cs=build_components()
    positions=assign_pcb_positions(cs)
    terminals=terminals_for(cs,positions)
    nets=net_table(cs)
    router=Router(terminals,nets)
    grouped,routed,failed=router.route()

    path=HW/f"{PROJECT}.kicad_pcb"
    pcb=path.read_text()
    marker='  (gr_text "DO NOT FABRICATE - UNROUTED / PROGRAMMABLE PIN MAPS UNVERIFIED"'
    pcb=pcb.replace(marker,
        '  (gr_text "DO NOT FABRICATE - PRELIMINARY ROUTE / PIN MAPS UNVERIFIED"')
    closing=pcb.rfind(')\n')
    if closing < 0:
        raise RuntimeError("invalid PCB closing expression")
    pcb=pcb[:closing]+pcb_route_text(router,nets)+pcb[closing:]
    path.write_text(pcb)

    report={
        "status":"complete" if not failed else "partial",
        "router":"MatrixDrive deterministic grid router",
        "signal_layers":["F.Cu","In2.Cu","In3.Cu","In4.Cu","In5.Cu","B.Cu"],
        "plane_layers":{"In1.Cu":"GND","In6.Cu":"3V3"},
        "grid_mm":STEP,
        "signal_track_width_mm":SIGNAL_WIDTH,
        "power_track_width_mm":POWER_WIDTH,
        "via_size_mm":VIA_SIZE,
        "via_drill_mm":VIA_DRILL,
        "routable_net_count":len([n for n,ts in grouped.items() if n not in PLANE_NETS and len(ts)>1]),
        "routed_net_count":len(routed),
        "failed_nets":failed,
        "connection_count":router.connections,
        "segment_count":len(router.segments),
        "via_count":len({(n,round(x,3),round(y,3)) for n,x,y,_ in router.vias}),
        "astar_expansions":router.expansions,
        "warning":"Physical package pin mappings remain unverified; run KiCad DRC and manual review.",
    }
    (HW/"routing-report.json").write_text(json.dumps(report,indent=2)+"\n")
    manifest_path=HW/"kicad-project-manifest.json"
    manifest=json.loads(manifest_path.read_text())
    manifest["status"]="logical-complete; preliminary routed PCB awaiting KiCad DRC"
    manifest["routing_report"]="routing-report.json"
    manifest["release_gates"]=[
        gate.replace(
            "Route all signal and power nets, refill zones, and pass KiCad ERC/DRC",
            "Review/refine the preliminary route, refill zones, and pass KiCad ERC/DRC",
        )
        for gate in manifest["release_gates"]
    ]
    if "routing-report.json" not in manifest["generated_files"]:
        manifest["generated_files"].append("routing-report.json")
    manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
