#!/usr/bin/env python3
"""
Turn on a "flashlight" by making the screen fullscreen bright white.
Point the camera at the screen to use it as a light source.
Close with: click anywhere, or press Escape, or press Q.
"""
import sys

try:
    import tkinter as tk
except ImportError:
    print("tkinter is required (usually included with Python).", file=sys.stderr)
    sys.exit(1)


def main():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.overrideredirect(True)
    root.configure(bg="white")
    root.lift()

    def close(_=None):
        root.destroy()

    root.bind("<Escape>", close)
    root.bind("q", close)
    root.bind("<Button-1>", close)
    root.bind("<Button-3>", close)

    label = tk.Label(
        root,
        text="Flashlight ON · Click or press Esc/Q to turn off",
        font=("Helvetica", 24),
        bg="white",
        fg="gray",
    )
    label.place(relx=0.5, rely=0.5, anchor="center")

    root.mainloop()
    print("Flashlight off.")


if __name__ == "__main__":
    main()
