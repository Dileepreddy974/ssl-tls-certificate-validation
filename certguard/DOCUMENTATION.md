# SSL/TLS Security Scanner - Project Documentation

## Project Overview

A comprehensive SSL/TLS certificate validation and security analysis tool that retrieves real-time certificate information from domains, validates certificate authenticity, checks TLS protocol support, and provides security scoring with trust assessment.

## Features

### Core Capabilities
- **Certificate Retrieval**: Fetches live SSL/TLS certificate data including subject, issuer, validity dates, serial number, SHA256 fingerprint, and subject alternative names (SANs)
- **Certificate Validation**: Validates certificate expiry status, hostname matching (including wildcard certificates)
- **TLS Protocol Detection**: Checks support for SSLv2, SSLv3, TLSv1.0, TLSv1.1, TLSv1.2, and TLSv1.3
- **Security Scoring**: Calculates security score (0-100) with letter grades (A+ to F)
- **Trust Assessment**: Provides detailed trust evaluation with explanations

### Technical Features
- Real-time certificate retrieval using Python's `ssl` and `socket` modules
- Binary certificate fingerprinting with SHA256 hashing
- Protocol version enumeration with graceful fallback handling
- CORS-enabled Flask API for frontend integration
- Responsive web UI with gradient design and real-time feedback

## Project Structure

```
certguard/
├── backend/
│   ├── app.py              # Flask API server
│   ├── validators.py       # Certificate retrieval & validation
│   ├── tls_checker.py      # TLS protocol detection
│   └── scoring.py          # Security scoring & trust analysis
├── index.html              # Frontend web interface
└── requirements.txt        # Python dependencies
```

## Technology Stack

### Backend
- **Flask 2.3.3**: Web framework for API server
- **Flask-CORS 4.0.0**: Cross-Origin Resource Sharing support
- **cryptography 41.0.7**: Cryptographic operations
- **certifi 2023.11.17**: CA certificate bundle
- **Python ssl module**: Built-in SSL/TLS functionality
- **Python socket module**: Network connectivity checks

### Frontend
- Vanilla HTML5, CSS3, JavaScript (no frameworks)
- Responsive grid layout with CSS Grid
- Async/await fetch API for backend communication
- Dynamic DOM manipulation

## Installation & Setup

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Installation Steps

