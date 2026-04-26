
import py_trees
import time

client = py_trees.blackboard.Client(name="Global")
client.register_key("task_queue", access=py_trees.common.Access.WRITE)
PREQUAL_TASKS = ["gate", "pole", "return"]

COMPETITION_TASKS = [
    "heading_out",
    "begin_assessment_gate",
    "avoid_debris_slalom",
    "recon_bins",
    "deploy_torpedoes",
    "resupply_octagon",
    "return_home"
]

client.task_queue = PREQUAL_TASKS.copy()
client.register_key("current_task", access=py_trees.common.Access.WRITE)
client.current_task = None
client.register_key("completed_tasks", access=py_trees.common.Access.WRITE)
client.completed_tasks = []

client.register_key("gate_found", access=py_trees.common.Access.WRITE)
client.gate_found = False
client.register_key("pole_found", access=py_trees.common.Access.WRITE)
client.pole_found = False

#TEMPORARY:
class PlaceholderAction(py_trees.behaviour.Behaviour):
    def __init__(self, name, message):
        super().__init__(name)
        self.message = message

    def update(self):
        print(self.message)
        return py_trees.common.Status.SUCCESS
    
class CheckBlackboardFlag(py_trees.behaviour.Behaviour):
    def __init__(self, name, flag_name):
        super().__init__(name)
        self.flag_name = flag_name
        self.bb = py_trees.blackboard.Client(name=name)
        self.bb.register_key(flag_name, access=py_trees.common.Access.READ)

    def update(self):
        if getattr(self.bb, self.flag_name):
            print(f"{self.flag_name} is true")
            return py_trees.common.Status.SUCCESS

        print(f"{self.flag_name} is false")
        return py_trees.common.Status.FAILURE
    



class DetectObject(py_trees.behaviour.Behaviour):
    def __init__(self, name, object_name, flag_name):
        super().__init__(name)
        self.object_name = object_name
        self.flag_name = flag_name
        self.bb = py_trees.blackboard.Client(name=name)
        self.bb.register_key(flag_name, access=py_trees.common.Access.WRITE)

    def update(self):
        print(f"Detecting {self.object_name}")
        setattr(self.bb, self.flag_name, True)
        print(f"{self.object_name} detected")
        return py_trees.common.Status.SUCCESS
    
class MarkTaskComplete(py_trees.behaviour.Behaviour):
    def __init__(self, name, task_name):
        super().__init__(name)
        self.task_name = task_name
        self.bb = py_trees.blackboard.Client(name=f"MarkComplete-{task_name}")
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.WRITE)

    def update(self):
        if self.task_name not in self.bb.completed_tasks:
            self.bb.completed_tasks.append(self.task_name)

        print(f"Task {self.task_name} is now complete")
        return py_trees.common.Status.SUCCESS

class SubAction(py_trees.behaviour.Behaviour):
    def __init__(self, name, direction):
        super().__init__(name)
        self.direction = direction

    def update(self):
        # real code
        print(f"Moving sub: {self.direction}")
        return py_trees.common.Status.SUCCESS

