#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Sub Action Class
class SubAction(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, direction):
        super().__init__(name)
        #Free-text movement instruction, e.g. "align with gate" or "surface"
        #No blackboard access, everything this node needs is passed in
        self.direction = direction

    #Update method that is used to perform actions.
    def update(self):
        #Issue the movement command
        #Stub: just prints, real motion commands go here later
        print(f"Moving sub: {self.direction}")
        return py_trees.common.Status.SUCCESS