1. Navigate to project directory:
```bash
cd certguard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the backend server:
```bash
cd backend
python app.py
```

4. Start the frontend server (separate terminal):
```bash
cd certguard
python -m http.server 8080
```

### Access Points
- **Backend API**: http://localhost:5000
- **Frontend UI**: http://localhost:8080

## API Reference

### POST /api/scan

Scans a domain for SSL/TLS certificate information and security assessment.

**Request Body:**
```json
{
  "hostname": "google.com"
}
```

**Response Schema:**
```json
{
  "hostname": "google.com",
  "certificate": {
    "subject": "*.google.com",
    "issuer": "Google Trust Services LLC",
    "serial_number": "ABC123...",
    "not_before": "Jan 15 00:00:00 2024 GMT",
    "not_after": "Apr 15 00:00:00 2024 GMT",
    "fingerprint_sha256": "a1b2c3d4e5f6...",
    "subject_alt_names": [["DNS", "*.google.com"], ["DNS", "google.com"]]
  },
  "validation": {
    "expiry": "valid",
    "hostname_match": true
  },
  "tls_versions": {
    "SSLv2": false,
    "SSLv3": false,
    "TLSv1": false,
    "TLSv1.1": false,
    "TLSv1.2": true,
    "TLSv1.3": true
  },
  "score": 95,
  "grade": "A+",
  "trusted": true,
  "explanation": {
    "status": "Trusted",
    "reason": "Valid SSL certificate and secure TLS protocols detected.",
    "brief": "The domain follows modern encryption standards.",
    "note": "Safe for normal internet use."
  }
}
```

**Error Response:**
```json
{
  "error": "Connection timeout"
}
```

## Module Documentation

### backend/app.py

Main Flask application that orchestrates the scanning workflow.

**Key Functions:**
- `scan_domain()`: Handles POST requests to `/api/scan` endpoint
- Integrates certificate retrieval, validation, TLS checking, and scoring
- Returns comprehensive JSON response with all analysis results

### backend/validators.py

Certificate retrieval and validation logic.

**Functions:**

#### get_certificate_info(hostname)
Retrieves SSL certificate details from a remote server.

**Parameters:**
- `hostname` (str): Domain name to scan (e.g., "google.com")

**Returns:**
```python
{
    "subject": str,           # Common Name from certificate subject
    "issuer": str,            # Common Name from certificate issuer
    "serial_number": str,     # Certificate serial number
    "not_before": str,        # Validity start date
    "not_after": str,         # Validity end date
    "fingerprint_sha256": str, # SHA256 hash of binary certificate
    "subject_alt_names": list  # Subject Alternative Names
}
```

**Process:**
1. Creates default SSL context
2. Establishes TCP connection on port 443
3. Wraps socket with SSL/TLS
4. Retrieves certificate in both text and binary formats
5. Computes SHA256 fingerprint
6. Extracts and structures certificate fields

#### validate_certificate(cert_info, hostname)
Validates certificate against security criteria.

**Parameters:**
- `cert_info` (dict): Certificate information from `get_certificate_info()`
- `hostname` (str): Expected hostname to match

**Returns:**
```python
{
    "expiry": str,           # "valid", "expiring soon", or "expired"
    "hostname_match": bool   # True if certificate matches hostname
}
```

**Validation Logic:**
- **Expiry Check**: 
  - Expired: < 0 days remaining
  - Expiring Soon: < 30 days remaining
  - Valid: ≥ 30 days remaining
- **Hostname Match**: Checks if hostname appears in certificate subject

### backend/tls_checker.py

TLS/SSL protocol version detection.

**Functions:**

#### try_protocol(hostname, protocol)
Tests if a specific TLS/SSL protocol is supported.

**Parameters:**
- `hostname` (str): Target domain
- `protocol`: SSL protocol constant (e.g., `ssl.PROTOCOL_TLSv1_2`)

**Returns:**
- `bool`: True if protocol is supported, False otherwise

#### check_tls_versions(hostname)
Checks support for multiple TLS/SSL protocol versions.

**Parameters:**
- `hostname` (str): Domain to test

**Returns:**
```python
{
    "SSLv2": bool,
    "SSLv3": bool,
    "TLSv1": bool,
    "TLSv1.1": bool,
    "TLSv1.2": bool,
    "TLSv1.3": bool
}
```

**Implementation Notes:**
- Uses `getattr()` with fallback for protocol constants that may not exist in all Python versions
- 3-second timeout per protocol test
- Gracefully handles unsupported protocols

### backend/scoring.py

Security scoring and trust evaluation.

**Functions:**

#### calculate_score(validation, tls_versions)
Calculates numerical security score and letter grade.

**Parameters:**
- `validation` (dict): Results from `validate_certificate()`
- `tls_versions` (dict): Results from `check_tls_versions()`

**Returns:**
- `score` (int): 0-100 security score
- `grade` (str): Letter grade ("A+", "B", "C", "D", "F")

**Scoring Algorithm:**
```
Base Score: 100 points

Deductions:
- Expired certificate: -50 points
- Expiring soon (< 30 days): -20 points
- Hostname mismatch: -30 points
- TLSv1.0 support (insecure): -10 points
- TLSv1.1 support (insecure): -10 points

Grade Scale:
- A+: ≥ 90 points
- B:  80-89 points
- C:  70-79 points
- D:  60-69 points
- F:  < 60 points
```

#### evaluate_trust(validation, tls_versions)
Determines overall trustworthiness with explanation.

**Parameters:**
- `validation` (dict): Certificate validation results
- `tls_versions` (dict): TLS protocol support

**Returns:**
- `trust` (bool): True if trusted, False otherwise
- `explanation` (dict): Detailed trust assessment

**Trust Criteria:**
- **Trusted** if ALL conditions met:
  - Certificate expiry status is "valid"
  - Hostname matches certificate subject
  - TLSv1.2 or higher is supported

**Explanation Structure:**
```python
{
    "status": "Trusted" | "Not Trusted",
    "reason": str,      # Primary reason for trust decision
    "brief": str,       # Brief summary
    "note": str         # User guidance
}
```

## Frontend Architecture

### index.html

Single-page application with embedded styles and scripts.

**Key Components:**

#### UI Sections
1. **Search Box**: Domain input field with scan button
2. **Loading Indicator**: Animated spinner during analysis
3. **Error Display**: Red alert box for error messages
4. **Results Panel**:
   - Grade badge with color coding
   - Security score display
   - Certificate information grid
   - Validation results
   - TLS protocol support list
   - Trust assessment box

#### Styling Features
- Purple gradient background (`#667eea` to `#764ba2`)
- Card-based layout with shadows
- Responsive grid system (auto-fit, minmax)
- Color-coded badges:
  - Green (`#4ade80`): Valid/Trusted/Supported
  - Yellow (`#fde047`): Warning/Expiring soon
  - Red (`#f87171`): Expired/Not trusted
  - Gray (`#e5e7eb`): Not supported