#write gettask class
class GetTask(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.bb = py_trees.blackboard.Client(name="GetTask")
        self.bb.register_key("current_task", access=py_trees.common.Access.WRITE)
        self.bb.register_key("task_queue", access=py_trees.common.Access.WRITE) #changed from read

    def update(self):
        # real code
        queue = self.bb.task_queue

        if not queue:
            print("no tasks left")
            return py_trees.common.Status.FAILURE
        else:
            self.bb.current_task = queue.pop(0)
            print(f"Current task: {self.bb.current_task}")
            return py_trees.common.Status.SUCCESS   



#write taskdone class
class TaskDone(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.bb = py_trees.blackboard.Client(name="TaskDone")
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.READ)

    def update(self):
        # real code
        task = self.bb.current_task
        if task in self.bb.completed_tasks:
            print(f"Task {task} already completed")
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE
class MoveToTask(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.bb = py_trees.blackboard.Client(name="MoveToTask")
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)

    def update(self):
        # real code
        task = self.bb.current_task
        print(f"Moving to {task}")
        #more real code maybe idk?
        return py_trees.common.Status.SUCCESS
class PerformTask(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.bb = py_trees.blackboard.Client(name="PerformTask")
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.WRITE)

        
    def update(self):
        # real code
        task = self.bb.current_task
        print(f"Performing {task}")
        self.bb.completed_tasks.append(task)
        #more real code maybe idk?
        print(f"Task {task} is now complete")
        return py_trees.common.Status.SUCCESS
def create_gate_subtree():
    gate_visible = CheckBlackboardFlag(
        name="Gate Visible?",
        flag_name="gate_found"
    )

    search_pattern = SubAction(
        name="Search Pattern For Gate",
        direction="slow forward scan for gate"
    )

    detect_gate = DetectObject(
        name="Detect Gate",
        object_name="gate",
        flag_name="gate_found"
    )

    search_gate = py_trees.composites.Selector(
        name="Find Gate",
        memory=False
    )

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

    align_gate = SubAction(
        name="Align With Gate",
        direction="align with gate"
    )

    drive_through_gate = SubAction(
        name="Drive Through Gate",
        direction="forward through gate"
    )

    gate_done = MarkTaskComplete(
        name="Mark Gate Complete",
        task_name="gate"
    )

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
def create_pole_subtree():
    pole_visible = CheckBlackboardFlag(
        name="Pole Visible?",
        flag_name="pole_found"
    )

    search_pattern = SubAction(
        name="Search Pattern For Pole",
        direction="slow scan for pole"
    )

    detect_pole = DetectObject(
        name="Detect Pole",
        object_name="pole",
        flag_name="pole_found"
    )

    search_pole = py_trees.composites.Selector(
        name="Find Pole",
        memory=False
    )

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

    approach_pole = SubAction(
        name="Approach Pole",
        direction="forward toward pole"
    )

    circle_pole = SubAction(
        name="Circle Pole",
        direction="circle around pole"
    )

    pole_done = MarkTaskComplete(
        name="Mark Pole Complete",
        task_name="pole"
    )
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
def create_return_subtree():
    #NEXT TODO: add blackboard cehcker to see if starting area is visible, and search for it etc.
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
    return_done = MarkTaskComplete(
        name="Mark Return Complete",
        task_name="return"
    )

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
class PerformPrequalTask(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        self.bb = py_trees.blackboard.Client(name="PerformPrequalTask")
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)

        self.task_trees = {
            "gate": create_gate_subtree(),
            "pole": create_pole_subtree(),
            "return": create_return_subtree()
        }

    def update(self):
        task = self.bb.current_task

        if task not in self.task_trees:
            print(f"No detailed prequal subtree exists for task: {task}")
            return py_trees.common.Status.FAILURE

        print(f"Running detailed subtree for: {task}")
        subtree = self.task_trees[task]
        subtree.tick_once()

        return subtree.status
    
def create_detailed_prequal_queue_tree():
    client.task_queue = PREQUAL_TASKS.copy()
    client.current_task = None
    client.completed_tasks = []
    client.gate_found = False
    client.pole_found = False
    get_task = GetTask(name="Get Task")
    move_to_task = MoveToTask(name="Move To Task")
    perform_prequal_task = PerformPrequalTask(name="Perform Detailed Prequal Task")
    task_done = TaskDone(name="Task Done")

    do_task = py_trees.composites.Sequence(name="Do Detailed Task", memory=True)
    do_task.add_children([
        move_to_task,
        perform_prequal_task
    ])

    fallback = py_trees.composites.Selector(name="Task Done Or Do Detailed Task", memory=False)
    fallback.add_children([
        task_done,
        do_task
    ])

    get_to_work = py_trees.composites.Sequence(name="Get To Work", memory=True)
    get_to_work.add_children([
        get_task,
        fallback
    ])

    root = py_trees.decorators.Repeat(
        child=get_to_work,
        num_success=-1,
        name="Repeat Detailed Prequal"
    )

    return root

def create_auv_tree(task_queue):
    
    client.task_queue = task_queue.copy()
    client.current_task = None
    client.completed_tasks = []
    get_task = GetTask(name="Get Task")
    move_to_task = MoveToTask(name="Move To Task")
    perform_task = PerformTask(name="Perform Task")
    task_done = TaskDone(name="Task Done")

    do_task = py_trees.composites.Sequence(name="Do Task", memory=True)
    do_task.add_children([move_to_task, perform_task])

    fallback = py_trees.composites.Selector(name="Fallback", memory=False)
    fallback.add_children([task_done, do_task])

    get_to_work = py_trees.composites.Sequence(name="Get To Work", memory=True)
    get_to_work.add_children([get_task, fallback])  

    root = py_trees.decorators.Repeat(child=get_to_work, num_success=-1, name="Repeat") #this repeats until a failure is returned
    return root

'''
print("Starting Prequalification Tree:\n")
prequal_tree = create_auv_tree(PREQUAL_TASKS)

for i in range(10):
    print(f"Prequal Tick {i+1}:")
    prequal_tree.tick_once()
'''
my_tree = create_detailed_prequal_queue_tree()

print("Starting Detailed Queue-Based Prequalification Behavior Tree:\n")

for i in range(20):
    print(f"\n\nTick {i+1}:")
    my_tree.tick_once()
    
print("\n\nStarting Broad Competition Tree:\n")
competition_tree = create_auv_tree(COMPETITION_TASKS)

for i in range(10):
    print(f"\nCompetition Tick {i+1}:")
    competition_tree.tick_once()
