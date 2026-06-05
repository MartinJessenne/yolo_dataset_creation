# test_isaac.py
# Verification script to ensure SimulationApp binds to the GPU headless

from isaacsim import SimulationApp

# Initialize headless simulation app
simulation_app = SimulationApp({"headless": True})

print("SimulationApp initialized successfully!")

# Clean up and close
simulation_app.close()
