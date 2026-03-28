import ssl
import socket


def try_protocol(hostname, version_enum):

    try:
        context = ssl.create_default_context()
        context.minimum_version = version_enum
        context.maximum_version = version_enum

        # Reduced timeout for faster response - timeout only on socket, not SSL wrap
        with socket.create_connection((hostname, 443), timeout=2) as sock:
            with context.wrap_socket(sock, server_hostname=hostname):
                return True
    except Exception:
        return False


def check_tls_versions(hostname):

    versions = {}

    protocols = {
        "TLSv1": getattr(ssl.TLSVersion, 'TLSv1', None),
        "TLSv1.1": getattr(ssl.TLSVersion, 'TLSv1_1', None),
        "TLSv1.2": getattr(ssl.TLSVersion, 'TLSv1_2', None),
        "TLSv1.3": getattr(ssl.TLSVersion, 'TLSv1_3', None),
        "SSLv2": getattr(ssl.TLSVersion, 'SSLv2', None),
        "SSLv3": getattr(ssl.TLSVersion, 'SSLv3', None)
    }

    for name, proto_enum in protocols.items():
        if proto_enum is not None:
            versions[name] = try_protocol(hostname, proto_enum)
        else:
            versions[name] = False

    return versions
