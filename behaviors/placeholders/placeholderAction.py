#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Placeholder Action Class
#TEMPORARY: stand-in for a behavior that has not been written yet
class PlaceholderAction(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, message):
        super().__init__(name)
        #Text to print when this node ticks, no blackboard access
        self.message = message

    #Update method that is used to perform actions.
    def update(self):
        #Print the message and always report success so the tree keeps ticking
        print(self.message)
        return py_trees.common.Status.SUCCESS
