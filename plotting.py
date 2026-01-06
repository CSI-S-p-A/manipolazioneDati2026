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
