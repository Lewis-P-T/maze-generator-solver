"""Maze Generator & Solver — stdlib only."""
import argparse
import contextlib
import heapq
import io
import json
import os
import tempfile
import random
from collections import deque

# Directions: name -> (dx, dy)
DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


class Maze:
    def __init__(self, width, height):
        self.width, self.height = width, height
        # each cell holds the set of directions with an open passage
        self.cells = [[set() for _ in range(width)] for _ in range(height)]

    def neighbors(self, x, y):
        for d, (dx, dy) in DIRS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield d, nx, ny

    def carve(self, x, y, d):
        dx, dy = DIRS[d]
        self.cells[y][x].add(d)
        self.cells[y + dy][x + dx].add(OPPOSITE[d])

    def to_json(self):
        return {"width": self.width, "height": self.height,
                "cells": [["".join(sorted(c)) for c in row] for row in self.cells]}

    @classmethod
    def from_json(cls, data):
        """Rebuild a maze, rejecting malformed data or one-sided passages."""
        w, h = data["width"], data["height"]
        cells = data["cells"]
        if not (isinstance(w, int) and isinstance(h, int) and w >= 1 and h >= 1)                 or len(cells) != h or any(len(row) != w for row in cells):
            raise ValueError("maze dimensions don't match cell grid")
        maze = cls(w, h)
        for y, row in enumerate(cells):
            for x, dirs in enumerate(row):
                for d in dirs:
                    nx, ny = x + DIRS[d][0], y + DIRS[d][1]
                    if not (0 <= nx < w and 0 <= ny < h) or OPPOSITE[d] not in cells[ny][nx]:
                        raise ValueError(f"bad passage {d} at ({x}, {y})")
                    maze.cells[y][x].add(d)
        return maze

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_json(), f)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_json(json.load(f))

    def render(self, path=(), marks=None):
        """ASCII maze; cells in `path` get a dot, `marks` maps cell -> single char (wins over path)."""
        on_path, marks = set(path), marks or {}
        lines = ["+" + "---+" * self.width]
        for y in range(self.height):
            row, floor = "|", "+"
            for x in range(self.width):
                if (x, y) in marks:
                    mark = f" {marks[(x, y)]} "
                else:
                    mark = " . " if (x, y) in on_path else "   "
                row += mark + (" " if "E" in self.cells[y][x] else "|")
                floor += ("   " if "S" in self.cells[y][x] else "---") + "+"
            lines += [row, floor]
        return "\n".join(lines)


def generate_backtracker(width, height, rng=random):
    """Recursive backtracker, iterative so big mazes don't hit recursion limits."""
    maze = Maze(width, height)
    visited = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        x, y = stack[-1]
        options = [(d, nx, ny) for d, nx, ny in maze.neighbors(x, y) if (nx, ny) not in visited]
        if not options:
            stack.pop()
            continue
        d, nx, ny = rng.choice(options)
        maze.carve(x, y, d)
        visited.add((nx, ny))
        stack.append((nx, ny))
    return maze


def generate_prim(width, height, rng=random):
    """Randomized Prim's: grow from a frontier of walls next to the carved region."""
    maze = Maze(width, height)
    inside = {(0, 0)}
    frontier = [(0, 0, d) for d, _, _ in maze.neighbors(0, 0)]
    while frontier:
        # swap-pop a random wall: O(1) removal
        i = rng.randrange(len(frontier))
        frontier[i], frontier[-1] = frontier[-1], frontier[i]
        x, y, d = frontier.pop()
        nx, ny = x + DIRS[d][0], y + DIRS[d][1]
        if (nx, ny) in inside:
            continue
        maze.carve(x, y, d)
        inside.add((nx, ny))
        frontier += [(nx, ny, d2) for d2, ax, ay in maze.neighbors(nx, ny) if (ax, ay) not in inside]
    return maze


def generate_kruskal(width, height, rng=random):
    """Randomized Kruskal's: shuffle all walls, knock down any joining two separate sets (union-find)."""
    maze = Maze(width, height)
    parent = list(range(width * height))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]  # path halving
            i = parent[i]
        return i

    walls = [(x, y, d) for y in range(height) for x in range(width) for d in "ES"
             if x + DIRS[d][0] < width and y + DIRS[d][1] < height]
    rng.shuffle(walls)
    for x, y, d in walls:
        a, b = find(y * width + x), find((y + DIRS[d][1]) * width + x + DIRS[d][0])
        if a != b:
            parent[a] = b
            maze.carve(x, y, d)
    return maze


GENERATORS = {"backtracker": generate_backtracker, "prim": generate_prim, "kruskal": generate_kruskal}


