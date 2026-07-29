import subprocess
import re
import ctypes

def is_admin():
    """Ellenőrzi, hogy a script rendszergazdai jogosultsággal fut-e."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_network_adapters():
    """Lekérdezi az aktív hálózati kártyákat natív netsh segítségével (villámgyors)."""
    try:
        result = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        adapters = []
        lines = result.stdout.split('\n')
        for line in lines:
            line = line.strip()
            if ("Connected" in line or "Csatlakoztatva" in line) and not line.startswith("Admin"):
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 4:
                    adapters.append(parts[-1])
        if not adapters:
            for line in lines:
                line = line.strip()
                if ("Enabled" in line or "Engedélyezve" in line) and not line.startswith("Admin"):
                    parts = re.split(r'\s{2,}', line)
                    if len(parts) >= 4:
                        adapters.append(parts[-1])
        return adapters
    except Exception as e:
        print(f"Hiba a hálózati kártyák lekérdezésekor: {e}")
        return []

def get_active_profile(adapter_name, profiles):
    """Lekérdezi az aktív IPv4 DNS címeket és megkeresi a hozzá tartozó profilt (natív netsh)."""
    try:
        result = subprocess.run(["netsh", "interface", "ipv4", "show", "dnsservers", f'name={adapter_name}'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', result.stdout)
        if not ips:
            return 'clear'
        first_ip = ips[0]
        for p in profiles:
            if p['ipv4'] and first_ip in p['ipv4']:
                return p['id']
        return None
    except Exception:
        return None

def ping_profile(profile):
    if not profile.get('ipv4'):
        return None
    ip = profile['ipv4'][0]
    try:
        result = subprocess.run(["ping", "-n", "1", "-w", "1500", ip], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        match = re.search(r'(?:time|idő)[=<]\s*(\d+)\s*ms', result.stdout, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    except Exception:
        return None

def get_current_network_name():
    ps_command = "Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -eq 'Internet' } | Select-Object -ExpandProperty Name -First 1"
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        name = result.stdout.strip()
        if name:
            return name
    except Exception:
        pass
    return None
