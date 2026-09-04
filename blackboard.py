#Used imports in this file
import py_trees

#Shared global blackboard state. Every tree and behavior reads and writes here
#instead of passing values to each other directly.

#Default task list for the prequal run
PREQUAL_TASKS = ["gate", "pole", "return"]

#One client that owns every key
client = py_trees.blackboard.Client(name="Global")

#Register every key up front so any behavior can attach to it later
client.register_key("task_queue", access=py_trees.common.Access.WRITE)       #tasks not started yet
client.register_key("current_task", access=py_trees.common.Access.WRITE)     #task being worked right now
client.register_key("completed_tasks", access=py_trees.common.Access.WRITE)  #tasks already finished
client.register_key("gate_found", access=py_trees.common.Access.WRITE)       #perception flag, set by DetectObject
client.register_key("pole_found", access=py_trees.common.Access.WRITE)       #perception flag, set by DetectObject

#Starting values. The tree builders reset these again when they run.
client.task_queue = PREQUAL_TASKS.copy()
client.current_task = None
client.completed_tasks = []
client.gate_found = False
client.pole_found = False
