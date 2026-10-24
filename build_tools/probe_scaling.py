import ctypes
import tkinter as tk

import customtkinter as ctk

ctypes.windll.shcore.SetProcessDpiAwareness(2)

root = ctk.CTk()
root.withdraw()

tracker = ctk.ScalingTracker
print("tk scaling:", float(root.tk.call("tk", "scaling")))
print("window_scaling:", getattr(tracker, "window_dpi_scaling_dict", {}))

# 创建一个控件看实际尺寸
btn = ctk.CTkButton(root, text="x", width=100, height=34)
btn.pack()
root.update_idletasks()
print("button asked:", btn.winfo_reqwidth(), btn.winfo_reqheight())
print("screen:", root.winfo_screenwidth(), root.winfo_screenheight())
print("GetDpiForSystem:", ctypes.windll.user32.GetDpiForSystem())
root.destroy()