def _walk_back(prev, cur):
    path = []
    while cur:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def _open_neighbors(maze, cell):
    x, y = cell
    for d in maze.cells[y][x]:
        yield (x + DIRS[d][0], y + DIRS[d][1])


def solve_bfs(maze, start=(0, 0), goal=None):
    """Shortest path. Returns (path, cells_visited); path is None if unreachable."""
    goal = goal or (maze.width - 1, maze.height - 1)
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            return _walk_back(prev, cur), len(prev)
        for n in _open_neighbors(maze, cur):
            if n not in prev:
                prev[n] = cur
                queue.append(n)
    return None, len(prev)


def solve_dfs(maze, start=(0, 0), goal=None):
    """Depth-first: finds *a* path (the only one in a perfect maze), not guaranteed shortest otherwise."""
    goal = goal or (maze.width - 1, maze.height - 1)
    prev = {start: None}
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur == goal:
            return _walk_back(prev, cur), len(prev)
        for n in _open_neighbors(maze, cur):
            if n not in prev:
                prev[n] = cur
                stack.append(n)
    return None, len(prev)


def solve_astar(maze, start=(0, 0), goal=None):
    """A* with Manhattan-distance heuristic (admissible on a grid) -> shortest path."""
    goal = goal or (maze.width - 1, maze.height - 1)
    h = lambda c: abs(c[0] - goal[0]) + abs(c[1] - goal[1])
    prev, cost = {start: None}, {start: 0}
    heap = [(h(start), 0, start)]
    while heap:
        _, g, cur = heapq.heappop(heap)
        if cur == goal:
            return _walk_back(prev, cur), len(prev)
        if g > cost[cur]:
            continue  # stale heap entry
        for n in _open_neighbors(maze, cur):
            if g + 1 < cost.get(n, float("inf")):
                cost[n], prev[n] = g + 1, cur
                heapq.heappush(heap, (g + 1 + h(n), g + 1, n))
    return None, len(prev)


SOLVERS = {"bfs": solve_bfs, "dfs": solve_dfs, "astar": solve_astar}


# ---------- play mode ----------

KEYS = {"w": "N", "s": "S", "d": "E", "a": "W"}
SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maze_scores.json")


def apply_moves(maze, pos, keys):
    """Walk from pos following WASD keys; walls block (no move). Returns (pos, moves made, bumps)."""
    moves = bumps = 0
    for k in keys.lower():
        d = KEYS.get(k)
        if d is None:
            continue
        x, y = pos
        if d in maze.cells[y][x]:
            pos = (x + DIRS[d][0], y + DIRS[d][1])
            moves += 1
        else:
            bumps += 1
    return pos, moves, bumps


def load_scores(path=SCORES_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def record_score(key, moves, optimal, path=SCORES_FILE):
    """Keep the fewest-moves result per maze key. Returns True if it's a new best."""
    scores = load_scores(path)
    old = scores.get(key)
    if old is not None and old["moves"] <= moves:
        return False
    scores[key] = {"moves": moves, "optimal": optimal}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=1, sort_keys=True)
    return True


def play(maze, key, input_fn=input, scores_path=SCORES_FILE):
    """Interactive walk from top-left to bottom-right. Returns moves taken, or None if quit."""
    goal = (maze.width - 1, maze.height - 1)
    optimal = len(solve_bfs(maze)[0]) - 1
    pos, moves, trail = (0, 0), 0, [(0, 0)]
    print(f"Reach G with WASD (several keys per line ok, e.g. 'ddsd'). q quits. Optimal: {optimal} moves.")
    while pos != goal:
        print(maze.render(trail, {goal: "G", pos: "@"}))
        try:
            line = input_fn(f"moves {moves}> ").strip()
        except EOFError:
            line = "q"
        if line.lower().startswith("q"):
            print("gave up.")
            return None
        for k in line:  # step key by key so the trail records every cell
            pos, m, b = apply_moves(maze, pos, k)
            moves += m
            if m:
                trail.append(pos)
            if b:
                print("bump! wall that way.")
            if pos == goal:
                break
    print(maze.render(trail, {goal: "@"}))
    extra = moves - optimal
    print(f"Solved in {moves} moves (optimal {optimal}" + (", perfect!)" if extra == 0 else f", +{extra})"))
    if record_score(key, moves, optimal, scores_path):
        print("New best score for this maze!")
    return moves


# ---------- menu mode ----------

