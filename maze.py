"""Maze Generator & Solver — stdlib only."""
import argparse
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


def solve_bfs(maze, start=(0, 0), goal=None):
    """Shortest path from start to goal (default bottom-right) as a list of cells."""
    goal = goal or (maze.width - 1, maze.height - 1)
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            path = []
            while cur:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        x, y = cur
        for d in maze.cells[y][x]:
            n = (x + DIRS[d][0], y + DIRS[d][1])
            if n not in prev:
                prev[n] = cur
                queue.append(n)
    return None


def self_check():
    rng = random.Random(42)
    for w, h in [(1, 1), (5, 3), (12, 8)]:
        m = generate_backtracker(w, h, rng)
        # perfect maze: spanning tree => exactly w*h-1 passages
        passages = sum(len(c) for row in m.cells for c in row) // 2
        assert passages == w * h - 1, (w, h, passages)
        # all cells reachable
        seen, todo = {(0, 0)}, [(0, 0)]
        while todo:
            x, y = todo.pop()
            for d in m.cells[y][x]:
                n = (x + DIRS[d][0], y + DIRS[d][1])
                if n not in seen:
                    seen.add(n)
                    todo.append(n)
        assert len(seen) == w * h
        assert len(m.render().splitlines()) == 2 * h + 1
        path = solve_bfs(m)
        assert path[0] == (0, 0) and path[-1] == (w - 1, h - 1)
        # consecutive path cells must be joined by an open passage
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            assert any((ax + DIRS[d][0], ay + DIRS[d][1]) == (bx, by) for d in m.cells[ay][ax])
        assert m.render(path).count(" . ") == len(path)
    # hand-built 3x1 corridor: path is the whole row
    m = Maze(3, 1)
    m.carve(0, 0, "E")
    m.carve(1, 0, "E")
    assert solve_bfs(m) == [(0, 0), (1, 0), (2, 0)]
    # same seed => same maze
    assert generate_backtracker(9, 6, random.Random(7)).cells == generate_backtracker(9, 6, random.Random(7)).cells
    print("self-check passed")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate and solve a random maze.")
    ap.add_argument("-W", "--width", type=int, default=15, help="columns (default 15)")
    ap.add_argument("-H", "--height", type=int, default=8, help="rows (default 8)")
    ap.add_argument("-s", "--seed", type=int, help="random seed for a reproducible maze")
    ap.add_argument("--no-solve", action="store_true", help="print the maze without the solution")
    ap.add_argument("--check", action="store_true", help="run the self-check and exit")
    args = ap.parse_args(argv)
    if args.check:
        return self_check()
    if args.width < 1 or args.height < 1:
        ap.error("width and height must be at least 1")
    maze = generate_backtracker(args.width, args.height, random.Random(args.seed))
    print(maze.render())
    if not args.no_solve:
        path = solve_bfs(maze)
        print(f"\nShortest path (BFS): {len(path)} cells\n")
        print(maze.render(path))


if __name__ == "__main__":
    main()
