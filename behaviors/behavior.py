#Used imports in this file
from abc import ABC, abstractmethod

#Behavior Base Class
#Template every behavior in this section inherits from, alongside
#py_trees.behaviour.Behaviour. It forces each node to define update(),
#so a class that forgets it fails at instantiation instead of silently
#doing nothing.
class Behavior(ABC):
    #Every behavior must implement this. Called each tick, returns a
    #py_trees.common.Status (SUCCESS / FAILURE / RUNNING).
    @abstractmethod
    def update(self):
        pass
