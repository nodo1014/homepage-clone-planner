"""
이메일 전송 모듈

이 모듈은 클론 기획서 생성기의 분석 결과를 이메일로 전송하는 기능을 제공합니다.
"""
import os
import smtplib
import logging
import asyncio
from email.message import EmailMessage
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import aiosmtplib
from dotenv import load_dotenv

# 로거 설정
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

class EmailSender:
    """이메일 전송을 처리하는 클래스"""
    
    def __init__(self, 
                smtp_server: Optional[str] = None, 
                smtp_port: Optional[int] = None,
                username: Optional[str] = None, 
                password: Optional[str] = None,
                use_tls: bool = True):
        """
        이메일 전송 클래스 초기화
        
        Args:
            smtp_server (Optional[str]): SMTP 서버 주소 (None이면 환경 변수에서 로드)
            smtp_port (Optional[int]): SMTP 포트 (None이면 환경 변수에서 로드)
            username (Optional[str]): SMTP 사용자 이름 (None이면 환경 변수에서 로드)
            password (Optional[str]): SMTP 비밀번호 (None이면 환경 변수에서 로드)
            use_tls (bool): TLS 사용 여부
        """
        # 환경 변수 또는 인자에서 SMTP 정보 설정
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('SMTP_USERNAME', '')
        self.password = password or os.getenv('SMTP_PASSWORD', '')
        self.use_tls = use_tls
        
        # 디버그 모드 설정
        self.debug_mode = os.getenv('EMAIL_DEBUG', 'false').lower() == 'true'
        
        # 재시도 설정
        self.max_retries = int(os.getenv('EMAIL_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('EMAIL_RETRY_DELAY', '5'))
        
        logger.info(f"이메일 전송 클래스 초기화: {self.smtp_server}:{self.smtp_port}")
    
    def send_email(self, 
                  to_email: Union[str, List[str]], 
                  subject: str, 
                  text_content: str,
                  html_content: Optional[str] = None,
                  from_name: Optional[str] = None,
                  from_email: Optional[str] = None, 
                  cc: Optional[Union[str, List[str]]] = None,
                  bcc: Optional[Union[str, List[str]]] = None,
                  attachments: Optional[List[Union[str, Path]]] = None,
                  reply_to: Optional[str] = None) -> bool:
        """
        이메일 전송
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            text_content (str): 이메일 텍스트 내용
            html_content (Optional[str]): 이메일 HTML 내용 (None이면 텍스트만 전송)
            from_name (Optional[str]): 발신자 이름 (None이면 기본값 사용)
            from_email (Optional[str]): 발신자 이메일 (None이면 SMTP 사용자 이름 사용)
            cc (Optional[Union[str, List[str]]]): 참조 이메일 주소 또는 목록
            bcc (Optional[Union[str, List[str]]]): 숨은 참조 이메일 주소 또는 목록
            attachments (Optional[List[Union[str, Path]]]): 첨부 파일 경로 목록
            reply_to (Optional[str]): 답장 이메일 주소
            
        Returns:
            bool: 전송 성공 여부
        """
        # 디버그 모드인 경우 콘솔에 출력만 하고 전송하지 않음
        if self.debug_mode:
            self._print_debug_email(to_email, subject, text_content, html_content, attachments)
            return True
        
        try:
            # 이메일 메시지 준비
            msg = self._create_email_message(
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                from_name=from_name,
                from_email=from_email,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                reply_to=reply_to
            )
            
            # SMTP 서버 연결 및 이메일 전송
            for attempt in range(self.max_retries):
                try:
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        if self.use_tls:
                            server.starttls()
                        
                        if self.username and self.password:
                            server.login(self.username, self.password)
                        
                        # 수신자 목록 생성
                        recipients = self._prepare_recipients(to_email, cc, bcc)
                        
                        # 이메일 전송
                        server.send_message(msg)
                        
                        logger.info(f"이메일 전송 성공: {subject}")
                        return True
                        
                except Exception as e:
                    logger.warning(f"이메일 전송 시도 {attempt + 1}/{self.max_retries} 실패: {str(e)}")
                    if attempt < self.max_retries - 1:
                        # 재시도 전 대기
                        import time
                        time.sleep(self.retry_delay)
                    else:
                        # 최대 재시도 횟수 초과
                        raise
            
            return False
            
        except Exception as e:
            logger.error(f"이메일 전송 실패: {str(e)}")
            return False
    
    async def send_email_async(self, 
                             to_email: Union[str, List[str]], 
                             subject: str, 
                             text_content: str,
                             html_content: Optional[str] = None,
                             from_name: Optional[str] = None,
                             from_email: Optional[str] = None, 
                             cc: Optional[Union[str, List[str]]] = None,
                             bcc: Optional[Union[str, List[str]]] = None,
                             attachments: Optional[List[Union[str, Path]]] = None,
                             reply_to: Optional[str] = None) -> bool:
        """
        비동기 이메일 전송
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            text_content (str): 이메일 텍스트 내용
            html_content (Optional[str]): 이메일 HTML 내용 (None이면 텍스트만 전송)
            from_name (Optional[str]): 발신자 이름 (None이면 기본값 사용)
            from_email (Optional[str]): 발신자 이메일 (None이면 SMTP 사용자 이름 사용)
            cc (Optional[Union[str, List[str]]]): 참조 이메일 주소 또는 목록
            bcc (Optional[Union[str, List[str]]]): 숨은 참조 이메일 주소 또는 목록
            attachments (Optional[List[Union[str, Path]]]): 첨부 파일 경로 목록
            reply_to (Optional[str]): 답장 이메일 주소
            
        Returns:
            bool: 전송 성공 여부
        """
        # 디버그 모드인 경우 콘솔에 출력만 하고 전송하지 않음
        if self.debug_mode:
            self._print_debug_email(to_email, subject, text_content, html_content, attachments)
            return True
        
        try:
            # 이메일 메시지 준비
            msg = self._create_email_message(
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                from_name=from_name,
                from_email=from_email,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                reply_to=reply_to
            )
            
            # 수신자 목록 생성
            recipients = self._prepare_recipients(to_email, cc, bcc)
            
            # SMTP 서버 연결 및 이메일 전송
            for attempt in range(self.max_retries):
                try:
                    # 비동기 SMTP 클라이언트 생성
                    client = aiosmtplib.SMTP(
                        hostname=self.smtp_server,
                        port=self.smtp_port,
                        use_tls=self.use_tls
                    )
                    
                    await client.connect()
                    
                    if self.username and self.password:
                        await client.login(self.username, self.password)
                    
                    # 이메일 전송
                    await client.send_message(msg)
                    await client.quit()
                    
                    logger.info(f"비동기 이메일 전송 성공: {subject}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"비동기 이메일 전송 시도 {attempt + 1}/{self.max_retries} 실패: {str(e)}")
                    if attempt < self.max_retries - 1:
                        # 재시도 전 대기
                        await asyncio.sleep(self.retry_delay)
                    else:
                        # 최대 재시도 횟수 초과
                        raise
            
            return False
            
        except Exception as e:
            logger.error(f"비동기 이메일 전송 실패: {str(e)}")
            return False
    
    def send_results_email(self,
                          to_email: Union[str, List[str]],
                          subject: str,
                          result_content: Dict[str, Any],
                          result_files: List[Union[str, Path]],
                          template_path: Optional[Union[str, Path]] = None) -> bool:
        """
        분석 결과를 이메일로 전송
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            result_content (Dict[str, Any]): 분석 결과 콘텐츠
            result_files (List[Union[str, Path]]): 첨부할 결과 파일 목록
            template_path (Optional[Union[str, Path]]): HTML 템플릿 경로 (None이면 기본 템플릿 사용)
            
        Returns:
            bool: 전송 성공 여부
        """
        # 결과 콘텐츠에서 정보 추출
        website_name = result_content.get('website', {}).get('name', '웹사이트')
        website_url = result_content.get('website', {}).get('url', '#')
        description = result_content.get('description', '분석 결과입니다.')
        
        # 텍스트 이메일 내용 생성
        text_content = f"""
홈페이지 클론 기획서 생성기 - 분석 결과

웹사이트: {website_name}
URL: {website_url}
설명: {description}

첨부된 파일에서 자세한 분석 결과를 확인하세요.
"""
        
        # HTML 이메일 내용 생성
        if template_path and os.path.exists(template_path):
            # 템플릿 파일에서 HTML 내용 로드
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
                
            # 변수 대체
            html_content = html_template.replace('{{website_name}}', website_name)
            html_content = html_content.replace('{{website_url}}', website_url)
            html_content = html_content.replace('{{description}}', description)
        else:
            # 기본 HTML 내용 생성
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .button {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>홈페이지 클론 기획서 생성기 - 분석 결과</h1>
    <p>다음 웹사이트에 대한 분석 결과를 보내드립니다.</p>
    
    <table>
        <tr>
            <th>웹사이트</th>
            <td>{website_name}</td>
        </tr>
        <tr>
            <th>URL</th>
            <td><a href="{website_url}">{website_url}</a></td>
        </tr>
        <tr>
            <th>설명</th>
            <td>{description}</td>
        </tr>
    </table>
    
    <p>첨부된 파일에서 자세한 분석 결과를 확인하세요.</p>
    
    <p>감사합니다.</p>
</body>
</html>
"""
        
        # 이메일 전송
        return self.send_email(
            to_email=to_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            attachments=result_files
        )
    
    async def send_results_email_async(self,
                                     to_email: Union[str, List[str]],
                                     subject: str,
                                     result_content: Dict[str, Any],
                                     result_files: List[Union[str, Path]],
                                     template_path: Optional[Union[str, Path]] = None) -> bool:
        """
        분석 결과를 비동기로 이메일 전송
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            result_content (Dict[str, Any]): 분석 결과 콘텐츠
            result_files (List[Union[str, Path]]): 첨부할 결과 파일 목록
            template_path (Optional[Union[str, Path]]): HTML 템플릿 경로 (None이면 기본 템플릿 사용)
            
        Returns:
            bool: 전송 성공 여부
        """
        # 결과 콘텐츠에서 정보 추출
        website_name = result_content.get('website', {}).get('name', '웹사이트')
        website_url = result_content.get('website', {}).get('url', '#')
        description = result_content.get('description', '분석 결과입니다.')
        
        # 텍스트 이메일 내용 생성
        text_content = f"""
홈페이지 클론 기획서 생성기 - 분석 결과

웹사이트: {website_name}
URL: {website_url}
설명: {description}

첨부된 파일에서 자세한 분석 결과를 확인하세요.
"""
        
        # HTML 이메일 내용 생성
        if template_path and os.path.exists(template_path):
            # 템플릿 파일에서 HTML 내용 로드
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
                
            # 변수 대체
            html_content = html_template.replace('{{website_name}}', website_name)
            html_content = html_content.replace('{{website_url}}', website_url)
            html_content = html_content.replace('{{description}}', description)
        else:
            # 기본 HTML 내용 생성
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .button {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>홈페이지 클론 기획서 생성기 - 분석 결과</h1>
    <p>다음 웹사이트에 대한 분석 결과를 보내드립니다.</p>
    
    <table>
        <tr>
            <th>웹사이트</th>
            <td>{website_name}</td>
        </tr>
        <tr>
            <th>URL</th>
            <td><a href="{website_url}">{website_url}</a></td>
        </tr>
        <tr>
            <th>설명</th>
            <td>{description}</td>
        </tr>
    </table>
    
    <p>첨부된 파일에서 자세한 분석 결과를 확인하세요.</p>
    
    <p>감사합니다.</p>
</body>
</html>
"""
        
        # 비동기 이메일 전송
        return await self.send_email_async(
            to_email=to_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            attachments=result_files
        )
    
    def _create_email_message(self,
                           to_email: Union[str, List[str]], 
                           subject: str, 
                           text_content: str,
                           html_content: Optional[str] = None,
                           from_name: Optional[str] = None,
                           from_email: Optional[str] = None, 
                           cc: Optional[Union[str, List[str]]] = None,
                           bcc: Optional[Union[str, List[str]]] = None,
                           attachments: Optional[List[Union[str, Path]]] = None,
                           reply_to: Optional[str] = None) -> EmailMessage:
        """
        이메일 메시지 객체 생성
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            text_content (str): 이메일 텍스트 내용
            html_content (Optional[str]): 이메일 HTML 내용 (None이면 텍스트만 전송)
            from_name (Optional[str]): 발신자 이름 (None이면 기본값 사용)
            from_email (Optional[str]): 발신자 이메일 (None이면 SMTP 사용자 이름 사용)
            cc (Optional[Union[str, List[str]]]): 참조 이메일 주소 또는 목록
            bcc (Optional[Union[str, List[str]]]): 숨은 참조 이메일 주소 또는 목록
            attachments (Optional[List[Union[str, Path]]]): 첨부 파일 경로 목록
            reply_to (Optional[str]): 답장 이메일 주소
            
        Returns:
            EmailMessage: 이메일 메시지 객체
        """
        # 발신자 정보 설정
        from_name = from_name or os.getenv('EMAIL_FROM_NAME', '홈페이지 클론 기획서 생성기')
        from_email = from_email or self.username or os.getenv('EMAIL_FROM_ADDRESS', 'noreply@example.com')
        
        # 이메일 메시지 객체 생성
        if html_content:
            # HTML 및 텍스트 콘텐츠가 모두 있는 경우 멀티파트 메시지
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        else:
            # 텍스트만 있는 경우
            msg = EmailMessage()
            msg.set_content(text_content)
        
        # 이메일 헤더 설정
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_email}>"
        
        # 수신자 설정
        if isinstance(to_email, list):
            msg['To'] = ', '.join(to_email)
        else:
            msg['To'] = to_email
        
        # 참조(CC) 설정
        if cc:
            if isinstance(cc, list):
                msg['Cc'] = ', '.join(cc)
            else:
                msg['Cc'] = cc
        
        # 숨은 참조(BCC) 설정
        if bcc:
            if isinstance(bcc, list):
                msg['Bcc'] = ', '.join(bcc)
            else:
                msg['Bcc'] = bcc
        
        # 답장 주소 설정
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # 첨부 파일 처리
        if attachments and (html_content or isinstance(msg, MIMEMultipart)):
            # 만약 첨부 파일이 있고 아직 멀티파트가 아니라면 멀티파트로 변환
            if not isinstance(msg, MIMEMultipart):
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                multipart_msg = MIMEMultipart()
                
                # 헤더 복사
                for key, value in msg.items():
                    multipart_msg[key] = value
                
                multipart_msg.attach(text_part)
                msg = multipart_msg
            
            # 첨부 파일 추가
            for attachment in attachments:
                attachment_path = Path(attachment)
                if attachment_path.exists():
                    with open(attachment_path, 'rb') as f:
                        part = MIMEApplication(f.read(), Name=attachment_path.name)
                    
                    part['Content-Disposition'] = f'attachment; filename="{attachment_path.name}"'
                    msg.attach(part)
                else:
                    logger.warning(f"첨부 파일을 찾을 수 없음: {attachment_path}")
        
        return msg
    
    def _prepare_recipients(self, 
                           to_email: Union[str, List[str]], 
                           cc: Optional[Union[str, List[str]]] = None,
                           bcc: Optional[Union[str, List[str]]] = None) -> List[str]:
        """
        모든 수신자 목록 생성
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            cc (Optional[Union[str, List[str]]]): 참조 이메일 주소 또는 목록
            bcc (Optional[Union[str, List[str]]]): 숨은 참조 이메일 주소 또는 목록
            
        Returns:
            List[str]: 모든 수신자 목록
        """
        recipients = []
        
        # 주 수신자 추가
        if isinstance(to_email, list):
            recipients.extend(to_email)
        else:
            recipients.append(to_email)
        
        # 참조(CC) 수신자 추가
        if cc:
            if isinstance(cc, list):
                recipients.extend(cc)
            else:
                recipients.append(cc)
        
        # 숨은 참조(BCC) 수신자 추가
        if bcc:
            if isinstance(bcc, list):
                recipients.extend(bcc)
            else:
                recipients.append(bcc)
        
        return recipients
    
    def _print_debug_email(self, 
                          to_email: Union[str, List[str]], 
                          subject: str, 
                          text_content: str,
                          html_content: Optional[str] = None,
                          attachments: Optional[List[Union[str, Path]]] = None) -> None:
        """
        디버그 모드에서 이메일 내용 출력
        
        Args:
            to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
            subject (str): 이메일 제목
            text_content (str): 이메일 텍스트 내용
            html_content (Optional[str]): 이메일 HTML 내용
            attachments (Optional[List[Union[str, Path]]]): 첨부 파일 목록
        """
        logger.info("======= 디버그 모드: 이메일 전송 시뮬레이션 =======")
        logger.info(f"수신자: {to_email}")
        logger.info(f"제목: {subject}")
        logger.info(f"내용:\n{text_content}")
        
        if html_content:
            logger.info(f"HTML 내용: {html_content[:100]}...")
        
        if attachments:
            logger.info(f"첨부 파일: {attachments}")
        
        logger.info("===================================================")


# 유틸리티 함수
def send_simple_email(to_email: Union[str, List[str]], 
                     subject: str, 
                     content: str,
                     attachments: Optional[List[Union[str, Path]]] = None) -> bool:
    """
    간단한 이메일 전송 유틸리티 함수
    
    Args:
        to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
        subject (str): 이메일 제목
        content (str): 이메일 내용 (텍스트)
        attachments (Optional[List[Union[str, Path]]]): 첨부 파일 경로 목록
        
    Returns:
        bool: 전송 성공 여부
    """
    sender = EmailSender()
    return sender.send_email(
        to_email=to_email,
        subject=subject,
        text_content=content,
        attachments=attachments
    )

async def send_simple_email_async(to_email: Union[str, List[str]], 
                                subject: str, 
                                content: str,
                                attachments: Optional[List[Union[str, Path]]] = None) -> bool:
    """
    간단한 비동기 이메일 전송 유틸리티 함수
    
    Args:
        to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
        subject (str): 이메일 제목
        content (str): 이메일 내용 (텍스트)
        attachments (Optional[List[Union[str, Path]]]): 첨부 파일 경로 목록
        
    Returns:
        bool: 전송 성공 여부
    """
    sender = EmailSender()
    return await sender.send_email_async(
        to_email=to_email,
        subject=subject,
        text_content=content,
        attachments=attachments
    )

def send_analysis_results(to_email: Union[str, List[str]],
                         result_content: Dict[str, Any],
                         result_files: List[Union[str, Path]],
                         template_path: Optional[Union[str, Path]] = None) -> bool:
    """
    분석 결과를 이메일로 전송하는 유틸리티 함수
    
    Args:
        to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
        result_content (Dict[str, Any]): 분석 결과 콘텐츠
        result_files (List[Union[str, Path]]): 첨부할 결과 파일 목록
        template_path (Optional[Union[str, Path]]): HTML 템플릿 경로 (None이면 기본 템플릿 사용)
        
    Returns:
        bool: 전송 성공 여부
    """
    website_name = result_content.get('website', {}).get('name', '웹사이트')
    subject = f"홈페이지 클론 기획서 생성기 - {website_name} 분석 결과"
    
    sender = EmailSender()
    return sender.send_results_email(
        to_email=to_email,
        subject=subject,
        result_content=result_content,
        result_files=result_files,
        template_path=template_path
    )

async def send_analysis_results_async(to_email: Union[str, List[str]],
                                    result_content: Dict[str, Any],
                                    result_files: List[Union[str, Path]],
                                    template_path: Optional[Union[str, Path]] = None) -> bool:
    """
    분석 결과를 비동기로 이메일 전송하는 유틸리티 함수
    
    Args:
        to_email (Union[str, List[str]]): 수신자 이메일 주소 또는 목록
        result_content (Dict[str, Any]): 분석 결과 콘텐츠
        result_files (List[Union[str, Path]]): 첨부할 결과 파일 목록
        template_path (Optional[Union[str, Path]]): HTML 템플릿 경로 (None이면 기본 템플릿 사용)
        
    Returns:
        bool: 전송 성공 여부
    """
    website_name = result_content.get('website', {}).get('name', '웹사이트')
    subject = f"홈페이지 클론 기획서 생성기 - {website_name} 분석 결과"
    
    sender = EmailSender()
    return await sender.send_results_email_async(
        to_email=to_email,
        subject=subject,
        result_content=result_content,
        result_files=result_files,
        template_path=template_path
    ) 