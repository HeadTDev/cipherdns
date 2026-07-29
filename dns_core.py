import subprocess
import ctypes
import json
import os
import re

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

def apply_dns(adapter_name, profile, strict_doh=True):
    """Beállítja a kiválasztott DNS-t a megadott hálózati kártyára."""
    
    if profile['id'] == 'clear':
        ps_script = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses
        Clear-DnsClientCache
        """
    else:
        ipv4_str = ",".join([f"'{ip}'" for ip in profile['ipv4']])
        ipv6_str = ",".join([f"'{ip}'" for ip in profile['ipv6']])
        template = profile.get('doh') or profile.get('doh_template')
        udpfallback = "no" if strict_doh else "yes"

        ps_script = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        
        foreach ($ip in @({ipv4_str})) {{
            $res = netsh dns add encryption server=$ip dohtemplate="{template}" autoupgrade=yes udpfallback={udpfallback} 2>&1
            if ($res -match "already exists" -or $res -match "már létezik") {{
                netsh dns set encryption server=$ip dohtemplate="{template}" autoupgrade=yes udpfallback={udpfallback} | Out-Null
            }}
        }}
        
        foreach ($ip in @({ipv6_str})) {{
            $res = netsh dns add encryption server=$ip dohtemplate="{template}" autoupgrade=yes udpfallback={udpfallback} 2>&1
            if ($res -match "already exists" -or $res -match "már létezik") {{
                netsh dns set encryption server=$ip dohtemplate="{template}" autoupgrade=yes udpfallback={udpfallback} | Out-Null
            }}
        }}

        Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses @({ipv4_str})
        Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -Family IPv6 -ServerAddresses @({ipv6_str})
        Clear-DnsClientCache
        """

    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0:
            return True, "Sikeres beállítás!"
        else:
            return False, f"Hiba: {result.stderr}"
    except Exception as e:
        return False, str(e)

def load_profiles():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_path = os.path.join(current_dir, 'profiles.json')
    with open(profiles_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_settings():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(current_dir, 'settings.json')
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"auto_switch": False, "network_memory": {}}

def save_settings(settings):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(current_dir, 'settings.json')
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass

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
