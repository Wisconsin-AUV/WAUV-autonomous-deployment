import torch

class SubDynamics:
    def __init__(self, dt=0.1, device='cpu'):
        """
        PyTorch-compatible dynamics model for an underwater vehicle.
        Must handle batched tensor operations for MPPI rollouts.
        """
        self.dt = dt
        self.device = device

        #TODO all the below lel
        
        # Mass Matrix
        # Format:[Mass_X, Mass_Y, Mass_Z, Inertia_Roll, Inertia_Pitch, Inertia_Yaw]
        self.M = None 
        self.M_inv = None  

        # Drag Coefficients (Linear and Quadratic)
        # Format:[X, Y, Z, K, M, N]
        self.D_lin = None
        self.D_quad = None

        # Restoring Forces (Gravity and Buoyancy)
        self.W = None    # Weight in Newtons
        self.B = None    # Buoyancy in Newtons
        self.z_b = None  # distance fromCOG to COB


    def __call__(self, state, action):
        """
        state: [batch_size, 12] ->[x, y, z, phi, theta, psi, u, v, w, p, q, r]
        action:[u,v,w,yaw]
        """

        eta = state[:, :6] # global frame positions [x, y, z, phi, theta, psi]
        nu = state[:, 6:] # body frame stuff [u, v, w, p, q, r]

        phi, theta, psi = eta[:, 3], eta[:, 4], eta[:, 5]
        u, v, w = nu[:, 0], nu[:, 1], nu[:, 2]
        p, q, r = nu[:, 3], nu[:, 4], nu[:, 5]

        # TODO Restoring Forces (Gravity & Buoyancy)
        # 6 equations mapping W and B into the body frame.
        g_eta = None

        # TODO Hydrodynamic Drag
        #  Calculate linear drag: D_lin * nu
        # Calculate quadratic drag: D_quad * abs(nu) * nu
        drag = None
        
        # TODO Acceleration (Fossen's Equation)
        # Calculate net force: tau - drag - g_eta
        # Multiply by M_inv to get body acceleration: dot_nu
        dot_nu = None

        #TODO Update Body Velocity
        nu_next = None
        

        return next_state
