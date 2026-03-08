import torch
from pytorch_mppi import mppi

from SubDynamics import SubDynamics
from SubCosts import SubCosts

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Running MPPI on: {device}")

    dynamics = SubDynamics(dt=0.1, device=device)
    costs = SubCosts(device=device)

    # Define MPPI Parameters
    nx = 12 # State dimensions:[x, y, z, roll, pitch, yaw, vx, vy, vz, roll_rate, pitch_rate, yaw_rate]
    nu = 4 # Action dimensions: [vx, vy, vz, yaw_rate]
    
    # Noise Sigma: How much should MPPI randomly explore?
    # Shape: [nu, nu]. Diagonal matrix representing variance for [vx, vy, vz, yaw_rate]
    noise_sigma = torch.tensor([[0.5, 0.0, 0.0, 0.0],  # vx variance[0.0, 0.5, 0.0, 0.0],  # vy variance[0.0, 0.0, 0.2, 0.0],  # vz variance (heave is usually slower)[0.0, 0.0, 0.0, 0.5]   # yaw_rate variance
    ], device=device)

    # Max/Min velocities your sub can physically move at
    u_min = torch.tensor([-1.0, -1.0, -0.5, -1.0], device=device)
    u_max = torch.tensor([ 1.0,  1.0,  0.5,  1.0], device=device)

    # Create the MPPI Controller
    mppi_ctrl = mppi.MPPI(
        dynamics=dynamics,
        running_cost=costs.running_cost,
        nx=nx,
        noise_sigma=noise_sigma,
        num_samples=1000,
        horizon=20,
        device=device,
        u_min=u_min,
        u_max=u_max,
        lambda_=1.0
    )



if __name__ == "__main__":
    main()
