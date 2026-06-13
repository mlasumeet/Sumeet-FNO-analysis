"""
upload_to_gdrive.py - Uploads generated PDF to Google Drive with detailed debug logging
Requires GDRIVE_CREDENTIALS (base64 encoded JSON) and GDRIVE_FOLDER_ID environment variables
"""
import os
import json
import base64
import binascii
import glob
import traceback
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def safe_print(msg):
    try:
        print(msg)
    except Exception:
        pass


def load_credentials_from_secret(secret_value):
    """Load service-account credentials from raw JSON or one-line base64 JSON."""
    cleaned = secret_value.strip()

    if cleaned.startswith("{"):
        return json.loads(cleaned)

    try:
        decoded = base64.b64decode(cleaned, validate=True)
    except binascii.Error as exc:
        raise ValueError(
            "GDRIVE_CREDENTIALS is not valid base64. Use a one-line base64 "
            "encoding of the Google service-account JSON key, or paste the raw "
            "JSON key directly."
        ) from exc

    try:
        creds_json = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "GDRIVE_CREDENTIALS decoded from base64, but the result is not "
            "UTF-8 JSON. Recreate the secret from the original service-account "
            "JSON key file."
        ) from exc

    return json.loads(creds_json)


def get_gdrive_service():
    """Create Google Drive API service from credentials and provide debugging info."""
    creds_b64 = os.environ.get("GDRIVE_CREDENTIALS")
    if not creds_b64:
        safe_print("ERROR: GDRIVE_CREDENTIALS environment variable not set")
        return None, None

    try:
        creds_dict = load_credentials_from_secret(creds_b64)

        # Don't print private key material — only safe metadata
        client_email = creds_dict.get('client_email')
        project_id = creds_dict.get('project_id')
        safe_print(f"Debug: service account client_email={client_email}")
        safe_print(f"Debug: project_id={project_id}")

        # Create credentials
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )

        # Force a token refresh to check validity
        try:
            request = Request()
            credentials.refresh(request)
            safe_print("Debug: credentials refreshed successfully")
        except Exception as e:
            safe_print(f"Warning: credentials.refresh() failed: {e}")

        # Build service
        service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        return service, client_email
    except Exception as e:
        safe_print("ERROR: Failed to create Google Drive service: \n" + traceback.format_exc())
        return None, None


def inspect_folder(service, folder_id):
    """Try to get folder metadata and list a few files for debugging."""
    try:
        safe_print(f"Debug: checking folder metadata for ID={folder_id}")
        folder = service.files().get(fileId=folder_id, fields='id, name, owners, permissions').execute()
        safe_print(f"Debug: Folder found: id={folder.get('id')} name={folder.get('name')}")
        owners = folder.get('owners') or []
        safe_print(f"Debug: Folder owners: {[o.get('emailAddress') for o in owners]}")
    except Exception as e:
        safe_print("ERROR: Could not get folder metadata: \n" + traceback.format_exc())

    try:
        safe_print("Debug: listing up to 10 files in folder (if accessible)")
        res = service.files().list(q=f"'{folder_id}' in parents", pageSize=10, fields='files(id,name)').execute()
        files = res.get('files', [])
        safe_print(f"Debug: files in folder (up to 10): {[(f.get('id'), f.get('name')) for f in files]}")
    except Exception as e:
        safe_print("ERROR: Could not list files in folder: \n" + traceback.format_exc())


def upload_pdf_to_gdrive(pdf_path, folder_id):
    """Upload PDF to Google Drive folder with detailed logging."""
    service, client_email = get_gdrive_service()
    if not service:
        safe_print("ERROR: Drive service creation failed")
        return False

    try:
        # Provide debugging info before upload
        safe_print(f"Debug: Attempting upload as service account: {client_email}")
        inspect_folder(service, folder_id)

        filename = os.path.basename(pdf_path)
        safe_print(f"Debug: Uploading {filename} to Google Drive folder {folder_id}...")

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

        safe_print(f"✅ Successfully uploaded to Google Drive!")
        safe_print(f"   File ID: {file_id}")
        safe_print(f"   Link: {web_link}")
        return True

    except Exception as e:
        safe_print("ERROR: Failed to upload PDF: \n" + traceback.format_exc())
        return False


def main():
    """Find and upload the latest PDF."""
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        safe_print("ERROR: GDRIVE_FOLDER_ID environment variable not set")
        return False

    # Find the latest PDF
    output_dir = os.path.join(os.path.dirname(__file__), "Output")
    pdf_files = glob.glob(os.path.join(output_dir, "*.pdf"))

    if not pdf_files:
        safe_print(f"WARNING: No PDF files found in {output_dir}")
        return False

    # Get the most recent PDF
    latest_pdf = max(pdf_files, key=os.path.getctime)
    safe_print(f"Found PDF: {latest_pdf}")

    # Upload to Google Drive
    return upload_pdf_to_gdrive(latest_pdf, folder_id)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
