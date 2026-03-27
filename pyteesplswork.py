import py_trees
import time


class MoveSub(py_trees.behaviour.Behaviour):
    def __init__(self, name, direction):
        super().__init__(name)
        self.direction = direction

    def update(self):
        # real code
        print(f"Moving sub: {self.direction}")
        return py_trees.common.Status.SUCCESS


def create_auv_tree():
    root = py_trees.composites.Selector(name="AUV Main", memory=False)
    
    # Priority 1
    emergency = py_trees.composites.Sequence(name="Check bad", memory=False)
    

    # Priority 2 actual logic
    mission_sequence = py_trees.composites.Sequence(name="Gate Mission", memory=True)
    
    find_gate = MoveSub(name="Search for Gate", direction="Spinning")
    align_gate = MoveSub(name="Align with Gate", direction="Forward-10")
    pass_gate = MoveSub(name="Pass Through", direction="Forward-50")

    mission_sequence.add_children([find_gate, align_gate, pass_gate])
    
    root.add_children([emergency, mission_sequence])
    return root


my_tree = create_auv_tree()
print("Starting AUV Behavior Tree: \n\n\n\n\n")

for i in range(3):
    print(f"Tick {i+1}:")
    my_tree.tick_once() 
