"""A/B handoff: validate public package/fingerprints and write or check Asset Links."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import httpx
from shared.config import ROOT

def make_links(package, fingerprints):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', package):
        raise ValueError('Provide the exact Android applicationId, such as edu.ee542.studentdesk')
    values = []
    for value in fingerprints:
        value = value.strip().upper()
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){31}[0-9A-F]{2}', value):
            raise ValueError('Expected a SHA-256 certificate fingerprint (32 colon-separated bytes)')
        values.append(value)
    if not values: raise ValueError('At least one signing fingerprint is required')
    return [{'relation':['delegate_permission/common.handle_all_urls'],
             'target':{'namespace':'android_app', 'package_name':package, 'sha256_cert_fingerprints':values}}]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', required=True)
    p.add_argument('--fingerprint', action='append', required=True)
    p.add_argument('--output', type=Path, default=ROOT/'webapp/frontend/.well-known/assetlinks.json')
    p.add_argument('--check-url', help='Check the deployed HTTPS origin instead of writing a file')
    args = p.parse_args()
    expected = make_links(args.package, args.fingerprint)
    if args.check_url:
        url = urlparse(args.check_url)
        if url.scheme != 'https' or not url.hostname or url.path not in ('', '/') or url.query or url.fragment:
            raise ValueError('Provide an HTTPS origin, without a path/query/fragment')
        response = httpx.get(args.check_url.rstrip('/')+'/.well-known/assetlinks.json', timeout=15, follow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200 or 'application/json' not in response.headers.get('content-type',''):
            raise ValueError('Asset Links must return HTTP 200 JSON directly, without redirects')
        entries = response.json()
        target = expected[0]['target']
        match = any('delegate_permission/common.handle_all_urls' in row.get('relation', [])
                    and row.get('target',{}).get('namespace') == 'android_app'
                    and row.get('target',{}).get('package_name') == target['package_name']
                    and set(target['sha256_cert_fingerprints']) <= set(row.get('target',{}).get('sha256_cert_fingerprints',[]))
                    for row in entries)
        if not match: raise ValueError('Deployed package or fingerprints do not match B\'s build')
        print('HTTPS Asset Links match the provided package and signing fingerprint.')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(expected, indent=2)+'\n', encoding='utf-8')
        print('Wrote Asset Links. Give B the same HTTPS origin and verify the signed APK together.')

if __name__ == '__main__': main()
