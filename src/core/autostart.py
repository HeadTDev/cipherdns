import winreg
import sys
import os

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "CipherDNS"

def get_launch_command() -> str:
    """Returns the executable command line for Windows Auto-Start."""
    script_path = os.path.abspath(sys.argv[0])
    # If running with run.pyw or pythonw.exe
    executable = sys.executable
    if executable.lower().endswith("python.exe"):
        pythonw = executable[:-10] + "pythonw.exe"
        if os.path.exists(pythonw):
            executable = pythonw

    return f'"{executable}" "{script_path}" --autostart'

def is_autostart_enabled() -> bool:
    """Checks if CipherDNS is registered in Windows Startup Registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return False

def set_autostart(enable: bool) -> bool:
    """Enables or disables Windows Startup registration in HKCU Run key."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            cmd = get_launch_command()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Autostart] Error setting registry: {e}")
        return False
