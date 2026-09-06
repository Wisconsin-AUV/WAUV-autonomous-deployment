#Entry point. Builds each tree and ticks it until it runs out of tasks.
#A tick is one full pass over the tree from the root, and completes one task.
#The root is a Repeat decorator: it returns RUNNING while work remains and
#FAILURE once GetTask hits an empty queue, which is the signal to stop.
import py_trees

from trees.prequalTree import create_detailed_prequal_queue_tree
from trees.competitionTree import create_auv_tree

#Build the detailed prequal tree (gate / pole / return subtrees)
my_tree = create_detailed_prequal_queue_tree()

#Task list for the broad competition run
COMPETITION_TASKS = [
    "heading_out",
    "begin_assessment_gate",
    "avoid_debris_slalom",
    "recon_bins",
    "deploy_torpedoes",
    "resupply_octagon",
    "return_home"
]


#Loop for the prequalification tasks. Runs until the tree returns FAILURE.
tick = 1
while my_tree.status != py_trees.common.Status.FAILURE:
    print(f"\n\nTick {tick}:")
    my_tree.tick_once()
    tick += 1

#Build and run the competition tree the same way
print("\n\nStarting Broad Competition Tree:\n")
competition_tree = create_auv_tree(COMPETITION_TASKS)

tick = 1
while competition_tree.status != py_trees.common.Status.FAILURE:
    print(f"\nCompetition Tick {tick}:")
    competition_tree.tick_once()
    tick += 1
