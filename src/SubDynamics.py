import torch
import numpy as np

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
        self.M_inv = 1/self.M  

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

        # Maps the 4-DOF input action[u, v, w, yaw] into 6-DOF body forces/torques
        batch_size = state.shape[0]
        tau = torch.zeros((batch_size, 6), device=self.device)
        tau[:, 0] = action[:, 0]  # Surge force
        tau[:, 1] = action[:, 1]  # Sway force
        tau[:, 2] = action[:, 2]  # Heave force
        tau[:, 5] = action[:, 3]  # Yaw torque
        # Roll (K) and Pitch (M) torques are assumed 0 since they aren't actuated

        #   Restoring Forces (Gravity & Buoyancy)
        # 6 equations mapping W and B into the body frame.
        g_eta = torch.stack([
            (self.W - self.B) * torch.sin(theta),
            -(self.W - self.B) * torch.cos(theta) * torch.sin(phi),
            -(self.W - self.B) * torch.cos(theta) * torch.cos(phi),
            -self.z_b * self.B * torch.cos(theta) * torch.sin(phi),
            -self.z_b * self.B * torch.sin(theta),
            torch.zeros_like(theta)
        ], dim=1)

        # Hydrodynamic Drag
        #  Calculate linear drag
        lin_drag = self.D_lin * nu
        # Calculate quadratic drag:
        quad_drag = self.D_quad * torch.abs(nu) * nu
        drag = lin_drag + quad_drag
        
        # Acceleration (Fossen's Equation)
        net_force = tau - drag - g_eta
        dot_nu = self.M_inv*(net_force)

        #Update Body Velocity
        nu_next = nu + dot_nu * self.dt
        
        #convert body frame to global frame
        c_phi, s_phi = torch.cos(phi), torch.sin(phi)
        c_theta, s_theta = torch.cos(theta), torch.sin(theta)
        c_psi, s_psi = torch.cos(psi), torch.sin(psi)

        dot_eta = torch.zeros_like(eta)

        # Linear velocities
        dot_eta[:, 0] = u*(c_psi*c_theta) + v*(c_psi*s_theta*s_phi - s_psi*c_phi) + w*(c_psi*s_theta*c_phi + s_psi*s_phi)
        dot_eta[:, 1] = u*(s_psi*c_theta) + v*(s_psi*s_theta*s_phi + c_psi*c_phi) + w*(s_psi*s_theta*c_phi - c_psi*s_phi)
        dot_eta[:, 2] = -u*s_theta + v*(c_theta*s_phi) + w*(c_theta*c_phi)
        
        # Angular velocities
        dot_eta[:, 3] = p + q*(s_phi*s_theta/c_theta_safe) + r*(c_phi*s_theta/c_theta_safe)
        dot_eta[:, 4] = q*c_phi - r*s_phi
        dot_eta[:, 5] = q*(s_phi/c_theta_safe) + r*(c_phi/c_theta_safe)

        # Global position update
        eta_next = eta + dot_eta * self.dt

        # Combine updated eta and nu into next_state
        next_state = torch.cat([eta_next, nu_next], dim=1)

        return next_state