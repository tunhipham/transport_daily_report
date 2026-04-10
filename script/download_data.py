"""
download_data.py - Download KRC from Google Sheets and KH folders from Google Drive
Usage: python script/download_data.py [--date DD.MM.YYYY]

Auto-download:  KRC (Google Sheets) + KH MEAT/ĐÔNG/MÁT (gdown folder sync)
Manual:         KFM, transfer_*, yeu_cau_* (user places in data/)

If gdown hits rate limits, automatically falls back to direct download via requests.
"""
import os, sys, re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

KRC_EXPORT_URL = "https://docs.google.com/spreadsheets/d/1tWamqjpOI2j2MrYW3Ah6ptmT524CAlQvEP8fCkxfuII/export?format=xlsx"

# Google Drive subfolder URLs for KH data
KH_FOLDERS = [
    ("KH MEAT", "https://drive.google.com/drive/folders/1GIzH8nmCbLhWfpdmxFIn9cHTvQNbnwWr"),
    ("KH HÀNG ĐÔNG", "https://drive.google.com/drive/folders/1pQ8coYeV-K0dcHlkvXcJ8KngmH22xp1Z"),
    ("KH HÀNG MÁT", "https://drive.google.com/drive/folders/1c2zfgcXM8O9ezkOZYj0p4t_ihaJmb98f"),
]


def download_krc():
    """Download KRC from Google Sheets (public, no auth needed)."""
    import requests
    dest = os.path.join(DATA, "THỜI GIAN GIAO HÀNG KRC.xlsx")
    print(f"  Downloading -> {os.path.basename(dest)}")
    r = requests.get(KRC_EXPORT_URL, allow_redirects=True, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)
    print(f"  OK ({len(r.content) / 1024 / 1024:.2f} MB)")


def _direct_download(file_id, dest_path):
    """Download a single file from Google Drive using requests (fallback)."""
    import requests
    url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    r = requests.get(url, allow_redirects=True, timeout=60)
    if r.status_code == 200 and len(r.content) > 500:
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True, len(r.content)
    return False, 0


def download_kh_folders():
    """Download KH folders from Google Drive using gdown + requests fallback.
    
    Strategy:
    1. Use gdown to list folder contents and download what it can
    2. Track files that gdown fails on (rate limit errors)
    3. Retry failed files using direct requests download
    """
    import gdown
    import io
    from contextlib import redirect_stdout, redirect_stderr

    for folder_name, folder_url in KH_FOLDERS:
        dest = os.path.join(DATA, folder_name)
        os.makedirs(dest, exist_ok=True)
        print(f"\n  [{folder_name}]")

        # Capture gdown output to detect failed file IDs
        captured = io.StringIO()
        failed_files = []  # list of (file_id, filename)
        processing_files = []  # all (file_id, filename) seen

        class TeeWriter:
            """Write to both console and capture buffer."""
            def __init__(self, original, capture):
                self.original = original
                self.capture = capture
            def write(self, s):
                self.original.write(s)
                self.capture.write(s)
            def flush(self):
                self.original.flush()

        tee_out = TeeWriter(sys.stdout, captured)
        tee_err = TeeWriter(sys.stderr, captured)

        try:
            with redirect_stdout(tee_out), redirect_stderr(tee_err):
                gdown.download_folder(
                    url=folder_url,
                    output=dest,
                    quiet=False,
                    remaining_ok=True,
                )
        except Exception as e:
            print(f"  gdown error: {e}")

        # Parse captured output for file IDs and detect failures
        output_text = captured.getvalue()
        
        # Find all "Processing file <id> <filename>" lines
        for m in re.finditer(r'Processing file (\S+) (.+)', output_text):
            file_id = m.group(1)
            filename = m.group(2).strip()
            processing_files.append((file_id, filename))

        # Check which files actually exist on disk
        for file_id, filename in processing_files:
            filepath = os.path.join(dest, filename)
            if not os.path.exists(filepath) or os.path.getsize(filepath) < 500:
                failed_files.append((file_id, filename))

        # Retry failed files with direct download
        if failed_files:
            print(f"  ⚠️ gdown missed {len(failed_files)} file(s), retrying with direct download...")
            for file_id, filename in failed_files:
                filepath = os.path.join(dest, filename)
                print(f"    ↳ {filename}...", end=" ")
                ok, size = _direct_download(file_id, filepath)
                if ok:
                    print(f"OK ({size/1024:.0f} KB)")
                else:
                    print(f"FAILED")
        else:
            print(f"  OK")


def main():
    print("=" * 45)
    print("  DOWNLOAD DATA")
    print("=" * 45)

    # Step 1: Download KRC
    print("\n[1] Downloading KRC...")
    try:
        download_krc()
    except Exception as e:
        print(f"  ERROR: {e}")

    # Step 2: Download KH folders
    print("\n[2] Downloading KH folders from Google Drive...")
    try:
        download_kh_folders()
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n" + "=" * 45)
    print("  DONE!")
    print("=" * 45)


if __name__ == "__main__":
    main()
