#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Task Done Class
class TaskDone(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name="TaskDone")

        #Only reading here, this node checks state and never changes it
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.READ)

    #Update method that is used to perform actions.
    def update(self):
        #Pull the task the tree is currently working on
        task = self.bb.current_task

        #Success if it is already in the completed list, so the tree can skip redoing it
        if task in self.bb.completed_tasks:
            print(f"Task {task} already completed")
            return py_trees.common.Status.SUCCESS

        #Otherwise report failure so the tree goes and does the task
        return py_trees.common.Status.FAILURE
