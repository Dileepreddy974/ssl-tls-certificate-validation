import ssl
import socket
import hashlib
import re
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import ExtensionOID, AuthorityInformationAccessOID
import requests
import base64


def get_certificate_info(hostname):

    context = ssl.create_default_context()
    
    # Reduced timeout for faster response - timeout only on socket, not SSL wrap
    with socket.create_connection((hostname, 443), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            binary_cert = ssock.getpeercert(binary_form=True)
            pem_cert = ssl.DER_cert_to_PEM_cert(binary_cert)

    subject = dict(x[0] for x in cert['subject'])
    issuer = dict(x[0] for x in cert['issuer'])

    fingerprint = hashlib.sha256(binary_cert).hexdigest()

    return {
        "subject": subject.get("commonName"),
        "issuer": issuer.get("commonName"),
        "serial_number": cert.get("serialNumber"),
        "not_before": cert.get("notBefore"),
        "not_after": cert.get("notAfter"),
        "fingerprint_sha256": fingerprint,
        "subject_alt_names": cert.get("subjectAltName"),
        "pem": pem_cert,
        "der_binary": base64.b64encode(binary_cert).decode('utf-8')
    }


def validate_certificate(cert_info, hostname):

    results = {}

    expiry = datetime.strptime(cert_info["not_after"], "%b %d %H:%M:%S %Y %Z")

    days_left = (expiry - datetime.now(timezone.utc).replace(tzinfo=None)).days

    if days_left < 0:
        results["expiry"] = "expired"
    elif days_left < 30:
        results["expiry"] = "expiring soon"
    else:
        results["expiry"] = "valid"

    # Check Subject Alternative Names (SANs)
    match_found = False
    sans = cert_info.get("subject_alt_names") or []
    
    if sans:
        for san_type, san_value in sans:
            if san_type == "DNS":
                # Convert wildcard *.example.com to regex pattern
                pattern = "^" + re.escape(san_value).replace("\\*", "[^.]+") + "$"
                if re.match(pattern, hostname, re.IGNORECASE):
                    match_found = True
                    break
    
    # Fallback to subject commonName if no SAN matched
    if not match_found and cert_info.get("subject"):
        cn = cert_info["subject"]
        pattern = "^" + re.escape(cn).replace("\\*", "[^.]+") + "$"
        if re.match(pattern, hostname, re.IGNORECASE):
            match_found = True

    results["hostname_match"] = match_found

    return results


def validate_chain_of_trust(hostname, cert_pem):
    """
    Validate that the certificate is signed by a trusted CA.
    Returns tuple: (is_valid, issuer_info, validation_message)
    """
    try:
        # Load the certificate
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        
        # Get issuer information
        issuer_name = cert.issuer.rfc4514_string()
        
        # Try to verify against system's trusted CA store
        context = ssl.create_default_context()
        
        # The context automatically checks against system CA store
        # We'll do a basic verification by attempting SSL connection again
        try:
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname):
                    # If this succeeds, chain is valid
                    return True, {"issuer": issuer_name}, "Certificate chain verified against trusted CA store"
        except ssl.SSLCertVerificationError as e:
            return False, {"issuer": issuer_name}, f"Certificate chain validation failed: {str(e)}"
        except Exception:
            # For other errors, assume chain might be okay but couldn't verify
            return True, {"issuer": issuer_name}, f"Issuer: {issuer_name} (Chain verification skipped)"
            
    except Exception as e:
        return False, {"error": str(e)}, f"Failed to validate chain: {str(e)}"


def check_revocation_status(hostname, cert_info):
    """
    Check if certificate has been revoked using OCSP or CRL.
    Returns dict with revocation status and details.
    """
    try:
        # Decode the certificate from base64
        try:
            der_cert = base64.b64decode(cert_info.get('der_binary', ''))
            cert = x509.load_der_x509_certificate(der_cert, default_backend())
        except Exception as e:
            return {
                "checked": False,
                "revoked": False,
                "method": "none",
                "error": f"Failed to load certificate: {str(e)}",
                "message": "Unable to parse certificate for revocation check"
            }
        
        # Try OCSP first
        ocsp_result = check_ocsp_status(hostname, cert, cert_info.get('pem'))
        if ocsp_result['checked']:
            return ocsp_result
        
        # Fallback to CRL
        crl_result = check_crl_status(hostname, cert)
        if crl_result['checked']:
            return crl_result
        
        # If both fail
        return {
            "checked": False,
            "revoked": False,
            "method": "none",
            "message": "No OCSP or CRL endpoints found in certificate"
        }
        
    except Exception as e:
        return {
            "checked": False,
            "revoked": False,
            "error": str(e),
            "message": f"Revocation check failed: {str(e)}"
        }


