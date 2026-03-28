import ssl
import socket
import requests


def check_hsts_header(hostname):
    """
    Check if the server sends HSTS (HTTP Strict Transport Security) header.
    Returns dict with hsts_enabled status and max-age value.
    """
    try:
        # Make HTTPS request to check headers
        response = requests.get(f"https://{hostname}", timeout=5, verify=True)
        
        headers = response.headers
        hsts_header = headers.get('Strict-Transport-Security')
        
        if hsts_header:
            # Parse max-age value
            parts = hsts_header.split(';')
            max_age = None
            include_subdomains = False
            preload = False
            
            for part in parts:
                part = part.strip()
                if part.startswith('max-age='):
                    try:
                        max_age = int(part.split('=')[1])
                    except ValueError:
                        pass
                elif part.strip() == 'includeSubDomains':
                    include_subdomains = True
                elif part.strip() == 'preload':
                    preload = True
            
            return {
                "enabled": True,
                "header": hsts_header,
                "max_age": max_age,
                "include_subdomains": include_subdomains,
                "preload": preload,
                "message": f"HSTS enabled with max-age={max_age} seconds"
            }
        else:
            return {
                "enabled": False,
                "header": None,
                "message": "HSTS header not present"
            }
            
    except requests.exceptions.SSLError as e:
        return {
            "enabled": False,
            "error": str(e),
            "message": f"SSL error checking HSTS: {str(e)}"
        }
    except Exception as e:
        return {
            "enabled": False,
            "error": str(e),
            "message": f"Failed to check HSTS: {str(e)}"
        }


def check_cipher_strength(hostname):
    """
    Check the cipher suites supported by the server and evaluate their strength.
    Returns list of ciphers with strength assessment.
    """
    weak_ciphers = [
        'RC4', 'DES', 'MD5', '3DES', 'EXPORT', 'NULL', 'ANON',
        'CBC', 'SHA1'  # These are considered weak in certain contexts
    ]
    
    result = {
        "ciphers_tested": [],
        "weak_found": [],
        "strong_found": [],
        "overall_strength": "unknown"
    }
    
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Get the cipher used for this connection
                cipher = ssock.cipher()
                
                if cipher:
                    cipher_name = cipher[0]
                    cipher_version = cipher[1]
                    
                    result["current_cipher"] = {
                        "name": cipher_name,
                        "version": cipher_version,
                        "bits": cipher[2] if len(cipher) > 2 else None
                    }
                    
                    # Check for weak components
                    is_weak = False
                    weakness_reasons = []
                    
                    for weak in weak_ciphers:
                        if weak.upper() in cipher_name.upper():
                            is_weak = True
                            weakness_reasons.append(weak)
                            result["weak_found"].append({
                                "cipher": weak,
                                "found_in": cipher_name
                            })
                    
                    # Check key length
                    key_bits = cipher[2] if len(cipher) > 2 else 0
                    if key_bits and key_bits < 128:
                        is_weak = True
                        weakness_reasons.append(f"Weak key length: {key_bits} bits")
                    
                    if is_weak:
                        result["overall_strength"] = "weak"
                        result["weakness_reasons"] = weakness_reasons
                    else:
                        result["overall_strength"] = "strong"
                        result["strong_found"].append(cipher_name)
                        
    except Exception as e:
        result["error"] = str(e)
        result["overall_strength"] = "unknown"
    
    return result


def check_key_strength(cert_info):
    """
    Analyze the public key strength from certificate information.
    Returns dict with key_type, key_size, and strength assessment.
    """
    try:
        # Note: This would ideally use the actual certificate object
        # For now, we'll return a structure that can be enhanced later
        result = {
            "checked": False,
            "message": "Key strength analysis requires full certificate object"
        }
        
        # In a complete implementation, you would:
        # 1. Access cert.public_key() from the x509 certificate object
        # 2. Check key_type (RSA, ECDSA, etc.)
        # 3. Verify key_size meets modern standards:
        #    - RSA: minimum 2048 bits (4096 recommended)
        #    - ECDSA: minimum 256 bits (384+ recommended)
        
        return result
        
    except Exception as e:
        return {
            "checked": False,
            "error": str(e),
            "message": f"Failed to analyze key strength: {str(e)}"
        }


def check_certificate_transparency(hostname, cert_pem):
    """
    Check if certificate is logged in Certificate Transparency logs.
    Returns dict with CT compliance status.
    """
    try:
        # Load certificate to check for CT extensions
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        
        # Look for CT Precertificate SCTs extension (OID: 1.3.6.1.4.1.11129.2.4.2)
        ct_extension_oid = x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.4.2")
        
        try:
            cert.extensions.get_extension_for_oid(ct_extension_oid)
            return {
                "logged": True,
                "compliant": True,
                "message": "Certificate Transparency logs found"
            }
        except x509.ExtensionNotFound:
            return {
                "logged": False,
                "compliant": False,
                "message": "No Certificate Transparency logs found (may not be required for all CAs)"
            }
            
    except Exception as e:
        return {
            "logged": False,
            "error": str(e),
            "message": f"Failed to check CT logs: {str(e)}"
        }
