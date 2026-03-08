import torch

class SubDynamics:
    def __init__(self, dt=0.1, device='cpu'):
        """
        PyTorch-compatible dynamics model for an underwater vehicle.
        Must handle batched tensor operations for MPPI rollouts.
        """
        self.dt = dt
        self.device = device

    def __call__(self, state, action):
        return next_state