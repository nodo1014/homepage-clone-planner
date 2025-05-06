"""
구글 드라이브 API 클라이언트 모듈

이 모듈은 구글 드라이브와의 연동을 처리하는 클라이언트를 제공합니다.
주요 기능:
- OAuth 인증 및 토큰 관리
- 파일 업로드
- 공유 설정
- 폴더 생성 및 관리
"""
import os
import pickle
import logging
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path
import json
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# 로거 설정
logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """구글 드라이브 API 클라이언트 클래스"""
    
    # 필요한 권한 범위
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',  # 앱이 생성한 파일만 접근
        'https://www.googleapis.com/auth/drive.metadata.readonly'  # 파일 메타데이터 읽기
    ]
    
    def __init__(self, 
                credentials_file: Optional[str] = None,
                token_file: Optional[str] = None,
                credentials_dict: Optional[Dict[str, Any]] = None):
        """
        구글 드라이브 클라이언트 초기화
        
        Args:
            credentials_file (Optional[str]): OAuth 클라이언트 인증 정보 파일 경로
            token_file (Optional[str]): 토큰 저장 파일 경로
            credentials_dict (Optional[Dict[str, Any]]): OAuth 클라이언트 인증 정보 딕셔너리
        """
        # 환경 변수에서 기본값 로드
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = token_file or os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
        self.credentials_dict = credentials_dict
        
        # 인증 상태
        self.credentials = None
        self.service = None
        self.is_authenticated = False
        
        # 마지막 인증/초기화 시도 시간 기록
        self.last_auth_attempt = None
        
        logger.info("구글 드라이브 클라이언트가 초기화되었습니다.")
    
    def authenticate(self, force_refresh: bool = False) -> bool:
        """
        구글 드라이브 API 인증 수행
        
        Args:
            force_refresh (bool): 기존 토큰이 있어도 강제로 재인증
            
        Returns:
            bool: 인증 성공 여부
        """
        # 이미 인증되어 있고 강제 갱신이 아니면 바로 성공 반환
        if self.is_authenticated and not force_refresh:
            return True
        
        # 마지막 인증 시도 시간 기록
        self.last_auth_attempt = datetime.now()
        
        try:
            # 기존 토큰 로드 시도
            if os.path.exists(self.token_file) and not force_refresh:
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # 유효한 토큰 확인
            if not self.credentials or not self.credentials.valid:
                # 만료된 토큰이면 갱신 시도
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # 인증 정보 가져오기
                    if self.credentials_dict:
                        # 딕셔너리에서 인증 정보 로드
                        flow = InstalledAppFlow.from_client_config(self.credentials_dict, self.SCOPES)
                    elif os.path.exists(self.credentials_file):
                        # 파일에서 인증 정보 로드
                        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                    else:
                        logger.error("구글 드라이브 인증 정보를 찾을 수 없습니다.")
                        return False
                    
                    # 로컬 서버에서 인증 처리
                    self.credentials = flow.run_local_server(port=0)
                
                # 토큰 저장
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # 드라이브 서비스 빌드
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.is_authenticated = True
            
            logger.info("구글 드라이브 인증 성공")
            return True
            
        except Exception as e:
            logger.error(f"구글 드라이브 인증 실패: {str(e)}")
            self.is_authenticated = False
            return False
    
    def upload_file(self, 
                   file_path: Union[str, Path], 
                   mime_type: Optional[str] = None,
                   folder_id: Optional[str] = None,
                   name: Optional[str] = None) -> Optional[str]:
        """
        파일을 구글 드라이브에 업로드
        
        Args:
            file_path (Union[str, Path]): 업로드할 파일 경로
            mime_type (Optional[str]): 파일의 MIME 타입 (None이면 자동 감지)
            folder_id (Optional[str]): 파일을 업로드할 폴더 ID (None이면 루트)
            name (Optional[str]): 업로드 후 파일 이름 (None이면 원본 파일 이름 사용)
            
        Returns:
            Optional[str]: 업로드된 파일의 ID 또는 실패 시 None
        """
        if not self.authenticate():
            return None
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"업로드할 파일을 찾을 수 없습니다: {file_path}")
                return None
            
            # 파일 이름 설정
            if not name:
                name = file_path.name
            
            # MIME 타입 자동 감지
            if not mime_type:
                mime_type = self._guess_mime_type(file_path)
            
            # 파일 메타데이터 설정
            file_metadata = {'name': name}
            
            # 폴더 지정이 있으면 부모 설정
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # 미디어 업로드 객체 생성
            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
            
            # 파일 업로드
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"파일이 성공적으로 업로드되었습니다. ID: {file_id}")
            return file_id
            
        except HttpError as e:
            logger.error(f"파일 업로드 중 HTTP 오류 발생: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"파일 업로드 중 오류 발생: {str(e)}")
            return None
    
    def create_folder(self, 
                     folder_name: str, 
                     parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        구글 드라이브에 새 폴더 생성
        
        Args:
            folder_name (str): 생성할 폴더 이름
            parent_folder_id (Optional[str]): 부모 폴더 ID (None이면 루트)
            
        Returns:
            Optional[str]: 생성된 폴더의 ID 또는 실패 시 None
        """
        if not self.authenticate():
            return None
        
        try:
            # 폴더 메타데이터 설정
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # 부모 폴더 지정이 있으면 추가
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            # 폴더 생성
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"폴더가 성공적으로 생성되었습니다. ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"폴더 생성 중 HTTP 오류 발생: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"폴더 생성 중 오류 발생: {str(e)}")
            return None
    
    def set_permission(self, 
                      file_id: str, 
                      role: str = 'reader', 
                      type: str = 'anyone') -> bool:
        """
        파일 또는 폴더의 권한 설정
        
        Args:
            file_id (str): 파일 또는 폴더 ID
            role (str): 권한 역할 ('reader', 'writer', 'commenter')
            type (str): 권한 유형 ('user', 'group', 'domain', 'anyone')
            
        Returns:
            bool: 권한 설정 성공 여부
        """
        if not self.authenticate():
            return False
        
        try:
            # 공유 권한 설정
            permission = {
                'role': role,
                'type': type
            }
            
            # 누구나 접근 가능한 설정인 경우
            if type == 'anyone':
                permission['allowFileDiscovery'] = False
            
            # 권한 추가
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"파일 ID '{file_id}'에 대한 권한이 설정되었습니다. 역할: {role}, 유형: {type}")
            return True
            
        except HttpError as e:
            logger.error(f"권한 설정 중 HTTP 오류 발생: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"권한 설정 중 오류 발생: {str(e)}")
            return False
    
    def get_file_url(self, file_id: str) -> Optional[str]:
        """
        파일의 공유 URL 가져오기
        
        Args:
            file_id (str): 파일 ID
            
        Returns:
            Optional[str]: 파일 공유 URL 또는 실패 시 None
        """
        if not file_id:
            return None
        
        return f"https://drive.google.com/file/d/{file_id}/view"
    
    def get_folder_url(self, folder_id: str) -> Optional[str]:
        """
        폴더의 공유 URL 가져오기
        
        Args:
            folder_id (str): 폴더 ID
            
        Returns:
            Optional[str]: 폴더 공유 URL 또는 실패 시 None
        """
        if not folder_id:
            return None
        
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def list_files(self, 
                  folder_id: Optional[str] = None, 
                  query: Optional[str] = None,
                  page_size: int = 100) -> List[Dict[str, Any]]:
        """
        구글 드라이브 파일 목록 조회
        
        Args:
            folder_id (Optional[str]): 폴더 ID (None이면 전체 파일)
            query (Optional[str]): 추가 검색 쿼리
            page_size (int): 한 번에 가져올 파일 수
            
        Returns:
            List[Dict[str, Any]]: 파일 메타데이터 목록
        """
        if not self.authenticate():
            return []
        
        try:
            # 기본 쿼리 설정
            q = "trashed=false"  # 휴지통에 없는 파일만
            
            # 폴더 지정이 있으면 해당 폴더의 파일만 조회
            if folder_id:
                q += f" and '{folder_id}' in parents"
            
            # 추가 쿼리 지정이 있으면 추가
            if query:
                q += f" and {query}"
            
            # 파일 목록 조회
            results = self.service.files().list(
                q=q,
                pageSize=page_size,
                fields="files(id, name, mimeType, webViewLink, createdTime, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"{len(files)}개의 파일을 조회했습니다.")
            return files
            
        except HttpError as e:
            logger.error(f"파일 목록 조회 중 HTTP 오류 발생: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"파일 목록 조회 중 오류 발생: {str(e)}")
            return []
    
    def delete_file(self, file_id: str) -> bool:
        """
        파일 또는 폴더 삭제
        
        Args:
            file_id (str): 삭제할 파일 또는 폴더 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        if not self.authenticate():
            return False
        
        try:
            # 파일 삭제
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"파일 ID '{file_id}'가 삭제되었습니다.")
            return True
            
        except HttpError as e:
            logger.error(f"파일 삭제 중 HTTP 오류 발생: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"파일 삭제 중 오류 발생: {str(e)}")
            return False
    
    def export_to_google_drive(self, 
                             file_path: Union[str, Path],
                             folder_name: Optional[str] = None,
                             make_public: bool = True) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        파일을 구글 드라이브로 내보내기
        
        Args:
            file_path (Union[str, Path]): 내보낼 파일 경로
            folder_name (Optional[str]): 파일을 저장할 폴더 이름 (None이면 현재 날짜 사용)
            make_public (bool): 파일을 공개 액세스로 설정할지 여부
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (성공 여부, 파일 ID, 파일 URL)
        """
        if not self.authenticate():
            return False, None, None
        
        try:
            # 기본 폴더 이름 생성 (지정되지 않은 경우)
            if not folder_name:
                today = datetime.now().strftime("%Y-%m-%d")
                folder_name = f"홈페이지 클론 기획서 {today}"
            
            # 폴더 생성
            folder_id = self.create_folder(folder_name)
            if not folder_id:
                logger.error("내보내기용 폴더 생성 실패")
                return False, None, None
            
            # 파일 업로드
            file_id = self.upload_file(file_path, folder_id=folder_id)
            if not file_id:
                logger.error("파일 업로드 실패")
                return False, None, None
            
            # 필요한 경우 공개 권한 설정
            if make_public:
                self.set_permission(file_id)
            
            # 파일 URL 생성
            file_url = self.get_file_url(file_id)
            
            logger.info(f"파일이 성공적으로 구글 드라이브로 내보내졌습니다. URL: {file_url}")
            return True, file_id, file_url
            
        except Exception as e:
            logger.error(f"구글 드라이브로 내보내기 실패: {str(e)}")
            return False, None, None
    
    def _guess_mime_type(self, file_path: Path) -> str:
        """
        파일 확장자를 기반으로 MIME 타입 추측
        
        Args:
            file_path (Path): 파일 경로
            
        Returns:
            str: MIME 타입
        """
        extension = file_path.suffix.lower()
        
        # 주요 파일 형식에 대한 MIME 타입 매핑
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.zip': 'application/zip',
            '.md': 'text/markdown',
        }
        
        return mime_types.get(extension, 'application/octet-stream')  # 기본값


# 유틸리티 함수
def create_google_drive_client(credentials_file: Optional[str] = None,
                              token_file: Optional[str] = None) -> GoogleDriveClient:
    """
    구글 드라이브 클라이언트 생성 유틸리티 함수
    
    Args:
        credentials_file (Optional[str]): 인증 정보 파일 경로
        token_file (Optional[str]): 토큰 저장 파일 경로
        
    Returns:
        GoogleDriveClient: 구글 드라이브 클라이언트 인스턴스
    """
    client = GoogleDriveClient(credentials_file, token_file)
    return client


def upload_to_google_drive(file_path: Union[str, Path],
                         folder_name: Optional[str] = None,
                         make_public: bool = True,
                         credentials_file: Optional[str] = None,
                         token_file: Optional[str] = None) -> Optional[str]:
    """
    파일을 구글 드라이브에 업로드하는 유틸리티 함수
    
    Args:
        file_path (Union[str, Path]): 업로드할 파일 경로
        folder_name (Optional[str]): 파일을 저장할 폴더 이름
        make_public (bool): 파일을 공개 액세스로 설정할지 여부
        credentials_file (Optional[str]): 인증 정보 파일 경로
        token_file (Optional[str]): 토큰 저장 파일 경로
        
    Returns:
        Optional[str]: 업로드된 파일의 URL 또는 실패 시 None
    """
    client = create_google_drive_client(credentials_file, token_file)
    success, _, file_url = client.export_to_google_drive(file_path, folder_name, make_public)
    
    if success:
        return file_url
    else:
        return None 