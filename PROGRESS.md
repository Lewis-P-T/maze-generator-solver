# Maze Generator & Solver — Progress

Python 3, standard library only. Run: `python maze.py [-W 15 -H 8 -s SEED]` (self-check: `python maze.py --check`).

- [x] 1. Skeleton: grid model, recursive-backtracker generator (iterative DFS), ASCII renderer, self-check
- [x] 2. BFS solver with shortest-path overlay drawn on the ASCII maze
- [x] 3. CLI options via argparse: width, height, seed (reproducible mazes)
- [ ] 4. More generators: randomized Prim's and Kruskal's (union-find)
- [ ] 5. More solvers: DFS and A* (heapq, Manhattan heuristic) with a stats comparison (visited cells, path length)
- [ ] 6. Save/load mazes to JSON files
- [ ] 7. Interactive menu mode + play mode (walk the maze with WASD, move counter vs optimal)
- [ ] 8. Polish: README, persistent best-scores file for play mode, full self-check covering every generator/solver
