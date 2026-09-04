#Used imports in this file
import py_trees

#Shared blackboard client and the leaf behaviors this tree is built from
from blackboard import client
from behaviors.navigation.moveToTask import MoveToTask
from behaviors.mission.getTask import GetTask
from behaviors.mission.taskDone import TaskDone
from behaviors.tasks.performTask import PerformTask


#Builds the coarse task-queue loop. task_queue is a list of task name strings.
def create_auv_tree(task_queue):
    #Reset the blackboard for a fresh run
    client.task_queue = task_queue.copy()
    client.current_task = None
    client.completed_tasks = []

    #Leaf nodes
    get_task = GetTask(name="Get Task")
    move_to_task = MoveToTask(name="Move To Task")
    perform_task = PerformTask(name="Perform Task")
    task_done = TaskDone(name="Task Done")

    #Drive to the task, then do it. Memory so it resumes mid-sequence.
    do_task = py_trees.composites.Sequence(name="Do Task", memory=True)
    do_task.add_children([move_to_task, perform_task])

    #Skip the work if the task is already done, otherwise run do_task
    fallback = py_trees.composites.Selector(name="Fallback", memory=False)
    fallback.add_children([task_done, do_task])

    #Grab the next task, then handle it
    get_to_work = py_trees.composites.Sequence(name="Get To Work", memory=True)
    get_to_work.add_children([get_task, fallback])

    #Repeat forever until GetTask fails on an empty queue
    root = py_trees.decorators.Repeat(child=get_to_work, num_success=-1, name="Repeat") #this repeats until a failure is returned
    return root
