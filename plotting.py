import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

def animation_car_points(x1, y1, x2, y2, x3, y3, x4, y4):
    """
    Animates 4 points with equal aspect ratio and a tracking camera.

    Inputs:
    x1, y1 ... x4, y4: Numpy arrays of the same length representing coordinates over time.
    """

    # 1. Setup the Figure and Axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # CRITICAL: Ensure angles are accurate
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.5)

    # 2. Determine static Y-limits
    # Since Y variation is small, we calculate the max range required for Y
    # across the whole animation and fix it. This prevents vertical jitter.
    all_y = np.concatenate([y1, y2, y3, y4])
    y_min, y_max = np.min(all_y), np.max(all_y)
    y_pad = 5  # Add some visual breathing room
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    # 3. Initialize the Plot Objects
    # We create empty plot objects that we will update in the loop
    # Points A, B, C are Blue. Point D is Red.
    (point_A,) = ax.plot([], [], "bo", markersize=4, label="A")
    (point_B,) = ax.plot([], [], "bo", markersize=4, label="B")
    (point_C,) = ax.plot([], [], "bo", markersize=4, label="C")
    (point_D,) = ax.plot([], [], "ro", markersize=4, label="D")  # Red

    # Initialize Text Labels
    txt_A = ax.text(0, 0, "A", fontsize=12)
    txt_B = ax.text(0, 0, "B", fontsize=12)
    txt_C = ax.text(0, 0, "C", fontsize=12)
    txt_D = ax.text(0, 0, "D", fontsize=12)

    # 4. Define the View Width
    # How "wide" (in data units) should the camera be?
    # Since aspect is equal, this depends on figure width, but we set a reasonable default.
    view_width = 40

    def init():
        """Initializes the background of the animation."""
        point_A.set_data([], [])
        point_B.set_data([], [])
        point_C.set_data([], [])
        point_D.set_data([], [])
        return point_A, point_B, point_C, point_D, txt_A, txt_B, txt_C, txt_D

    def update(frame):
        """Update function called for every frame."""

        # --- Update Positions ---
        point_A.set_data([x1[frame]], [y1[frame]])
        point_B.set_data([x2[frame]], [y2[frame]])
        point_C.set_data([x3[frame]], [y3[frame]])
        point_D.set_data([x4[frame]], [y4[frame]])

        # --- Update Labels (slightly offset from dot) ---
        offset = 0.5
        txt_A.set_position((x1[frame] + offset, y1[frame] + offset))
        txt_B.set_position((x2[frame] + offset, y2[frame] + offset))
        txt_C.set_position((x3[frame] + offset, y3[frame] + offset))
        txt_D.set_position((x4[frame] + offset, y4[frame] + offset))

        # --- Update Camera (The "Video Game" Logic) ---
        # Calculate the center X of the current cluster of points
        current_xs = [x1[frame], x2[frame], x3[frame], x4[frame]]
        center_x = np.mean(current_xs)

        # Move the X-axis limits to center on the points
        ax.set_xlim(center_x - (view_width / 2), center_x + (view_width / 2))

        return point_A, point_B, point_C, point_D, txt_A, txt_B, txt_C, txt_D

    # 5. Create the Animation Object
    # frames=len(x1) ensures we run through the whole time series
    ani = FuncAnimation(
        fig, update, frames=len(x1), init_func=init, blit=False, interval=1
    )  # interval is ms between frames

    plt.show()
    return ani
