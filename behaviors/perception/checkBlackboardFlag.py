#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Check Blackboard Flag Class
class CheckBlackboardFlag(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, flag_name):
        super().__init__(name)
        #Which blackboard flag this node checks, e.g. "gate_found"
        self.flag_name = flag_name

        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name=name)

        #Only reading here, this node checks state and never changes it
        self.bb.register_key(flag_name, access=py_trees.common.Access.READ)

    #Update method that is used to perform actions.
    def update(self):
        #Success if the flag is set, so the tree can skip the search step
        if getattr(self.bb, self.flag_name):
            print(f"{self.flag_name} is true")
            return py_trees.common.Status.SUCCESS

        #Otherwise failure so the tree goes and runs the search
        print(f"{self.flag_name} is false")
        return py_trees.common.Status.FAILURE
