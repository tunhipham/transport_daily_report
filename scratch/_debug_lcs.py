import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script'))
from domains.nso.fetch_nso_mail import _normalize, _lcs_length, _is_name_match

# Previous false matches to verify they're now rejected
cases = [
    ("Homyland Riverside - TDU", "Block C Diamond Riverside", "DMR"),
    ("Sunrise Citiview - Q7", "X1.013 Sunrise City North", "A141"),
    ("Phú Hoàng Anh - NBE", "A01-16 Hoàng Anh Thanh Bình", "A144"),
    ("1132 Nguyễn Duy Trinh (67 NDT) - TDU", "305 Nguyễn Duy Trinh", "NDT"),
    ("902 Nguyễn Duy Trinh - TDU", "305 Nguyễn Duy Trinh", "NDT"),
    # These SHOULD match:
    ("Masterise Center Point", "B6-D.TMDV.02 Masteri Center Point", "A181"),
    ("Golden Mansion - 119 Phổ Quang", "Golden Mansion 119 Phổ Quang", "A175"),
    ("Melody Residence-TPH", "H.38 Melody Residences Âu Cơ", "A186"),
    ("Saigon Mia - L1-08", "Saigon Mia - L1-08", "A184"),
    ("Tân Thới Nhất 17 - Q12", "Tân Thới Nhất 17", "A155"),
]
print(f"{'Mail Name':<40} | {'DSST Name':<40} | Code | LCS | Shorter | Ratio | Match")
print("-"*130)
for mail, dsst, code in cases:
    a = _normalize(mail)
    b = _normalize(dsst)
    lcs = _lcs_length(a, b)
    shorter = min(len(a), len(b))
    ratio = lcs / shorter if shorter else 0
    match = _is_name_match(a, b)
    status = "✅" if match else "❌"
    print(f"{a:<40} | {b:<40} | {code:<4} | {lcs:>3} | {shorter:>7} | {ratio:>5.0%} | {status}")
