#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Perform Prequal Task Class
#Fine version, dispatches into a hand-built subtree per task. Used by the prequal tree.
class PerformPrequalTask(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, task_trees):
        super().__init__(name)
        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name="PerformPrequalTask")

        #Only reading here, this node needs to know which task to run
        self.bb.register_key("current_task", access=py_trees.common.Access.READ)

        #{task_name: pre-built py_trees subtree}, supplied by the tree builder
        self.task_trees = task_trees

    #Update method that is used to perform actions.
    def update(self):
        #Pull the task the tree is currently working on
        task = self.bb.current_task

        #Fail if we have no subtree defined for this task
        if task not in self.task_trees:
            print(f"No detailed prequal subtree exists for task: {task}")
            return py_trees.common.Status.FAILURE

        #Tick the matching subtree once and hand its status back up to the main tree
        print(f"Running detailed subtree for: {task}")
        subtree = self.task_trees[task]
        subtree.tick_once()

        return subtree.status
