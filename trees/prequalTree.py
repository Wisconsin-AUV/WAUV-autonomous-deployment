#Used imports in this file
import py_trees

#Shared blackboard state and the leaf behaviors this tree is built from
from blackboard import client, PREQUAL_TASKS
from behaviors.perception.checkBlackboardFlag import CheckBlackboardFlag
from behaviors.perception.detectObject import DetectObject
from behaviors.navigation.moveToTask import MoveToTask
from behaviors.navigation.subAction import SubAction
from behaviors.mission.getTask import GetTask
from behaviors.mission.markTaskCompleted import MarkTaskComplete
from behaviors.mission.taskDone import TaskDone
from behaviors.tasks.performPrequalTask import PerformPrequalTask


#Subtree for the gate task: find the gate, line up, drive through, mark done
def create_gate_subtree():
    #Guard, true once the gate has been seen
    gate_visible = CheckBlackboardFlag(
        name="Gate Visible?",
        flag_name="gate_found"
    )

    #Scan pattern used while searching for the gate
    search_pattern = SubAction(
        name="Search Pattern For Gate",
        direction="slow forward scan for gate"
    )

    #Detection step, sets gate_found on a hit
    detect_gate = DetectObject(
        name="Detect Gate",
        object_name="gate",
        flag_name="gate_found"
    )

    #Selector: skip the search if the gate is already visible
    search_gate = py_trees.composites.Selector(
        name="Find Gate",
        memory=False
    )

    #Search then detect, run in order
    search_sequence = py_trees.composites.Sequence(
        name="Search Then Detect Gate",
        memory=True
    )

    search_sequence.add_children([
        search_pattern,
        detect_gate
    ])

    search_gate.add_children([
        gate_visible,
        search_sequence
    ])

    #Movement steps once the gate is found
    align_gate = SubAction(
        name="Align With Gate",
        direction="align with gate"
    )

    drive_through_gate = SubAction(
        name="Drive Through Gate",
        direction="forward through gate"
    )

    #Mark the task done so TaskDone will skip it if the tree comes back
    gate_done = MarkTaskComplete(
        name="Mark Gate Complete",
        task_name="gate"
    )

    #Full gate sequence, top to bottom
    gate_sequence = py_trees.composites.Sequence(
        name="Gate Subtree",
        memory=True
    )

    gate_sequence.add_children([
        search_gate,
        align_gate,
        drive_through_gate,
        gate_done
    ])

    return gate_sequence


#Subtree for the pole task, same shape as the gate subtree with pole names/flag
def create_pole_subtree():
    #Guard, true once the pole has been seen
    pole_visible = CheckBlackboardFlag(
        name="Pole Visible?",
        flag_name="pole_found"
    )

    #Scan pattern used while searching for the pole
    search_pattern = SubAction(
        name="Search Pattern For Pole",
        direction="slow scan for pole"
    )

    #Detection step, sets pole_found on a hit
    detect_pole = DetectObject(
        name="Detect Pole",
        object_name="pole",
        flag_name="pole_found"
    )

    #Selector: skip the search if the pole is already visible
    search_pole = py_trees.composites.Selector(
        name="Find Pole",
        memory=False
    )

    #Search then detect, run in order
    search_sequence = py_trees.composites.Sequence(
        name="Search Then Detect Pole",
        memory=True
    )

    search_sequence.add_children([
        search_pattern,
        detect_pole
    ])

    search_pole.add_children([
        pole_visible,
        search_sequence
    ])

    #Movement steps once the pole is found
    approach_pole = SubAction(
        name="Approach Pole",
        direction="forward toward pole"
    )

    circle_pole = SubAction(
        name="Circle Pole",
        direction="circle around pole"
    )

    #Mark the task done
    pole_done = MarkTaskComplete(
        name="Mark Pole Complete",
        task_name="pole"
    )
    #Full pole sequence, top to bottom
    pole_sequence = py_trees.composites.Sequence(
        name="Pole Subtree",
        memory=True
    )

    pole_sequence.add_children([
        search_pole,
        approach_pole,
        circle_pole,
        pole_done
    ])

    return pole_sequence


#Subtree for the return task: head home and surface
def create_return_subtree():
    #NEXT TODO: add blackboard checker to see if starting area is visible, and search for it etc.
    turn_home = SubAction(
        name="Turn Toward Start",
        direction="turn toward start area"
    )

    drive_home = SubAction(
        name="Drive Back",
        direction="forward back to start area"
    )

    surface = SubAction(
        name="Surface",
        direction="surface"
    )
    #Mark the task done
    return_done = MarkTaskComplete(
        name="Mark Return Complete",
        task_name="return"
    )

    #No perception step yet, just run the moves in order
    return_sequence = py_trees.composites.Sequence(
        name="Return Subtree",
        memory=True
    )

    return_sequence.add_children([
        turn_home,
        drive_home,
        surface,
        return_done
    ])

    return return_sequence


#Builds the detailed prequal loop: same skeleton as the competition tree, but the
#perform step dispatches into one of the subtrees above.
def create_detailed_prequal_queue_tree():
    #Reset the blackboard for a fresh run, including the perception flags
    client.task_queue = PREQUAL_TASKS.copy()
    client.current_task = None
    client.completed_tasks = []
    client.gate_found = False
    client.pole_found = False

    #Leaf nodes
    get_task = GetTask(name="Get Task")
    move_to_task = MoveToTask(name="Move To Task")

    #Perform node gets a subtree for each task it might be handed
    perform_prequal_task = PerformPrequalTask(
        name="Perform Detailed Prequal Task",
        task_trees={
            "gate": create_gate_subtree(),
            "pole": create_pole_subtree(),
            "return": create_return_subtree(),
        },
    )
    task_done = TaskDone(name="Task Done")

    #Drive to the task, then run its subtree
    do_task = py_trees.composites.Sequence(name="Do Detailed Task", memory=True)
    do_task.add_children([
        move_to_task,
        perform_prequal_task
    ])

    #Skip the work if the task is already done, otherwise run do_task
    fallback = py_trees.composites.Selector(name="Task Done Or Do Detailed Task", memory=False)
    fallback.add_children([
        task_done,
        do_task
    ])

    #Grab the next task, then handle it
    get_to_work = py_trees.composites.Sequence(name="Get To Work", memory=True)
    get_to_work.add_children([
        get_task,
        fallback
    ])

    #Repeat forever until GetTask fails on an empty queue
    root = py_trees.decorators.Repeat(
        child=get_to_work,
        num_success=-1,
        name="Repeat Detailed Prequal"
    )

    return root
