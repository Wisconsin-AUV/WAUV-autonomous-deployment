#!/bin/bash
set -e

# Check Ubuntu Version
if [[ $(lsb_release -rs) != "22.04" ]]; then
    echo "ERROR: This script requires Ubuntu 22.04"
    exit 1
fi

sudo apt-get update
sudo apt-get install -y curl gnupg lsb-release build-essential cmake git
sudo apt-get install -y python3-pip

# FIX: ensure modern pip before anything uses it
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install pynput

# add to dialout to enable serial communication through the USB
sudo usermod -aG dialout "$USER"

# stop ModemManager
sudo systemctl stop ModemManager 2>/dev/null || true
sudo systemctl disable ModemManager 2>/dev/null || true

# Install ROS2 Humble
if ! command -v ros2 &> /dev/null; then
    echo "Installing ROS2 Humble..."

    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y ros-humble-ros-base \
                        python3-colcon-common-extensions \
                        python3-rosdep \
                        python3-vcstool
fi

# Source ROS
if ! grep -q "ros/humble/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
fi

# Install MAVROS
sudo apt-get install -y ros-humble-mavros \
                    ros-humble-mavros-extras \
                    geographiclib-tools # dependency

sudo geographiclib-get-geoids egm96-5 || true

# Create ROS2 Workspace
mkdir -p ~/WAUV/WAUVSim/src
cd ~/WAUV/WAUVSim

source /opt/ros/humble/setup.bash

# Install Dependencies & Build
cd ~/WAUV/WAUVSim

source /opt/ros/humble/setup.bash

# Ensure rosdep is installed
sudo apt-get install -y python3-rosdep

# Initialize rosdep
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "Initializing rosdep..."
    sudo rosdep init
fi

# Update rosdep
rosdep update

# Install dependencies
rosdep install --from-paths src --ignore-src -r -y

python3 -m pip install "setuptools<80"

# Build workspace
colcon build --symlink-install

# Ensure workspace is sourced properly
if ! grep -q "WAUV/WAUVSim/install/setup.bash" ~/.bashrc; then
    echo "source ~/WAUV/WAUVSim/install/setup.bash" >> ~/.bashrc
fi

sudo apt-get install -y ros-humble-cv-bridge
sudo apt-get install -y ros-humble-py-trees

echo "INSTALL COMPLETE (づ ◕‿◕ )づ"
echo "Reboot for dialout changes to take affect"