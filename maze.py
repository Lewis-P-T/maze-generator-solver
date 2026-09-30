"""Maze Generator & Solver — stdlib only."""
import random
import sys

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

    def render(self):
        lines = ["+" + "---+" * self.width]
        for y in range(self.height):
            row, floor = "|", "+"
            for x in range(self.width):
                row += "   " + (" " if "E" in self.cells[y][x] else "|")
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
    print("self-check passed")


if __name__ == "__main__":
    if "--check" in sys.argv:
        self_check()
    else:
        print(generate_backtracker(15, 8).render())
