import subprocess
import json
import ctypes
import socket
import time
import re

def is_admin() -> bool:
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def _run_powershell_json(script: str) -> dict | list | None:
    """Executes a PowerShell script expecting JSON output."""
    full_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        {script}
    }} catch {{
        Write-Output "null"
    }}
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", full_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        stdout = res.stdout.strip()
        if stdout and stdout != "null":
            return json.loads(stdout)
    except Exception as e:
        print(f"[Network] PS JSON execution error: {e}")
    return None

def get_network_adapters() -> list[str]:
    """
    Queries active connected network adapters using language-independent CIM/Get-NetAdapter.
    Returns a list of adapter interface aliases (e.g. ['Wi-Fi', 'Ethernet']).
    """
    ps_cmd = """
    $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.HardwareInterface -eq $true } | Select-Object -ExpandProperty Name
    if (-not $adapters) {
        $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -ExpandProperty Name
    }
    if ($adapters -is [string]) { $adapters = @($adapters) }
    $adapters | ConvertTo-Json
    """
    result = _run_powershell_json(ps_cmd)
    if isinstance(result, list):
        return [str(a) for a in result if a]
    elif isinstance(result, str) and result:
        return [result]
    return []

def get_active_profile(adapter_name: str, profiles: list[dict]) -> str | None:
    """
    Queries active DNS server addresses on the specified adapter and matches them to a profile.
    Returns profile ID or None.
    """
    if not adapter_name or adapter_name == "No active adapter":
        return None

    # Escape single quotes in adapter name for PowerShell safety
    safe_adapter = adapter_name.replace("'", "''")
    ps_cmd = f"""
    $dns = Get-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -ErrorAction SilentlyContinue
    if ($dns) {{
        $ips = $dns.ServerAddresses
        if ($ips -is [string]) {{ $ips = @($ips) }}
        $ips | ConvertTo-Json
    }} else {{
        "[]" | ConvertTo-Json
    }}
    """
    ips = _run_powershell_json(ps_cmd)
    if not ips or (isinstance(ips, list) and len(ips) == 0):
        return 'clear'

    if isinstance(ips, str):
        ips = [ips]

    # Convert all retrieved IPs to clean string list
    active_ips = set(str(ip).strip() for ip in ips if ip)
    if not active_ips:
        return 'clear'

    # Check profiles matching
    for p in profiles:
        p_ips = set(p.get('ipv4', []) + p.get('ipv6', []))
        if p_ips and active_ips.intersection(p_ips):
            return p['id']

    return None

def ping_profile(profile: dict) -> int | None:
    """
    Measures latency to the profile's primary DNS server IP via native socket TCP port 53 connection.
    Language-independent, fast, and tests actual DNS port responsiveness.
    """
    ipv4_list = profile.get('ipv4', [])
    if not ipv4_list:
        return None
    
    target_ip = ipv4_list[0]
    try:
        start_time = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.2)
        conn_res = sock.connect_ex((target_ip, 53))
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        sock.close()
        
        # If TCP port 53 is open (0), return latency
        if conn_res == 0:
            return elapsed_ms
    except Exception:
        pass

    # Fallback to ICMP ping using ctypes IcmpSendEcho if socket fails
    try:
        return _win32_icmp_ping(target_ip)
    except Exception:
        return None

def _win32_icmp_ping(ip_str: str) -> int | None:
    """Win32 native ICMP Echo for fallback ping without launching ping.exe subprocess."""
    try:
        icmp = ctypes.windll.iphlpapi
        handle = icmp.IcmpCreateFile()
        if handle == -1 or handle == 0:
            return None
        
        # Convert IP string to uint32
        inet_addr = socket.inet_aton(ip_str)
        ip_num = ctypes.c_ulong.from_buffer_copy(inet_addr).value

        send_data = b"CipherDNS"
        reply_buffer_size = 100
        reply_buffer = ctypes.create_string_buffer(reply_buffer_size)

        ret = icmp.IcmpSendEcho(
            handle,
            ip_num,
            send_data,
            len(send_data),
            None,
            reply_buffer,
            reply_buffer_size,
            1200 # timeout ms
        )
        icmp.IcmpCloseHandle(handle)

        if ret > 0:
            # Round trip time is at offset 8 in IP_OPTION_INFORMATION / ICMP_ECHO_REPLY struct
            rtt = int.from_bytes(reply_buffer[8:12], byteorder='little')
            return rtt
    except Exception:
        pass
    return None

def get_current_network_name() -> str | None:
    """
    Retrieves active network connection profile name (Wi-Fi or Ethernet SSID/Network name).
    Language-independent using CIM / Get-NetConnectionProfile.
    """
    ps_cmd = """
    $net = Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -eq 'Internet' -or $_.IPv6Connectivity -eq 'Internet' } | Select-Object -ExpandProperty Name -First 1
    if ($net) { $net | ConvertTo-Json } else { "null" | ConvertTo-Json }
    """
    result = _run_powershell_json(ps_cmd)
    if isinstance(result, str) and result != "null":
        return result
    return None