#### JavaScript Functions

##### scanDomain()
Initiates domain scanning process.

**Workflow:**
1. Validates user input
2. Clears previous results
3. Shows loading indicator
4. Sends POST request to backend API
5. Displays results or error message
6. Re-enables scan button

##### displayResults(data)
Renders scan results to the UI.

**Actions:**
- Updates grade badge with appropriate color class
- Populates certificate information grid
- Renders validation status badges
- Generates TLS protocol support indicators
- Displays trust assessment explanation

##### showError(message)
Displays error messages to the user.

## Security Considerations

### Certificate Validation
- Uses system's trusted CA bundle via `ssl.create_default_context()`
- Validates hostname against certificate subject
- Checks certificate expiry status
- Detects hostname mismatches

### Protocol Security
- Identifies deprecated protocols (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
- Rewards modern protocols (TLSv1.2, TLSv1.3)
- Penalizes insecure configurations in scoring

### Data Integrity
- Retrieves live certificate data (no caching/mocking)
- Computes SHA256 fingerprint for verification
- Preserves original certificate values without modification

## Usage Examples

### Example 1: Scanning a Secure Domain
```bash
curl -X POST http://localhost:5000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"hostname":"google.com"}'
```

**Expected Result:**
- Grade: A+
- Score: 95-100
- TLSv1.2/1.3: Supported
- Older protocols: Disabled
- Trusted: Yes

### Example 2: Scanning with Expiring Certificate
A domain with certificate expiring in 15 days:
- Deduction: -20 points
- Likely Grade: B or lower
- Status: "expiring soon"

### Example 3: Hostname Mismatch
Certificate issued to `example.com` but scanning `www.example.com`:
- Deduction: -30 points
- Hostname Match: False
- Impact on trust assessment

## Troubleshooting

### Common Issues

**1. Connection Timeout**
- **Cause**: Server unreachable on port 443
- **Solution**: Verify domain exists and accepts HTTPS connections

**2. Certificate Retrieval Failure**
- **Cause**: SSL handshake failure
- **Solution**: Check if domain supports SSL/TLS

**3. Blank Page on Frontend**
- **Cause**: Backend server not running
- **Solution**: Ensure `python app.py` is running on port 5000

**4. CORS Errors**
- **Cause**: Missing CORS headers
- **Solution**: Verify Flask-CORS is installed and initialized

### Debug Tips

Enable debug mode in Flask:
```python
app.run(port=5000, debug=True)
```

Check backend logs for detailed error messages.

## Future Enhancements

### Planned Features
- Certificate chain validation
- Certificate revocation checking (CRL, OCSP)
- Cipher suite analysis
- Security header detection (CSP, HSTS)
- Historical certificate tracking
- Batch domain scanning
- Export reports (PDF, JSON)
- Client certificate authentication support

### Performance Improvements
- Asynchronous certificate retrieval
- Connection pooling
- Result caching with TTL
- Parallel protocol testing

## License & Dependencies

All dependencies are open-source packages:
- Flask (BSD license)
- Flask-CORS (MIT license)
- cryptography (Apache 2.0 / BSD license)
- certifi (MPL 2.0 license)

## Contact & Support

For issues, questions, or contributions, please refer to the project repository.

---

**Document Version**: 1.0  
**Last Updated**: March 13, 2026  
**Project Status**: Production Ready
