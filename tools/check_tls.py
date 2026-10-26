#!/usr/bin/env python3
"""
check_tls.py — will the Nokia 3210 accept HTTPS from this server?

Simulates the phone's two hard limits instead of guessing:

  1. Trust: the firmware ships exactly ONE root certificate. This script
     extracts it from EXEC_USER_IMAGE.bin and uses it as the only anchor.
  2. Ciphers: mbedTLS 2.6 in this build offers no ECDHE at all, so the
     handshake is restricted to the static-RSA suites the phone actually has.

A pass here means the phone will accept the certificate. A pass in a desktop
browser means nothing — desktops trust hundreds of roots the phone does not.

    python check_tls.py nokia.smartbinary.org
    python check_tls.py nokia.smartbinary.org --image path/to/EXEC_USER_IMAGE.bin
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import socket
import ssl
import sys
import tempfile
import textwrap

DEFAULT_IMAGE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'גיבוים', '_DownloadFiles64E0_A641E99_0', 'EXEC_USER_IMAGE.bin')

# Published fingerprint of "Go Daddy Root Certificate Authority - G2".
KNOWN_ROOT_SHA256 = '45140B3247EB9CC8C5B4F0D7B53091F73292089E6E5A63E2749DD3ACA9198EDA'

# OpenSSL names for the static-RSA suites present in the phone's table.
PHONE_CIPHERS = 'AES128-SHA:AES256-SHA:AES128-SHA256:AES128-GCM-SHA256:AES256-GCM-SHA384'


def root_from_firmware(path: str) -> bytes:
    with open(path, 'rb') as fh:
        blob = fh.read()
    m = re.search(rb'-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----', blob, re.S)
    if not m:
        raise SystemExit(f'no certificate found inside {path}')
    return base64.b64decode(re.sub(rb'\s', b'', m.group(1)))


def der_to_pem(der: bytes) -> str:
    b64 = base64.b64encode(der).decode()
    return ('-----BEGIN CERTIFICATE-----\n'
            + '\n'.join(textwrap.wrap(b64, 64))
            + '\n-----END CERTIFICATE-----\n')


def probe(host: str, port: int, anchor_file: str, restrict_ciphers: bool):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    ctx.load_verify_locations(cafile=anchor_file)
    if restrict_ciphers:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2   # the phone has no TLS 1.3
        try:
            ctx.set_ciphers('@SECLEVEL=0:' + PHONE_CIPHERS)
        except ssl.SSLError as ex:
            return None, f'this python cannot offer the phone ciphers: {ex}'
    try:
        with socket.create_connection((host, port), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                return tls, f'{tls.version()} / {tls.cipher()[0]}'
    except ssl.SSLCertVerificationError as ex:
        return None, f'certificate rejected: {ex.verify_message or ex}'
    except ssl.SSLError as ex:
        return None, f'handshake failed: {str(ex)[:140]}'
    except OSError as ex:
        return None, f'cannot connect: {ex}'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('host')
    ap.add_argument('--port', type=int, default=443)
    ap.add_argument('--image', default=DEFAULT_IMAGE,
                    help='path to EXEC_USER_IMAGE.bin (default: the backup in this project)')
    args = ap.parse_args()

    print(f'target: {args.host}:{args.port}\n')

    der = root_from_firmware(args.image)
    fp = hashlib.sha256(der).hexdigest().upper()
    print(f'trust anchor taken from firmware, sha256 {fp}')
    if fp == KNOWN_ROOT_SHA256:
        print('  = Go Daddy Root Certificate Authority - G2 (verified by fingerprint)')
    else:
        print('  ! this is NOT the expected GoDaddy root — check the image path')
    print(f'  the phone trusts this certificate and nothing else\n')

    anchor = os.path.join(tempfile.gettempdir(), 'nokia_root_' + fp[:8] + '.pem')
    with open(anchor, 'w') as fh:
        fh.write(der_to_pem(der))

    # Step 1 — trust, without constraining the handshake.
    tls, detail = probe(args.host, args.port, anchor, restrict_ciphers=False)
    trust_ok = tls is not None
    if tls:
        tls.close()
    print(f'[{"PASS" if trust_ok else "FAIL"}] certificate chains to the root the phone has')
    print(f'       {detail}\n')

    # Step 2 — trust *and* the phone's cipher limits together.
    tls, detail = probe(args.host, args.port, anchor, restrict_ciphers=True)
    full_ok = tls is not None
    if tls:
        tls.close()
    print(f'[{"PASS" if full_ok else "FAIL"}] handshake succeeds using only ciphers the phone has')
    print(f'       {detail}\n')

    if full_ok:
        print('RESULT: the Nokia will accept https on this host.')
        return 0

    print('RESULT: the Nokia will NOT accept https on this host.')
    if not trust_ok:
        print('  - The certificate does not chain to GoDaddy Root G2.')
        print('    Install a GoDaddy-issued certificate and paste the full CA bundle,')
        print('    so the cross-signed intermediate is served with it.')
    else:
        print('  - Trust is fine; the server refuses every cipher the phone can do.')
        print('    It needs one of: ' + PHONE_CIPHERS.replace(':', ', '))
        print('    On shared hosting this is usually not adjustable — ask support,')
        print('    or keep serving the phone over plain http.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