def _ask(input_fn, prompt, default, cast=str, choices=None):
    raw = input_fn(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        val = cast(raw)
    except ValueError:
        val = None
    if val is None or (choices and val not in choices) or (cast is int and val < 1):
        print("invalid, using default")
        return default
    return val


def menu(input_fn=input, scores_path=SCORES_FILE):
    """Text menu tying everything together. input_fn is injectable for the self-check."""
    state = {"gen": "backtracker", "w": 15, "h": 8, "seed": random.randrange(10 ** 6)}
    maze = GENERATORS[state["gen"]](state["w"], state["h"], random.Random(state["seed"]))

    def key():
        return f"{state['gen']}-{state['w']}x{state['h']}-{state['seed']}"

    while True:
        print(f"\n== Maze menu == current: {key()}")
        print("1) new maze  2) show  3) solve  4) compare solvers  5) play  6) save  7) load  8) best scores  q) quit")
        try:
            choice = input_fn("> ").strip().lower()
        except EOFError:
            choice = "q"
        if choice == "1":
            state["gen"] = _ask(input_fn, "generator " + "/".join(GENERATORS), state["gen"], choices=GENERATORS)
            state["w"] = _ask(input_fn, "width", state["w"], int)
            state["h"] = _ask(input_fn, "height", state["h"], int)
            state["seed"] = _ask(input_fn, "seed", random.randrange(10 ** 6), int)
            maze = GENERATORS[state["gen"]](state["w"], state["h"], random.Random(state["seed"]))
            print(maze.render())
        elif choice == "2":
            print(maze.render())
        elif choice == "3":
            name = _ask(input_fn, "solver " + "/".join(SOLVERS), "bfs", choices=SOLVERS)
            path, visited = SOLVERS[name](maze)
            print(maze.render(path))
            print(f"{name.upper()}: path {len(path)} cells, visited {visited}")
        elif choice == "4":
            print(f"{'solver':<8}{'path':>6}{'visited':>9}")
            for name, solve in SOLVERS.items():
                path, visited = solve(maze)
                print(f"{name:<8}{len(path):>6}{visited:>9}")
        elif choice == "5":
            play(maze, key(), input_fn, scores_path)
        elif choice == "6":
            fname = _ask(input_fn, "save to", "maze.json")
            try:
                maze.save(fname)
                print(f"saved to {fname}")
            except OSError as e:
                print(f"save failed: {e}")
        elif choice == "7":
            fname = _ask(input_fn, "load from", "maze.json")
            try:
                maze = Maze.load(fname)
            except (OSError, ValueError, KeyError, TypeError) as e:
                print(f"load failed: {e}")
                continue
            # loaded mazes are keyed by file name so their scores stay separate
            state.update(gen="file", w=maze.width, h=maze.height, seed=os.path.basename(fname))
            print(maze.render())
        elif choice == "8":
            scores = load_scores(scores_path)
            if not scores:
                print("no scores yet - play a maze!")
            for k, v in sorted(scores.items()):
                print(f"{k:<32}{v['moves']:>5} moves (optimal {v['optimal']})")
        elif choice.startswith("q"):
            print("bye!")
            return
        else:
            print("unknown option")


def self_check():
    rng = random.Random(42)
    for gname, gen in GENERATORS.items():
        for w, h in [(1, 1), (5, 3), (12, 8)]:
            m = gen(w, h, rng)
            # perfect maze: spanning tree => exactly w*h-1 passages
            passages = sum(len(c) for row in m.cells for c in row) // 2
            assert passages == w * h - 1, (gname, w, h, passages)
            # all cells reachable
            seen, todo = {(0, 0)}, [(0, 0)]
            while todo:
                for n in _open_neighbors(m, todo.pop()):
                    if n not in seen:
                        seen.add(n)
                        todo.append(n)
            assert len(seen) == w * h, gname
            assert len(m.render().splitlines()) == 2 * h + 1
            paths = {}
            for sname, solve in SOLVERS.items():
                path, visited = solve(m)
                assert path[0] == (0, 0) and path[-1] == (w - 1, h - 1), (gname, sname)
                assert len(path) <= visited <= w * h
                # consecutive path cells must be joined by an open passage
                for a, b in zip(path, path[1:]):
                    assert b in _open_neighbors(m, a), (gname, sname)
                assert m.render(path).count(" . ") == len(path)
                paths[sname] = path
            # perfect maze has a unique path, so every solver agrees
            assert paths["bfs"] == paths["dfs"] == paths["astar"], gname
        # same seed => same maze
        assert gen(9, 6, random.Random(7)).cells == gen(9, 6, random.Random(7)).cells
    # 2x2 open room (has a loop): BFS and A* are shortest (3 cells)
    m = Maze(2, 2)
    m.carve(0, 0, "E"); m.carve(0, 0, "S"); m.carve(1, 0, "S"); m.carve(0, 1, "E")
    assert len(solve_bfs(m)[0]) == len(solve_astar(m)[0]) == 3
    # JSON round-trip (file + in-memory) and rejection of a one-sided passage
    m = generate_kruskal(7, 4, rng)
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        m.save(tmp)
        assert Maze.load(tmp).cells == m.cells
    finally:
        os.remove(tmp)
    try:
        Maze.from_json({"width": 2, "height": 1, "cells": [["E", ""]]})
        raise AssertionError("one-sided passage accepted")
    except ValueError:
        pass
    # walled-off goal => no path
    assert solve_astar(Maze(2, 1))[0] is None and solve_dfs(Maze(2, 1))[0] is None
    # play mode: walls block, a scripted solve records a best score, menu drives everything
    m = generate_backtracker(6, 4, random.Random(3))
    assert apply_moves(Maze(2, 1), (0, 0), "dx")[1:] == (0, 1)
    path = solve_bfs(m)[0]
    route = "".join(next(k for k, d in KEYS.items() if (a[0] + DIRS[d][0], a[1] + DIRS[d][1]) == b)
                    for a, b in zip(path, path[1:]))
    assert apply_moves(m, (0, 0), route) == ((5, 3), len(path) - 1, 0)
    assert m.render(marks={(0, 0): "@"}).count(" @ ") == 1
    bump = next(k for k, d in KEYS.items() if d not in m.cells[0][0])
    fd, scores = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(scores)
    try:
        feed = iter([bump, route[:2], route[2:]])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert play(m, "k", lambda _: next(feed), scores) == len(path) - 1
        assert "perfect" in out.getvalue() and "bump" in out.getvalue()
        assert load_scores(scores)["k"]["moves"] == len(path) - 1
        assert not record_score("k", len(path) + 5, len(path) - 1, scores)  # worse => old kept
        assert record_score("j", 9, 7, scores) and set(load_scores(scores)) == {"j", "k"}
        feed = iter(["1", "kruskal", "5", "3", "11", "2", "3", "astar", "4", "5", "q", "8", "zz", "q"])
        with contextlib.redirect_stdout(io.StringIO()) as out:
            menu(lambda _: next(feed), scores)
        text = out.getvalue()
        assert "kruskal-5x3-11" in text and "ASTAR" in text and "gave up" in text and "bye!" in text
        assert "unknown option" in text and "optimal 7" in text
    finally:
        if os.path.exists(scores):
            os.remove(scores)
    print("self-check passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate and solve a random maze.")
    ap.add_argument("-W", "--width", type=int, default=15, help="columns (default 15)")
    ap.add_argument("-H", "--height", type=int, default=8, help="rows (default 8)")
    ap.add_argument("-s", "--seed", type=int, help="random seed for a reproducible maze")
    ap.add_argument("-g", "--generator", choices=GENERATORS, default="backtracker", help="generation algorithm")
    ap.add_argument("-a", "--solver", choices=SOLVERS, default="bfs", help="solver whose path is drawn")
    ap.add_argument("--no-solve", action="store_true", help="print the maze without the solution")
    ap.add_argument("--compare", action="store_true", help="print a stats table for every solver")
    ap.add_argument("--save", metavar="FILE", help="save the generated maze to a JSON file")
    ap.add_argument("--load", metavar="FILE", help="load a maze from a JSON file instead of generating one")
    ap.add_argument("--play", action="store_true", help="walk the maze yourself with WASD")
    ap.add_argument("--menu", action="store_true", help="interactive menu (generate/solve/play/save/load)")
    ap.add_argument("--check", action="store_true", help="run the self-check and exit")
    args = ap.parse_args(argv)
    if args.check:
        return self_check()
    if args.menu:
        return menu()
    if args.width < 1 or args.height < 1:
        ap.error("width and height must be at least 1")
    if args.load:
        try:
            maze = Maze.load(args.load)
        except (OSError, ValueError, KeyError, TypeError) as e:
            ap.error(f"can't load {args.load}: {e}")
        args.generator = "loaded"
        key = f"file-{maze.width}x{maze.height}-{os.path.basename(args.load)}"
    else:
        if args.seed is None:
            args.seed = random.randrange(10 ** 6)  # pick one so play scores get a reproducible key
        maze = GENERATORS[args.generator](args.width, args.height, random.Random(args.seed))
        key = f"{args.generator}-{args.width}x{args.height}-{args.seed}"
    if args.save:
        maze.save(args.save)
        print(f"saved to {args.save}")
    if args.play:
        print(f"maze: {key}")
        return play(maze, key)
    print(maze.render())
    if not args.no_solve:
        path, visited = SOLVERS[args.solver](maze)
        print(f"\n{args.solver.upper()} ({args.generator}): path {len(path)} cells, visited {visited}\n")
        print(maze.render(path))
    if args.compare:
        print(f"\n{'solver':<8}{'path':>6}{'visited':>9}")
        for name, solve in SOLVERS.items():
            path, visited = solve(maze)
            print(f"{name:<8}{len(path):>6}{visited:>9}")


if __name__ == "__main__":
    main()
