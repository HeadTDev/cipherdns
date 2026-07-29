import subprocess

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
