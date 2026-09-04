## DEV INFO
Author: Conner O'Reilly
Wisc email: ccoreilly@wisc.edu
Last modified date: 09/01/2026
Other contact info(optional): oreillyconner@protonmail.com

# WAUV-autonomous-deployment
Mission control logic for the AUV. Built using `py_trees` documentation for py_trees is attached at the bottom of this readme. The AUV is given an ordered list of mission tasks. A behavior tree walks that list pulling the next task, drives
to the task, performs the task and marks the task as completed. This is repeated until the list is exhausted.

## TODO
Everything here is currently **stubbed** behaviours print what they would
command instead of talking to hardware. The structure is correct actions are not.

## trees/competitionTree.py
One coarse large task node, a full competition run with many tasks.

## trees/prequalTree.py
Dispatches into a custom subtree per task (search → align → drive → mark done) with the gate challenge 

## Shared state

Behaviors do not pass anything to each other directly. They share one py_trees
blackboard, set up in `blackboard.py`. One node writes a key and a later node
reads it. There are currently `four` keys.

`task_queue` is the list of tasks not started yet, front of the list first. It is
seeded in `blackboard.py`, and `GetTask` pops from it.

`current_task` is the task being worked. `GetTask` sets it. Meanwhile `MoveToTask`,
`PerformTask`, `PerformPrequalTask`, and `TaskDone` read it.

`completed_tasks` is the list of tasks already finished. `PerformTask` and
`MarkTaskComplete` append to it, and `TaskDone` checks it.

`gate_found` and `pole_found` are perception flags. `DetectObject` sets one to true
once it sees the object, and `CheckBlackboardFlag` reads it so the search stops
running.

## Control flow

Both trees run the same loop and finish one task per tick, where a tick is one
full pass over the tree from the root.

`GetTask` takes the next task off `task_queue` and stores it in `current_task`. If
the queue is empty it returns `FAILURE`, and the `Repeat` at the root stops the
tree.

With a task in hand a `Selector` tries `TaskDone` first. If `current_task` is
already in `completed_tasks` the selector succeeds and the tick ends. Otherwise it
falls through to a `Sequence` that runs `MoveToTask` to drive to the task and then
the perform node.

The perform node is the only difference between the two trees. `competitionTree`
runs `PerformTask`, which handles the whole task in one node.
On the other hand `prequalTree` runs `PerformPrequalTask`, which ticks the subtree for `current_task` The subtree shapes are described in trees readme(listed below).

## Structure

## Folder
Every folder under `behaviors/` maps to a real part of the vehicle, so a new
behaviour has an obvious home: a new sensor check goes in `perception/`, a new
thruster manuver in `navigation/`, and so on.

## Root
main.py                 build both trees, tick them
blackboard.py           shared blackboard keys + starting values

## Behaviors
Described in a seperate readme file.

## Tree              
Assemble behaviors into useable trees see trees/README.md

## External Documentation
[trees/README.md](trees/README.md)
[blackboard.py](blackboard.py)