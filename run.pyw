import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.network import is_admin
from src.ui.app import run_as_admin, CipherDNSApp

if __name__ == "__main__":
    if not is_admin():
        run_as_admin()
        
    app = CipherDNSApp()
    app.mainloop()
