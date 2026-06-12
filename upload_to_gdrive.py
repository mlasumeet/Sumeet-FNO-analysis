"""
upload_to_gdrive.py - Uploads generated PDF to Google Drive
Requires GDRIVE_CREDENTIALS (base64 encoded JSON) and GDRIVE_FOLDER_ID environment variables
"""
import os
import json
import base64
import glob
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_gdrive_service():
    """Create Google Drive API service from credentials."""
    creds_b64 = os.environ.get("GDRIVE_CREDENTIALS")
    if not creds_b64:
        print("ERROR: GDRIVE_CREDENTIALS environment variable not set")
        return None
    
    try:
        # Decode base64 credentials
        creds_json = base64.b64decode(creds_b64).decode('utf-8')
        creds_dict = json.loads(creds_json)
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build service
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"ERROR: Failed to create Google Drive service: {e}")
        return None

def upload_pdf_to_gdrive(pdf_path, folder_id):
    """Upload PDF to Google Drive folder."""
    service = get_gdrive_service()
    if not service:
        return False
    
    try:
        filename = os.path.basename(pdf_path)
        print(f"Uploading {filename} to Google Drive...")
        
        # Prepare file metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Upload file
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        web_link = file.get('webViewLink')
        
        print(f"✅ Successfully uploaded to Google Drive!")
        print(f"   File ID: {file_id}")
        print(f"   Link: {web_link}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to upload PDF: {e}")
        return False

def main():
    """Find and upload the latest PDF."""
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        print("ERROR: GDRIVE_FOLDER_ID environment variable not set")
        return False
    
    # Find the latest PDF
    output_dir = os.path.join(os.path.dirname(__file__), "Output")
    pdf_files = glob.glob(os.path.join(output_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"WARNING: No PDF files found in {output_dir}")
        return False
    
    # Get the most recent PDF
    latest_pdf = max(pdf_files, key=os.path.getctime)
    print(f"Found PDF: {latest_pdf}")
    
    # Upload to Google Drive
    return upload_pdf_to_gdrive(latest_pdf, folder_id)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
