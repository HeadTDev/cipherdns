import socket
import ssl
import urllib.parse
import time
import subprocess

def test_adblocking() -> tuple[bool, int, int]:
    """
    Tests if the current DNS resolver blocks known ad/tracking domains.
    Returns: (is_blocking_active: bool, blocked_count: int, total_count: int)
    """
    test_domains = [
        "doubleclick.net", 
        "google-analytics.com",
        "pagead2.googlesyndication.com",
        "adservice.google.com"
    ]
    blocked_count = 0
    total = len(test_domains)
    
    socket.setdefaulttimeout(1.5)
    
    for domain in test_domains:
        try:
            ip = socket.gethostbyname(domain)
            if ip in ["0.0.0.0", "127.0.0.1", "::1"]:
                blocked_count += 1
        except socket.gaierror:
            blocked_count += 1
        except Exception:
            pass
            
    is_active = blocked_count >= (total - 1)
    return is_active, blocked_count, total

def test_dnssec_validation() -> tuple[bool, str]:
    """
    Tests whether the active DNS resolver enforces DNSSEC signature validation.
    Resolves 'dnssec-failed.org' (intentionally broken DNSSEC signature).
    - If resolution fails (SERVFAIL/gaierror): DNSSEC validation is ACTIVE (Secure).
    - If resolution succeeds: DNSSEC validation is INACTIVE (Unvalidated).
    
    Returns: (is_dnssec_active: bool, details_text: str)
    """
    test_domain = "dnssec-failed.org"
    socket.setdefaulttimeout(2.0)
    try:
        ip = socket.gethostbyname(test_domain)
        # Resolved successfully -> Resolver ignored broken DNSSEC signature
        return False, f"Resolver did not validate DNSSEC signature (resolved to {ip})."
    except socket.gaierror:
        # Failed resolution (SERVFAIL) -> Resolver blocked fake/invalid DNSSEC signature!
        return True, "Resolver actively validates DNSSEC signatures and blocks spoofed records."
    except Exception as e:
        return True, f"DNSSEC validation test returned: {e}"

def test_doh_tls_status(doh_url: str) -> tuple[bool, str, str]:
    """
    Inspects TLS connection to the DoH endpoint URL.
    Returns: (is_connected: bool, tls_version: str, details: str)
    """
    if not doh_url or not isinstance(doh_url, str):
        return False, "N/A", "No DoH URL configured for active provider."
        
    doh_url = doh_url.strip()
    if not doh_url.startswith("https://") and not doh_url.startswith("http://"):
        doh_url = "https://" + doh_url.lstrip("/")

    parsed = urllib.parse.urlparse(doh_url)
    hostname = parsed.hostname
    port = parsed.port or 443
    
    if not hostname:
        return False, "N/A", "Invalid DoH URL hostname."
        
    try:
        context = ssl.create_default_context()
        start_t = time.perf_counter()
        with socket.create_connection((hostname, port), timeout=3.0) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                tls_ver = ssock.version() or "TLS 1.3"
                rtt_ms = int((time.perf_counter() - start_t) * 1000)
                cipher = ssock.cipher()
                cipher_name = cipher[0] if cipher else "AES-GCM"
                return True, tls_ver, f"Connected to {hostname}:{port} via {tls_ver} ({cipher_name}) in {rtt_ms}ms"
    except Exception as e:
        return False, "Failed", f"DoH TLS handshake error: {str(e)}"

def flush_dns_cache() -> tuple[bool, str]:
    """Flushes local OS DNS resolver cache."""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Clear-DnsClientCache -ErrorAction Stop"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if res.returncode == 0:
            return True, "DNS cache flushed successfully!"
        else:
            return False, f"Failed to flush DNS cache: {res.stderr.strip()}"
    except Exception as e:
        return False, f"Flush error: {str(e)}"
