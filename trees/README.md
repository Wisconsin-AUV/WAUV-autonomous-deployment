## DEV INFO
Author: Conner O'Reilly
Wisc email: ccoreilly@wisc.edu
Last modified date: 09/01/2026
Other contact info(optional): oreillyconner@protonmail.com

## Trees
Each file here builds one behavior tree out of the leaf nodes in `behaviors/`. A
file exposes a `create_*` function that resets the blackboard keys the tree needs
and returns a root node ready to tick with `tick_once()`. `main.py` calls these
builders.

The trees are assembled from three py_trees composites:

- `Sequence` runs its children in order and stops at the first `FAILURE`. With
  `memory=True` it resumes at the child that was still running instead of starting
  over.
- `Selector` tries its children in order and stops at the first `SUCCESS`. With
  `memory=False` it re-checks from the first child every tick.
- `Repeat` re-ticks its child forever and stops once the child returns `FAILURE`.

## Structure
One file per tree, named `<purpose>Tree.py`. Subtrees that only belong to one tree
live as `create_*_subtree` functions in that same file. Anything shared across
trees (such as the task queue reset values) comes from `blackboard.py`, not from
here.

## TODO
- `create_return_subtree` has no perception guard yet. It should check whether the
  starting area is visible and search for it, the same way the gate and pole
  subtrees do.

## competitionTree.py
`create_auv_tree(task_queue)` builds the coarse loop used for a full competition
run, where `task_queue` is a list of task name strings.

The root is a `Repeat` over a `Sequence` ("Get To Work") of `GetTask` then a
`Selector` ("Fallback"). `GetTask` pulls the next task; when the queue is empty it
fails and the `Repeat` ends. The selector runs `TaskDone` first to skip a task
that is already complete, otherwise it runs a `Sequence` of `MoveToTask` then
`PerformTask`. `PerformTask` carries out the whole task in one node, so this tree
never goes deeper.

## prequalTree.py
`create_detailed_prequal_queue_tree()` builds the same loop as the competition
tree with two changes: it also resets `gate_found` and `pole_found`, and the
perform node is `PerformPrequalTask` instead of `PerformTask`.

The builder creates the gate, pole, and return subtrees below and passes them to
`PerformPrequalTask` as `{"gate": ..., "pole": ..., "return": ...}`. On each tick
`PerformPrequalTask` reads `current_task` and ticks the matching subtree.

### create_gate_subtree / create_pole_subtree
Both have the same shape; the pole version only swaps the names and the flag it
uses. The subtree is a `Sequence`:

    Sequence "Gate Subtree"
    ├─ Selector "Find Gate"
    │  ├─ CheckBlackboardFlag("gate_found")   already seen, skip the search
    │  └─ Sequence "Search Then Detect Gate"
    │     ├─ SubAction        slow scan for the gate
    │     └─ DetectObject     sets gate_found
    ├─ SubAction              align with the gate
    ├─ SubAction              drive through the gate
    └─ MarkTaskComplete("gate")

The `Selector` means the search only runs while `gate_found` is still false. The
final `MarkTaskComplete` is what lets `TaskDone` skip the task if the tree comes
back to it later.

### create_return_subtree
A plain `Sequence` with no perception step (see TODO): turn toward start, drive
back to start, surface, then `MarkTaskComplete("return")`.

## External Documentation
[py_trees documentation](https://py-trees.readthedocs.io/)
