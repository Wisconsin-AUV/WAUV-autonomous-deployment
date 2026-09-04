#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Perform Task Class
#Coarse version, does a whole task in one node. Used by the competition tree.
class PerformTask(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super().__init__(name)
        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name="PerformTask")

        #Reading which task to do, writing the completed list when it is done
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)
        self.bb.register_key("completed_tasks", access=py_trees.common.Access.WRITE)

    #Update method that is used to perform actions.
    def update(self):
        #Pull the task the tree is currently working on
        task = self.bb.current_task

        #Carry out the task
        #Stub: just prints, real task logic needs to be implemented here
        print(f"Performing {task}")

        #Mark it finished so TaskDone will skip it next time around
        self.bb.completed_tasks.append(task)

        #Report the result and success
        print(f"Task {task} is now complete")
        return py_trees.common.Status.SUCCESS
