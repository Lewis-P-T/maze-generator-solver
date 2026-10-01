"""Maze Generator & Solver — stdlib only."""
import argparse
import heapq
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

    def render(self, path=()):
        """ASCII maze; cells in `path` are marked with a dot."""
        on_path = set(path)
        lines = ["+" + "---+" * self.width]
        for y in range(self.height):
            row, floor = "|", "+"
            for x in range(self.width):
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
    # walled-off goal => no path
    assert solve_astar(Maze(2, 1))[0] is None and solve_dfs(Maze(2, 1))[0] is None
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
    ap.add_argument("--check", action="store_true", help="run the self-check and exit")
    args = ap.parse_args(argv)
    if args.check:
        return self_check()
    if args.width < 1 or args.height < 1:
        ap.error("width and height must be at least 1")
    maze = GENERATORS[args.generator](args.width, args.height, random.Random(args.seed))
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
