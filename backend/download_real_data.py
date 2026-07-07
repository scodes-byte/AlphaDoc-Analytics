import os
import urllib.request

def download_file(url, destination):
    try:
        print(f"[Downloader] Fetching: {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(destination, 'wb') as out_file:
            out_file.write(response.read())
        print(f"[Downloader] Saved to: {destination} ({os.path.getsize(destination)} bytes)")
        return True
    except Exception as e:
        print(f"[Downloader] Error downloading {url}: {str(e)}")
        return False

if __name__ == "__main__":
    # Setup folders
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(project_root, "real_datasets")
    os.makedirs(target_dir, exist_ok=True)
    
    print("[Downloader] Setting up real financial datasets...")
    
    # Official Tesla Shareholder PDF URLs for FY 2024 quarters
    tesla_reports = {
        "TSLA_Q1_2024_Update.pdf": "https://digitalassets.tesla.com/tesla-contents/image/upload/IR/TSLA-Q1-2024-Update.pdf",
        "TSLA_Q2_2024_Update.pdf": "https://digitalassets.tesla.com/tesla-contents/image/upload/IR/TSLA-Q2-2024-Update.pdf",
        "TSLA_Q3_2024_Update.pdf": "https://digitalassets.tesla.com/tesla-contents/image/upload/IR/TSLA-Q3-2024-Update.pdf",
        "TSLA_Q4_2024_Update.pdf": "https://digitalassets.tesla.com/tesla-contents/image/upload/IR/TSLA-Q4-2024-Update.pdf"
    }
    
    success_count = 0
    for filename, url in tesla_reports.items():
        destination_path = os.path.join(target_dir, filename)
        if download_file(url, destination_path):
            success_count += 1
            
    print(f"\n[Downloader] Download completed: {success_count}/{len(tesla_reports)} reports acquired.")
    if success_count > 0:
        print(f"[Downloader] Files saved in: {target_dir}")
