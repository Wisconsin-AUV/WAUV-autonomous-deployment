#Used imports in this file
import py_trees
from behaviors.behavior import Behavior

#Detect Object Class
class DetectObject(Behavior, py_trees.behaviour.Behaviour):
    def __init__(self, name, object_name, flag_name):
        super().__init__(name)
        #What we are looking for and which flag to set once we find it
        self.object_name = object_name
        self.flag_name = flag_name

        #Client for reaching the blackboard
        self.bb = py_trees.blackboard.Client(name=name)

        #Writing the flag so other files know the object has been seen
        self.bb.register_key(flag_name, access=py_trees.common.Access.WRITE)

    #Update method that is used to perform actions.
    def update(self):
        #Run the detector for the object
        #Stub: always "detects" immediately, real vision goes here later
        print(f"Detecting {self.object_name}")

        #Latch the flag on the blackboard so the search stops running
        setattr(self.bb, self.flag_name, True)

        #Report the hit and success
        print(f"{self.object_name} detected")
        return py_trees.common.Status.SUCCESS
