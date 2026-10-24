import ctypes
import tkinter as tk

user32 = ctypes.windll.user32
try:
    shcore = ctypes.windll.shcore
except Exception:
    shcore = None


def probe(label):
    root = tk.Tk()
    root.withdraw()
    scaling = root.tk.call("tk", "scaling")
    info = {
        "label": label,
        "tk_scaling": round(float(scaling), 3),
        "screen": (root.winfo_screenwidth(), root.winfo_screenheight()),
        "GetDpiForSystem": user32.GetDpiForSystem() if hasattr(user32, "GetDpiForSystem") else "n/a",
    }
    try:
        info["ScaleFactorForDevice"] = shcore.GetScaleFactorForDevice(0) if shcore else "n/a"
    except Exception as exc:
        info["ScaleFactorForDevice"] = str(exc)
    root.destroy()
    print(info)


print("=== 未设置 DPI awareness ===")
probe("none")

print("\n=== 设置 PerMonitorAware 后 ===")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()
probe("per-monitor")

try:
    import customtkinter as ctk

    print("\ncustomtkinter:", ctk.__version__)
    print("ScalingTracker:", getattr(ctk, "ScalingTracker", None))
except Exception as exc:
    print("ctk import fail", exc)
