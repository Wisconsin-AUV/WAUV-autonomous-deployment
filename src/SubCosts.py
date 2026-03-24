import torch

class SubCosts:
    def __init__(self, device='cpu'):
        self.device = device

        # Obstacle data from depth camera - shape [num_obstacles, 3]
        self.obstacles = None
        self.safe_distance = 1.0   # meters: hard collision boundary

        # Goal position [x, y, z] in global frame
        self.goal = None
        self.goal_weight = 10.0    # tune this up to make the sub more aggressive toward goal

        # Depth limits (NED convention: z positive = downward)
        # Set max_depth to slightly less than actual pool/ocean floor
        self.max_depth = 3.0       # meters: don't go deeper than this (floor limit)
        self.min_depth = 0.3       # meters: don't accidentally surface
        self.depth_weight = 500.0  # large enough to hard-discourage floor/surface hits

    def set_goal(self, goal_position):
        """
        Set the target 3D waypoint before each MPPI command loop.
        goal_position: list or tensor [x, y, z]

        Example:
            costs.set_goal([5.0, 3.0, 1.5])  # 1.5m depth, 5m forward, 3m right
        """
        self.goal = torch.tensor(goal_position, dtype=torch.float32, device=self.device)

    def update_obstacles(self, obstacle_tensor):
        """
        Call from your ROS2 loop whenever a new depth camera frame arrives.
        obstacle_tensor: shape [num_obstacles, 3] with x,y,z points in global frame.
        """
        self.obstacles = obstacle_tensor.to(self.device)

    def running_cost(self, state, action=None):
        """
        Cost evaluated at every step of every MPPI rollout.
        state:  [batch_size, 12] -> [x, y, z, phi, theta, psi, u, v, w, p, q, r]
        action: [batch_size, 4]  -> [surge, sway, heave, yaw_torque]
        returns: cost [batch_size]
        """
        batch_size = state.shape[0]
        cost = torch.zeros(batch_size, device=self.device)

        positions = state[:, :3]  # [x, y, z]
        z = state[:, 2]           # depth (positive = down in NED)

        # --- 1. Obstacle Avoidance ---
        if self.obstacles is not None and len(self.obstacles) > 0:
            # Distance from each rollout position to every obstacle point
            dists = torch.cdist(positions, self.obstacles)  # [batch_size, num_obstacles]
            min_dists, _ = torch.min(dists, dim=1)

            # Hard penalty for being inside the safety bubble
            cost[min_dists < self.safe_distance] += 10000.0

            # Soft repulsive gradient: smoothly steers away before hitting the hard boundary
            cost += 5.0 / (min_dists + 0.1)

        # --- 2. Goal Seeking ---
        # Penalise distance to the current target waypoint.
        # Call costs.set_goal([x, y, z]) to update the target from your mission state machine.
        if self.goal is not None:
            goal_dist = torch.norm(positions - self.goal.unsqueeze(0), dim=1)
            cost += self.goal_weight * goal_dist

        # --- 3. Depth Floor / Ceiling ---
        # Penalise getting too deep (floor) or too shallow (surface breach).
        # Uses a soft ramp so the penalty grows the further the limit is exceeded.
        too_deep    = torch.clamp(z - self.max_depth,    min=0.0)
        too_shallow = torch.clamp(self.min_depth - z,    min=0.0)
        cost += self.depth_weight * (too_deep + too_shallow)

        return cost

    def terminal_cost(self, state):
        """
        Extra cost applied ONLY at the final step of the MPPI horizon.
        Weighting the end state more heavily biases the controller to actually
        reach the goal rather than just drifting in its direction.
        """
        batch_size = state.shape[0]
        cost = torch.zeros(batch_size, device=self.device)

        if self.goal is not None:
            positions = state[:, :3]
            goal_dist = torch.norm(positions - self.goal.unsqueeze(0), dim=1)
            cost += 5.0 * self.goal_weight * goal_dist  # 5x the running weight

        return cost
