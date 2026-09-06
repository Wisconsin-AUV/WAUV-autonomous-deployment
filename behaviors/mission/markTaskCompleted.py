#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Mark Task Complete Class
class MarkTaskComplete(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, task_name):
        super().__init__(name)
        #The task this node is responsible for marking done
        self.task_name = task_name

        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name=f"MarkComplete-{task_name}")

        #Writing to the completed list so other files can see the task is finished
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.WRITE)

    #Update method that is used to perform actions.
    def update(self):
        #Add the task to the completed list, but only once
        if self.task_name not in self.bb.completed_tasks:
            self.bb.completed_tasks.append(self.task_name)

        #Print the result and report success
        print(f"Task {self.task_name} is now complete")
        return py_trees.common.Status.SUCCESS
