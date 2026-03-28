def calculate_score(validation, tls_versions, chain_valid=True, cipher_strength="strong"):

    score = 100

    if validation["expiry"] == "expired":
        score -= 50

    if validation["expiry"] == "expiring soon":
        score -= 20

    if not validation["hostname_match"]:
        score -= 30

    if tls_versions.get("TLSv1"):
        score -= 10

    if tls_versions.get("TLSv1.1"):
        score -= 10

    # Chain of trust validation
    if not chain_valid:
        score -= 40

    # Cipher strength check
    if cipher_strength == "weak":
        score -= 20

    if score >= 90:
        grade = "A+"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return score, grade


def evaluate_trust(validation, tls_versions, chain_valid=True, cipher_strength="strong", ct_compliant=True):

    # Base requirements for trust
    base_requirements = (
        validation["expiry"] == "valid" and 
        validation["hostname_match"] and 
        tls_versions.get("TLSv1.2")
    )
    
    # Enhanced security checks
    critical_issues = []
    warnings = []
    
    # Critical issues that immediately affect trust
    if not chain_valid:
        critical_issues.append("Certificate chain validation failed")
    
    if cipher_strength == "weak":
        critical_issues.append("Weak cipher suites detected")
    
    # Non-critical warnings
    if not ct_compliant:
        warnings.append("Certificate Transparency not verified")
    
    if tls_versions.get("TLSv1") or tls_versions.get("TLSv1.1"):
        warnings.append("Deprecated TLS versions supported")
    
    # Determine trust status
    if base_requirements and chain_valid and cipher_strength != "weak":
        trust = True
        
        explanation = {
            "status": "Trusted",
            "reason": "Valid SSL certificate, secure TLS protocols, and trusted certificate chain detected.",
            "brief": "The domain follows modern encryption standards.",
            "note": "Safe for normal internet use.",
            "warnings": warnings if warnings else None,
            "security_features": {
                "strong_ciphers": cipher_strength == "strong",
                "ct_logged": ct_compliant
            }
        }
        
    else:
        trust = False
        
        reasons = []
        if validation["expiry"] != "valid":
            reasons.append(f"Certificate {validation['expiry']}")
        if not validation["hostname_match"]:
            reasons.append("Hostname mismatch")
        if not tls_versions.get("TLSv1.2"):
            reasons.append("Missing TLS 1.2 support")
        if critical_issues:
            reasons.extend(critical_issues)
        
        explanation = {
            "status": "Not Trusted",
            "reason": "; ".join(reasons) + ".",
            "brief": "The domain may expose users to security risks.",
            "note": "Avoid transmitting sensitive information.",
            "critical_issues": critical_issues if critical_issues else None,
            "warnings": warnings if warnings else None
        }

    return trust, explanation
