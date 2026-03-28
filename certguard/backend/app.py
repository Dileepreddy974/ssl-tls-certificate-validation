import re
import concurrent.futures
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from validators import get_certificate_info, validate_certificate, validate_chain_of_trust, check_revocation_status
from tls_checker import check_tls_versions
from scoring import calculate_score, evaluate_trust
from security_checks import check_cipher_strength, check_certificate_transparency

app = Flask(__name__)
CORS(app)


def normalize_hostname(raw_hostname):
    """
    Accept loose input (URL/path/port) and normalize to a bare hostname.
    """
    hostname = (raw_hostname or "").strip().lower()
    hostname = re.sub(r"^https?://", "", hostname)
    hostname = hostname.split("/")[0].split("?")[0].split("#")[0]
    hostname = hostname.split(":")[0]
    return hostname

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.route("/api/scan", methods=["POST"])
@limiter.limit("5 per minute")
def scan_domain():

    data = request.get_json() or {}
    hostname = normalize_hostname(data.get("hostname", ""))

    # Basic input sanitization
    if not hostname or not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", hostname):
        return jsonify({"error": "Invalid hostname format."}), 400

    try:
        # Parallel execution of independent checks for faster response
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks in parallel
            cert_future = executor.submit(get_certificate_info, hostname)
            tls_future = executor.submit(check_tls_versions, hostname)
            cipher_future = executor.submit(check_cipher_strength, hostname)
            
            # Wait for certificate info first (needed for validation)
            cert_info = cert_future.result(timeout=10)
            
            # Now submit dependent tasks
            validation_future = executor.submit(validate_certificate, cert_info, hostname)
            revocation_future = executor.submit(check_revocation_status, hostname, cert_info)
            
            # Collect all results
            validation = validation_future.result(timeout=5)
            tls_versions = tls_future.result(timeout=5)
            cipher_result = cipher_future.result(timeout=5)
            revocation_result = revocation_future.result(timeout=10)
            
            chain_future = executor.submit(validate_chain_of_trust, hostname, cert_info["pem"])
            ct_future = executor.submit(check_certificate_transparency, hostname, cert_info["pem"])
            
            chain_valid, chain_issuer, chain_message = chain_future.result(timeout=5)
            ct_result = ct_future.result(timeout=5)
            ct_compliant = ct_result.get("compliant", True)

        # Removed dummy assignments as they are now securely verified
        
        cipher_strength = cipher_result.get("overall_strength", "unknown")

        # Calculate score with enhanced parameters
        score, grade = calculate_score(
            validation, 
            tls_versions,
            chain_valid=chain_valid,
            cipher_strength=cipher_strength
        )

        # Evaluate trust with enhanced parameters
        trust, explanation = evaluate_trust(
            validation,
            tls_versions,
            chain_valid=chain_valid,
            cipher_strength=cipher_strength,
            ct_compliant=ct_compliant
        )

        result = {
            "hostname": hostname,
            "certificate": cert_info,
            "validation": validation,
            "tls_versions": tls_versions,
            "score": score,
            "grade": grade,
            "trusted": trust,
            "explanation": explanation,
            "security_checks": {
                "cipher_strength": cipher_result,
                "chain_validation": {
                    "valid": chain_valid,
                    "message": chain_message
                },
                "revocation": revocation_result
            }
        }

        return jsonify(result)

    except concurrent.futures.TimeoutError:
        return jsonify({"error": "Request timed out. The server may be slow or unreachable."}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Disable debug mode for better performance
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
