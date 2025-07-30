import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from config import Config
import logging

logger = logging.getLogger(__name__)

class GoogleDriveManager:
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self):
        self.service = None
        self.folder_id = Config.GOOGLE_DRIVE_FOLDER_ID
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        # Check if token.json exists
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GOOGLE_CREDENTIALS_PATH, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive authentication successful")
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """Create a folder in Google Drive"""
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            logger.info(f"Created folder '{folder_name}' with ID: {folder.get('id')}")
            return folder.get('id')
        
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}': {str(e)}")
            return None
    
    def upload_image(self, file_path, file_name, folder_id=None):
        """Upload an image to Google Drive"""
        try:
            if folder_id is None:
                folder_id = self.folder_id
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id] if folder_id else []
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()
            
            # Make file publicly viewable
            self.service.permissions().create(
                fileId=file.get('id'),
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            logger.info(f"Uploaded '{file_name}' with ID: {file.get('id')}")
            return {
                'id': file.get('id'),
                'web_view_link': file.get('webViewLink'),
                'web_content_link': file.get('webContentLink')
            }
        
        except Exception as e:
            logger.error(f"Error uploading '{file_name}': {str(e)}")
            return None
    
    def upload_data_file(self, file_path, file_name, folder_id=None):
        """Upload a data file (JSON, CSV, etc.) to Google Drive"""
        try:
            if folder_id is None:
                folder_id = self.folder_id
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id] if folder_id else []
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()
            
            logger.info(f"Uploaded data file '{file_name}' with ID: {file.get('id')}")
            return file.get('id')
        
        except Exception as e:
            logger.error(f"Error uploading data file '{file_name}': {str(e)}")
            return None
    
    def list_files(self, folder_id=None, file_type=None):
        """List files in a Google Drive folder"""
        try:
            if folder_id is None:
                folder_id = self.folder_id
            
            query = f"'{folder_id}' in parents and trashed=false"
            if file_type:
                query += f" and mimeType contains '{file_type}'"
            
            results = self.service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, createdTime, size)"
            ).execute()
            
            return results.get('files', [])
        
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file with ID: {file_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False