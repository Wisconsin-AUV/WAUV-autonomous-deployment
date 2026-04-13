
import py_trees
import time

client = py_trees.blackboard.Client(name="Global")
client.register_key("task_queue", access=py_trees.common.Access.WRITE)
client.task_queue = ["gate", "pole", "return"]
client.register_key("current_task", access=py_trees.common.Access.WRITE)
client.current_task = None
client.register_key("completed_tasks", access=py_trees.common.Access.WRITE)
client.completed_tasks = []

class MoveSub(py_trees.behaviour.Behaviour):
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
        self.bb.register_key("task_queue", access=py_trees.common.Access.READ)

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

def create_auv_tree():
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
my_tree = create_auv_tree()
print("Starting AUV Behavior Tree: \n\n\n\n\n")

for i in range(20):
    print(f"Tick {i+1}:")
    my_tree.tick_once() 
