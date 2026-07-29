import socket

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
    
    # Set default socket timeout for fast test execution
    socket.setdefaulttimeout(1.5)
    
    for domain in test_domains:
        try:
            ip = socket.gethostbyname(domain)
            # If the IP resolves to local loopback or 0.0.0.0, it is blocked by DNS
            if ip in ["0.0.0.0", "127.0.0.1", "::1"]:
                blocked_count += 1
        except socket.gaierror:
            # NXDOMAIN (Name or service not known) - blocked by DNS
            blocked_count += 1
        except Exception:
            pass
            
    is_active = blocked_count >= (total - 1)  # At least most blocked
    return is_active, blocked_count, total
