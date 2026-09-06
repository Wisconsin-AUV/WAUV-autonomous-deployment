#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Move To Task Class
class MoveToTask(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name="MoveToTask")

        #Only reading here, this node needs to know which task to drive toward
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)

    #Update method that is used to perform actions.
    def update(self):
        #Pull the task the tree is currently working on
        task = self.bb.current_task

        #Drive the sub to that task's location
        #Stub: just prints, real motion commands go here later
        print(f"Moving to {task}")
        return py_trees.common.Status.SUCCESS
