#Used imports in this file
import py_trees
from behaviors.behavior import Behavior
 
#Get Task Class
class GetTask(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        #Getting the current task
        self.bb = py_trees.blackboard.Client(name="GetTask")

        #Writing the task to the py_trees table so other files can access the current state of the update
        self.bb.register_key("current_task", access=py_trees.common.Access.WRITE)
        self.bb.register_key("task_queue", access=py_trees.common.Access.WRITE)

    #Update method that is used to perform actions.
    def update(self):
        # Pulling the queue from the blackboard
        queue = self.bb.task_queue

        #Update status to failure if there is no tasks left. Otherwise print the task. Set to sucess.
        if not queue:
            print("no tasks left")
            return py_trees.common.Status.FAILURE
        else:
            self.bb.current_task = queue.pop(0)
            print(f"Current task: {self.bb.current_task}")
            return py_trees.common.Status.SUCCESS   