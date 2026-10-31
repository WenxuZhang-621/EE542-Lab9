import pytest
from scripts.assetlinks import make_links

def test_valid_assetlinks():
    value = make_links('edu.ee542.studentdesk', [':'.join(['AB']*32)])
    assert value[0]['target']['package_name'] == 'edu.ee542.studentdesk'
    assert value[0]['relation'] == ['delegate_permission/common.handle_all_urls']

@pytest.mark.parametrize('package,fingerprints', [('missingdot', [':'.join(['AA']*32)]),
    ('edu.example', ['not-a-sha256']), ('edu.example', [])])
def test_invalid_handoff_rejected(package, fingerprints):
    with pytest.raises(ValueError): make_links(package, fingerprints)