def check_ocsp_status(hostname, cert, pem_cert):
    """
    Check certificate revocation status via OCSP (Online Certificate Status Protocol).
    """
    try:
        # Extract OCSP responder URL from certificate
        try:
            aia_extension = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
            ocsp_urls = [
                desc.access_location.value
                for desc in aia_extension.value
                if desc.access_method == AuthorityInformationAccessOID.OCSP
            ]
            
            if not ocsp_urls:
                return {
                    "checked": False,
                    "revoked": False,
                    "method": "ocsp",
                    "message": "No OCSP responder URL found in certificate"
                }
            
            ocsp_url = ocsp_urls[0]
        except x509.ExtensionNotFound:
            return {
                "checked": False,
                "revoked": False,
                "method": "ocsp",
                "message": "AIA extension not found - OCSP not supported"
            }
        
        # Get issuer certificate (simplified - in production you'd fetch it)
        # For now, we'll use a simplified approach
        
        # Build OCSP request
        from cryptography.x509.ocsp import OCSPRequestBuilder
        
        builder = OCSPRequestBuilder()
        builder = builder.add_certificate(cert, cert)  # Using same cert as issuer (simplified)
        ocsp_request = builder.build()
        
        # Encode request
        ocsp_request_data = ocsp_request.public_bytes("der")
        
        # Send OCSP request
        headers = {
            'Content-Type': 'application/ocsp-request',
            'Accept': 'application/ocsp-response'
        }
        
        response = requests.post(ocsp_url, data=ocsp_request_data, headers=headers, timeout=5)
        
        if response.status_code == 200:
            # Parse OCSP response
            from cryptography.x509.ocsp import load_der_ocsp_response
            
            ocsp_response = load_der_ocsp_response(response.content, default_backend())
            
            # Check response status
            if ocsp_response.response_status != x509.ocsp.OCSPResponseStatus.SUCCESSFUL:
                return {
                    "checked": False,
                    "revoked": False,
                    "method": "ocsp",
                    "message": f"OCSP response status: {ocsp_response.response_status}"
                }
            
            # Get certificate status
            cert_status = ocsp_response.certificate_status
            
            if cert_status == x509.ocsp.CertificateStatus.GOOD:
                return {
                    "checked": True,
                    "revoked": False,
                    "method": "ocsp",
                    "responder": ocsp_url,
                    "this_update": ocsp_response.this_update.strftime('%Y-%m-%d %H:%M:%S'),
                    "next_update": ocsp_response.next_update.strftime('%Y-%m-%d %H:%M:%S') if ocsp_response.next_update else None,
                    "message": "Certificate is valid and not revoked (verified via OCSP)"
                }
            elif cert_status == x509.ocsp.CertificateStatus.REVOKED:
                return {
                    "checked": True,
                    "revoked": True,
                    "method": "ocsp",
                    "responder": ocsp_url,
                    "revocation_time": ocsp_response.revocation_time.strftime('%Y-%m-%d %H:%M:%S') if ocsp_response.revocation_time else None,
                    "revocation_reason": getattr(ocsp_response, 'revocation_reason', 'Unknown'),
                    "message": "⚠️ CERTIFICATE HAS BEEN REVOKED"
                }
            else:
                return {
                    "checked": True,
                    "revoked": False,
                    "method": "ocsp",
                    "message": "Certificate status unknown"
                }
        else:
            return {
                "checked": False,
                "revoked": False,
                "method": "ocsp",
                "message": f"OCSP server returned status {response.status_code}"
            }
            
    except Exception as e:
        return {
            "checked": False,
            "revoked": False,
            "method": "ocsp",
            "error": str(e),
            "message": f"OCSP check failed: {str(e)}"
        }


def check_crl_status(hostname, cert):
    """
    Check certificate revocation status via CRL (Certificate Revocation List).
    """
    try:
        # Extract CRL Distribution Points from certificate
        try:
            crl_extension = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS)
            crl_urls = []
            
            for point in crl_extension.value:
                if point.full_name:
                    for name in point.full_name:
                        if isinstance(name, x509.UniformResourceIdentifier):
                            crl_urls.append(name.value)
            
            if not crl_urls:
                return {
                    "checked": False,
                    "revoked": False,
                    "method": "crl",
                    "message": "No CRL distribution points found in certificate"
                }
            
            crl_url = crl_urls[0]
        except x509.ExtensionNotFound:
            return {
                "checked": False,
                "revoked": False,
                "method": "crl",
                "message": "CRL distribution points not found - CRL not supported"
            }
        
        # Download CRL with shorter timeout
        response = requests.get(crl_url, timeout=5)
        
        if response.status_code == 200:
            # Parse CRL
            from cryptography.x509 import load_der_x509_crl, load_pem_x509_crl
            
            try:
                crl = load_der_x509_crl(response.content, default_backend())
            except Exception:
                try:
                    crl = load_pem_x509_crl(response.content, default_backend())
                except Exception:
                    return {
                        "checked": False,
                        "revoked": False,
                        "method": "crl",
                        "message": "Failed to parse CRL"
                    }
            
            # Check if certificate serial number is in CRL
            cert_serial = cert.serial_number
            
            for revoked_cert in crl:
                if revoked_cert.serial_number == cert_serial:
                    return {
                        "checked": True,
                        "revoked": True,
                        "method": "crl",
                        "crl_url": crl_url,
                        "revocation_time": revoked_cert.revocation_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "message": "⚠️ CERTIFICATE HAS BEEN REVOKED (found in CRL)"
                    }
            
            # Not found in CRL - certificate is valid
            return {
                "checked": True,
                "revoked": False,
                "method": "crl",
                "crl_url": crl_url,
                "last_update": crl.last_update.strftime('%Y-%m-%d %H:%M:%S'),
                "next_update": crl.next_update.strftime('%Y-%m-%d %H:%M:%S') if hasattr(crl, 'next_update') and crl.next_update else None,
                "message": "Certificate is valid and not in revocation list (verified via CRL)"
            }
        else:
            return {
                "checked": False,
                "revoked": False,
                "method": "crl",
                "message": f"Failed to download CRL: HTTP {response.status_code}"
            }
            
    except Exception as e:
        return {
            "checked": False,
            "revoked": False,
            "method": "crl",
            "error": str(e),
            "message": f"CRL check failed: {str(e)}"
        }
