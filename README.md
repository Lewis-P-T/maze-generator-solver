# Maze Generator & Solver

A terminal maze toolkit in pure Python 3 (standard library only, no installs).
Generate random "perfect" mazes three different ways, solve them with three
search algorithms, compare their stats, save/load mazes as JSON, and play them
yourself with WASD while chasing a best score.

## Run

```
git clone https://github.com/Lewis-P-T/maze-generator-solver
cd maze-generator-solver
python maze.py            # random 15x8 maze + its BFS solution
python maze.py --menu     # interactive menu: generate / solve / compare / play / save / load / scores
python maze.py --play     # walk a maze yourself
python maze.py --check    # self-check (every generator x every solver, play, menu, JSON, scores)
```

### Options

| Flag | Meaning |
|------|---------|
| `-W N`, `-H N` | width / height in cells (default 15 x 8) |
| `-s SEED` | reproducible maze |
| `-g backtracker\|prim\|kruskal` | generation algorithm |
| `-a bfs\|dfs\|astar` | solver whose path is drawn |
| `--compare` | table of path length and cells visited for every solver |
| `--no-solve` | print only the maze |
| `--save FILE` / `--load FILE` | write / read a maze as JSON |
| `--play` | play mode |
| `--menu` | menu mode |

## Algorithms

**Generators** (all produce perfect mazes: a spanning tree, exactly one path between any two cells)

- **Recursive backtracker** - iterative DFS with an explicit stack; long winding corridors.
- **Randomized Prim's** - grows from a frontier of walls, O(1) random removal; lots of short dead ends.
- **Randomized Kruskal's** - shuffles every wall and knocks it down if it joins two separate
  regions, tracked with a union-find (path halving).

**Solvers**

- **BFS** - shortest path, explores outward evenly.
- **DFS** - finds a path with a stack; not shortest in general (it is in a perfect maze).
- **A\*** - priority queue (`heapq`) with a Manhattan-distance heuristic; shortest path while
  usually visiting far fewer cells than BFS.

```
$ python maze.py -W 6 -H 3 -s 1 --compare
solver    path  visited
bfs         14       18
dfs         14       18
astar       14       15
```

## Play mode

You are `@`, the goal is `G` (bottom-right). Type one or more of `w a s d` per line
(e.g. `ddsd`) and press Enter; `q` quits. Walls block you ("bump!"), your trail is
drawn with dots, and when you finish you see your move count against the optimal
BFS route. The fewest-moves result per maze (keyed by generator, size and seed, or
the file name for loaded mazes) is kept in `maze_scores.json` next to the script -
view them with option 8 in the menu.

## Save format

```json
{"width": 2, "height": 2, "cells": [["E", "SW"], ["E", "NW"]]}
```

Each cell lists its open sides. Loading validates dimensions and rejects one-sided passages.
