import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script'))
from domains.nso.fetch_nso_mail import _normalize, _lcs_length, _is_name_match

cases = [
    ("Sunrise Citiview Q7", "X1.013 Sunrise City North", "A141"),
    ("Phú Hoàng Anh NBE", "A01-16 Hoàng Anh Thanh Bình", "A144"),
    ("1132 Nguyễn Duy Trinh (67 NDT) TDU", "305 Nguyễn Duy Trinh", "NDT"),
]
for mail, dsst, code in cases:
    a = _normalize(mail)
    b = _normalize(dsst)
    lcs = _lcs_length(a, b)
    shorter = min(len(a), len(b))
    ratio = lcs / shorter if shorter else 0
    match = _is_name_match(a, b)
    print(f"  '{a}' vs '{b}'")
    print(f"    LCS={lcs}, shorter={shorter}, ratio={ratio:.0%}, match={match}")
    print()
