import subprocess
import json
import time

def _escape_ps(s: str) -> str:
    """Escapes single quotes for PowerShell single-quoted strings."""
    return s.replace("'", "''")

def apply_dns(adapter_name: str, profile: dict, strict_doh: bool = True) -> tuple[bool, str, list[str]]:
    """
    Applies DNS settings to a specified network interface alias.
    Ensures Windows Settings UI properly recognizes DoH Encryption status.
    Returns (success: bool, message: str, logs: list[str])
    """
    logs = []
    def log(msg: str):
        t = time.strftime("%H:%M:%S")
        logs.append(f"[{t}] {msg}")

    if not adapter_name or adapter_name == "No active adapter":
        log("Error: Invalid network adapter.")
        return False, "Network adapter not found!", logs

    safe_adapter = _escape_ps(adapter_name)
    prof_name = profile.get('name', 'Unknown')
    log(f"Starting: Applying DNS configuration to '{adapter_name}' -> Profile: '{prof_name}'")

    # --- CASE 1: RESET TO SYSTEM DEFAULT (CLEAR) ---
    if profile.get('id') == 'clear':
        log("Type: Restoring default (DHCP) DNS settings.")
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        $logList = @()
        try {{
            $logList += "Querying: Identifying current IP addresses..."
            $oldDns = Get-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -ErrorAction SilentlyContinue
            $oldIps = if ($oldDns) {{ $oldDns.ServerAddresses }} else {{ @() }}
            
            $logList += "Resetting: Reverting interface to DHCP..."
            Set-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -ResetServerAddresses -ErrorAction Stop
            
            $logList += "Cleanup: Removing registered system DoH templates..."
            foreach ($ip in $oldIps) {{
                if ($ip) {{
                    Remove-DnsClientDohServerAddress -ServerAddress $ip -ErrorAction SilentlyContinue
                    $null = netsh dns delete encryption server=$ip 2>&1
                }}
            }}
            
            $logList += "Registry: Cleaning Windows Settings DoH registry entries..."
            $adapter = Get-NetAdapter -InterfaceAlias '{safe_adapter}' -ErrorAction SilentlyContinue
            if ($adapter -and $adapter.InterfaceGuid) {{
                $guid = $adapter.InterfaceGuid
                $baseRegPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Dnscache\\InterfaceSpecificParameters\\$guid\\DohInterfaceSettings"
                Remove-Item -Path $baseRegPath -Recurse -Force -ErrorAction SilentlyContinue
            }}

            $logList += "Cache: Flushing Windows DNS cache..."
            Clear-DnsClientCache -ErrorAction SilentlyContinue
            
            return @{{ Success = $true; Message = "Default DNS settings successfully restored!"; Logs = $logList }} | ConvertTo-Json
        }} catch {{
            $logList += "ERROR: $_"
            return @{{ Success = $false; Message = $_.Exception.Message; Logs = $logList }} | ConvertTo-Json
        }}
        """
        return _execute_dns_powershell(ps_script, logs)

    # --- CASE 2: APPLY SPECIFIC DNS PROFILE ---
    ipv4_list = profile.get('ipv4', [])
    ipv6_list = profile.get('ipv6', [])
    template = profile.get('doh') or profile.get('doh_template') or ""
    
    ipv4_ps = ",".join([f"'{_escape_ps(ip)}'" for ip in ipv4_list]) if ipv4_list else ""
    ipv6_ps = ",".join([f"'{_escape_ps(ip)}'" for ip in ipv6_list]) if ipv6_list else ""
    
    all_ips = ipv4_list + ipv6_list
    all_ips_ps = ",".join([f"'{_escape_ps(ip)}'" for ip in all_ips]) if all_ips else ""
    
    udp_fallback = "no" if strict_doh else "yes"
    allow_fallback_bool = "$false" if strict_doh else "$true"
    doh_flag_val = 3 if strict_doh else 2  # 3 = Encrypted Only, 2 = Automatic (Preferred)
    strict_str = "Strict (Encrypted Only)" if strict_doh else "Flexible (Fallback Enabled)"

    log(f"DoH Mode: {strict_str}")
    if ipv4_list: log(f"IPv4 Addresses: {', '.join(ipv4_list)}")
    if ipv6_list: log(f"IPv6 Addresses: {', '.join(ipv6_list)}")
    if template: log(f"DoH URL: {template}")

    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    $logList = @()
    try {{
        $logList += "Step 1/5: Validating network adapter ('{safe_adapter}')..."
        $adapter = Get-NetAdapter -InterfaceAlias '{safe_adapter}' -ErrorAction Stop
        
        $v4Array = @({ipv4_ps})
        $v6Array = @({ipv6_ps})
        $allIps = @({all_ips_ps})
        
        if ($allIps.Count -eq 0) {{
            return @{{ Success = $false; Message = "The profile does not contain any IP addresses."; Logs = $logList }} | ConvertTo-Json
        }}

        # Enable global AutoDoH in Windows Dnscache
        try {{
            $paramPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Dnscache\\Parameters"
            if (-not (Test-Path $paramPath)) {{ New-Item -Path $paramPath -Force | Out-Null }}
            Set-ItemProperty -Path $paramPath -Name "EnableAutoDoh" -Value 2 -Type DWord -ErrorAction SilentlyContinue
        }} catch {{}}

        # STEP 2: System-wide DoH Template Registration
        if ('{_escape_ps(template)}' -ne '') {{
            $logList += "Step 2/5: Registering system-wide DoH encryption template..."
            foreach ($ip in $allIps) {{
                if (-not $ip) {{ continue }}
                
                Remove-DnsClientDohServerAddress -ServerAddress $ip -ErrorAction SilentlyContinue
                $null = netsh dns delete encryption server=$ip 2>&1
                
                try {{
                    Add-DnsClientDohServerAddress -ServerAddress $ip -DohTemplate '{_escape_ps(template)}' -AllowFallbackToUdp {allow_fallback_bool} -AutoUpgrade $true -ErrorAction Stop
                    $logList += "  -> PowerShell DoH registered for IP: $ip"
                }} catch {{
                    $null = netsh dns add encryption server=$ip dohtemplate='{_escape_ps(template)}' autoupgrade=yes udpfallback={udp_fallback} 2>&1
                    $logList += "  -> Netsh DoH registered for IP: $ip"
                }}
            }}
        }} else {{
            $logList += "Step 2/5: No DoH URL specified, applying standard DNS."
        }}

        # STEP 3: Assign DNS Server IP Addresses
        $logList += "Step 3/5: Assigning IP addresses to interface..."
        $setSuccess = $false
        $lastErr = ""
        
        try {{
            Set-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -ServerAddresses $allIps -ErrorAction Stop
            $setSuccess = $true
            $logList += "  -> IPv4 and IPv6 addresses successfully set."
        }} catch {{
            $lastErr = $_.Exception.Message
            $logList += "  -> Warning: Combined IP setting failed ($lastErr). Retrying with IPv4 only..."
        }}
        
        if (-not $setSuccess -and $v4Array.Count -gt 0) {{
            try {{
                Set-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -ServerAddresses $v4Array -ErrorAction Stop
                $setSuccess = $true
                $logList += "  -> IPv4 addresses successfully set."
            }} catch {{
                $lastErr = $_.Exception.Message
            }}
        }}
        
        if (-not $setSuccess) {{
            $logList += "ERROR: Failed to assign DNS server addresses: $lastErr"
            return @{{ Success = $false; Message = "DNS IP configuration error: $lastErr"; Logs = $logList }} | ConvertTo-Json
        }}

        # STEP 4: Windows 11 Settings UI DoH Configuration (Full Registry Sync)
        $logList += "Step 4/5: Synchronizing Windows Settings DoH UI status..."
        try {{
            $guid = $adapter.InterfaceGuid
            if ($guid) {{
                $dohFlag = {doh_flag_val}
                $baseRegPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Dnscache\\InterfaceSpecificParameters\\$guid\\DohInterfaceSettings"
                
                Remove-Item -Path $baseRegPath -Recurse -Force -ErrorAction SilentlyContinue
                New-Item -Path $baseRegPath -Force | Out-Null
                
                # Main interface DoH flags
                Set-ItemProperty -Path $baseRegPath -Name "DohFlags" -Value $dohFlag -Type DWord -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $baseRegPath -Name "DohAutoUpgrade" -Value 1 -Type DWord -ErrorAction SilentlyContinue

                if ('{_escape_ps(template)}' -ne '') {{
                    # IPv4 subkeys
                    foreach ($ip in $v4Array) {{
                        if (-not $ip) {{ continue }}
                        $regPath = "$baseRegPath\\Doh\\$ip"
                        New-Item -Path $regPath -Force | Out-Null
                        Set-ItemProperty -Path $regPath -Name "DohFlags" -Value $dohFlag -Type QWord -ErrorAction SilentlyContinue
                        Set-ItemProperty -Path $regPath -Name "DohTemplate" -Value '{_escape_ps(template)}' -Type String -ErrorAction SilentlyContinue
                        Set-ItemProperty -Path $regPath -Name "DohAutoUpgrade" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                    }}
                    
                    # IPv6 subkeys
                    foreach ($ip in $v6Array) {{
                        if (-not $ip) {{ continue }}
                        $regPath = "$baseRegPath\\Doh6\\$ip"
                        New-Item -Path $regPath -Force | Out-Null
                        Set-ItemProperty -Path $regPath -Name "DohFlags" -Value $dohFlag -Type QWord -ErrorAction SilentlyContinue
                        Set-ItemProperty -Path $regPath -Name "DohTemplate" -Value '{_escape_ps(template)}' -Type String -ErrorAction SilentlyContinue
                        Set-ItemProperty -Path $regPath -Name "DohAutoUpgrade" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                    }}
                }}
                $logList += "  -> Windows Settings DoH registry keys synchronized (DohFlags: $dohFlag)"
            }}
        }} catch {{
            $logList += "  -> Registry synchronization warning: $_"
        }}

        # Step 5: Flush DNS cache & Verification
        $logList += "Step 5/5: Flushing DNS cache and verifying..."
        Clear-DnsClientCache -ErrorAction SilentlyContinue

        # Verification check
        $verify = Get-DnsClientServerAddress -InterfaceAlias '{safe_adapter}' -AddressFamily IPv4 -ErrorAction SilentlyContinue
        $currentIps = if ($verify) {{ $verify.ServerAddresses }} else {{ @() }}
        
        $matched = $false
        foreach ($targetIp in $v4Array) {{
            if ($currentIps -contains $targetIp) {{
                $matched = $true
                break
            }}
        }}

        if ($matched -or $v4Array.Count -eq 0) {{
            $logList += "SUCCESS: New DNS server addresses are active on adapter."
            return @{{ Success = $true; Message = "DNS profile ('{_escape_ps(prof_name)}') successfully applied!"; Logs = $logList }} | ConvertTo-Json
        }} else {{
            $logList += "WARNING: IP configuration command completed, but post-verification query did not reflect new IPs yet."
            return @{{ Success = $false; Message = "IP update initiated, but adapter verification query did not confirm yet."; Logs = $logList }} | ConvertTo-Json
        }}

    }} catch {{
        $logList += "CRITICAL ERROR: $_"
        return @{{ Success = $false; Message = $_.Exception.Message; Logs = $logList }} | ConvertTo-Json
    }}
    """
    return _execute_dns_powershell(ps_script, logs)

def _execute_dns_powershell(ps_script: str, initial_logs: list[str]) -> tuple[bool, str, list[str]]:
    logs = list(initial_logs)
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        stdout = res.stdout.strip()
        if stdout:
            try:
                data = json.loads(stdout)
                if isinstance(data, dict):
                    ps_logs = data.get('Logs', [])
                    for pl in ps_logs:
                        t = time.strftime("%H:%M:%S")
                        logs.append(f"[{t}] {pl}")
                    return bool(data.get('Success', False)), str(data.get('Message', 'Unknown response')), logs
            except Exception:
                pass

        if res.returncode == 0:
            return True, "Successfully applied!", logs
        else:
            err = res.stderr.strip() or stdout or "Unknown PowerShell error."
            t = time.strftime("%H:%M:%S")
            logs.append(f"[{t}] Error: {err}")
            return False, f"Error: {err}", logs
    except Exception as e:
        t = time.strftime("%H:%M:%S")
        logs.append(f"[{t}] Exception: {str(e)}")
        return False, f"Execution error: {str(e)}", logs
