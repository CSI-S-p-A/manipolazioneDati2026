import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation


def animation_3_points(x1, y1, x2, y2, x3, y3, x4, y4):
    fig, ax = plt.subplots()
    scat1 = ax.scatter([], [], c="blue")  # First 3 points
    scat2 = ax.scatter([], [], c="red")  # Fourth point in red

    # Create text labels
    labels = ["A", "B", "C", "D"]
    texts = [ax.text(0, 0, label, fontsize=12, ha="right") for label in labels]

    # Auto-calculate limits based on your actual data
    all_x = np.concatenate([x1, x2, x3, x4])
    all_y = np.concatenate([y1, y2, y3, y4])

    x_margin = (all_x.max() - all_x.min()) * 0.1
    y_margin = (all_y.max() - all_y.min()) * 0.1

    ax.set_xlim(all_x.min() - x_margin, all_x.max() + x_margin)
    ax.set_ylim(all_y.min() - y_margin, all_y.max() + y_margin)

    print(f"X range: {all_x.min()} to {all_x.max()}")
    print(f"Y range: {all_y.min()} to {all_y.max()}")

    def update(frame):
        # First 3 points (blue)
        xs = np.array([x1[frame], x2[frame], x3[frame]])
        ys = np.array([y1[frame], y2[frame], y3[frame]])
        scat1.set_offsets(np.c_[xs, ys])

        # Fourth point (red)
        scat2.set_offsets([[x4[frame], y4[frame]]])

        # Update text positions
        texts[0].set_position((x1[frame], y1[frame]))
        texts[1].set_position((x2[frame], y2[frame]))
        texts[2].set_position((x3[frame], y3[frame]))
        texts[3].set_position((x4[frame], y4[frame]))

        return (scat1, scat2, *texts)

    ani = FuncAnimation(fig, update, frames=len(x1), interval=10, blit=True)
    plt.show()


def animate_car_frame(x1, y1, x2, y2, x3, y3, x4, y4):
    import matplotlib.animation as animation

    """
    Animate 4 points representing a car frame over time.

    Parameters:
    x1, y1 : numpy arrays of x and y coordinates over time for point a
    x2, y2 : numpy arrays of x and y coordinates over time for point b
    x3, y3 : numpy arrays of x and y coordinates over time for point c
    x4, y4 : numpy arrays of x and y coordinates over time for point d
    """
    # Get number of frames
    n_frames = len(x1)

    # Get axis limits based on all coordinates
    all_x = np.concatenate([x1, x2, x3, x4])
    all_y = np.concatenate([y1, y2, y3, y4])
    x_min, x_max = all_x.min() - 1, all_x.max() + 1
    y_min, y_max = all_y.min() - 1, all_y.max() + 1

    # Calculate appropriate figure size to maintain aspect ratio
    x_range = x_max - x_min
    y_range = y_max - y_min
    aspect_ratio = x_range / y_range

    # Set figure width based on aspect ratio (height fixed at 6)
    fig_height = 6
    fig_width = max(fig_height * aspect_ratio, 10)  # At least 10 inches wide

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Car Frame Points Animation")

    # Initialize plot elements
    (scatter_abc,) = ax.plot([], [], "bo", markersize=12, label="Points a, b, c")
    (scatter_d,) = ax.plot([], [], "ro", markersize=12, label="Point d")

    # Create text annotations for labels
    text_a = ax.text(0, 0, "a", fontsize=12, ha="center", va="bottom")
    text_b = ax.text(0, 0, "b", fontsize=12, ha="center", va="bottom")
    text_c = ax.text(0, 0, "c", fontsize=12, ha="center", va="bottom")
    text_d = ax.text(0, 0, "d", fontsize=12, ha="center", va="bottom")

    # Add legend
    ax.legend()

    # Animation function
    def init():
        scatter_abc.set_data([], [])
        scatter_d.set_data([], [])
        text_a.set_position((0, 0))
        text_b.set_position((0, 0))
        text_c.set_position((0, 0))
        text_d.set_position((0, 0))
        return scatter_abc, scatter_d, text_a, text_b, text_c, text_d

    def animate(frame):
        # Get current positions for all points
        frame_idx = frame % n_frames

        # Plot points a, b, c (first 3 points)
        x_abc = [x1[frame_idx], x2[frame_idx], x3[frame_idx]]
        y_abc = [y1[frame_idx], y2[frame_idx], y3[frame_idx]]
        scatter_abc.set_data(x_abc, y_abc)

        # Plot point d with different color
        scatter_d.set_data([x4[frame_idx]], [y4[frame_idx]])

        # Update labels positions
        text_a.set_position((x1[frame_idx], y1[frame_idx] + 0.15))
        text_b.set_position((x2[frame_idx], y2[frame_idx] + 0.15))
        text_c.set_position((x3[frame_idx], y3[frame_idx] + 0.15))
        text_d.set_position((x4[frame_idx], y4[frame_idx] + 0.15))

        return scatter_abc, scatter_d, text_a, text_b, text_c, text_d

    # Create animation
    anim = animation.FuncAnimation(
        fig,
        animate,
        init_func=init,
        frames=n_frames,
        interval=50,
        blit=True,
        repeat=True,
    )

    plt.tight_layout()
    plt.show()

    return anim
