## DEV INFO
Author: Conner O'Reilly
Wisc email: ccoreilly@wisc.edu
Last modified date: 09/01/2026
Other contact info(optional): oreillyconner@protonmail.com

## Behaviors
Every file here defines one leaf node of the behavior tree. A behavior
does its work inside `update()` and returns its status that tells its parent
composite what happened. There are three possible results: 
`SUCCESS` when it did its job or itscondition holds, 
`FAILURE` when it could not or the condition does not hold
`RUNNING` while the job is still in progress.

Behaviors never call each other. They communicate through the shared blackboard
described in the root readme, and each entry below notes which
keys the behavior reads or writes. The trees decide the order behaviors run in,
see the trees readme.

## Structure
Folders group behaviors by the part of the AUV they belong to.
`perception` vision based conditions
`navigation` navigation and directional based systems
`mission` task queue tracking
`tasks` the nodes that perform the actions
`placeholders` actions that don't do anything and should be replaced

## TODO
Every behavior is currently a stub that prints instead of driving hardware, and
nothing returns `RUNNING` yet. The real actuation is yet to be implemented and must be created. Most likely will need to be tied in from another branch or repo.

## perception
Sensing and the blackboard flags that cache what has been sensed.

### `detectObject.py` — `DetectObject(name, object_name, flag_name)`
Runs the detector for object_name. On a hit it sets blackboard `flag_name` to
`True` and returns `SUCCESS`. 
*Stub:* always "detects" immediately and writes `flag_name`.

### `checkBlackboardFlag.py` — `CheckBlackboardFlag(name, flag_name)`
Pure condition. `SUCCESS` if blackboard `flag_name` is true, else `FAILURE`.
Used as a guard so a search only runs while the flag is still `False`.
Reads `flag_name`.

## navigation
Commands to the motion controller.

### `moveToTask.py` — `MoveToTask(name)`
Transit to the location of `current_task`. Returns `SUCCESS`.
Reads `current_task`. 
*Stub:* prints the move.

### `subAction.py` — `SubAction(name, direction)`
Generic parametrised action. `direction` is a free-text instruction
("align with gate", "circle around pole", "surface", "slow forward scan").
Always returns `SUCCESS`. No blackboard access. This is the building block the
prequal subtrees are made of.

## mission
Bookkeeping for the ordered task list. No hardware.

### `getTask.py` — `GetTask(name)`
Pops the front of `task_queue` into `current_task` and returns `SUCCESS`.
If the queue is empty, returns `FAILURE`. Signal the top-level `Repeat` uses to stop.
Reads/writes `task_queue`, writes `current_task`.

### `markTaskCompleted.py` — `MarkTaskComplete(name, task_name)`
Appends `task_name` to `completed_tasks` (if not already there) and returns
`SUCCESS`. Each prequal subtree ends with one of these.
Writes `completed_tasks`.

### `taskDone.py` — `TaskDone(name)`
Condition. `SUCCESS` if `current_task` is in `completed_tasks` (so the tree can
skip re-doing it), else `FAILURE`.
Reads `current_task`, `completed_tasks`.

## tasks
The node that sits under "Do Task" and actually carries the task out. The two
trees pick different ones.

### `performTask.py` — `PerformTask(name)`
Coarse version:\
prints "Performing X", appends `current_task` to `completed_tasks`, returns `SUCCESS`. One node = one whole task. Used by
`competitionTree`.
Reads `current_task`, writes `completed_tasks`.
*NOTE* This is currently just a stub there needs to be logic implemented to actually perform the task

### `performPrequalTask.py` — `PerformPrequalTask(name, task_trees)`
Fine version: `task_trees` is `{task_name: py_trees subtree}`, supplied by the
tree builder. `update()` looks up `current_task`, ticks that subtree once, and
returns the subtree's status. If there is no subtree for the task, returns
`FAILURE`. Used by `prequalTree`.
Reads `current_task`.
*NOTE* This is more detailed than the performTask. Still doesnt implement anything concrete that works.

## placeholders
Temporary stand-ins for behaviors that have not been written yet.

### `placeholderAction.py` — `PlaceholderAction(name, message)`
Prints `message`, returns `SUCCESS`. Drop this in wherever a real behavior is
missing so the tree still ticks. Currently unused.

## External Documentation
[py_trees documentation](https://py-trees.readthedocs.io/)
[trees/README.md](../trees/README.md)
[README](../README.md)