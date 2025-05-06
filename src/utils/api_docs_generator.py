"""
API 문서 자동 생성 도구

이 모듈은 FastAPI 애플리케이션에서 API 엔드포인트 정보를 추출하여
마크다운 또는 HTML 형식의 문서를 자동으로 생성합니다.

기능:
- FastAPI 앱에서 모든 라우트 정보 추출
- 경로, HTTP 메서드, 파라미터, 응답 형식 등의 메타데이터 수집
- 마크다운 또는 HTML 형식의 API 문서 생성
- 문서 하이라이트 및 코드 예제 자동 생성
"""
import inspect
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, get_type_hints

from fastapi import APIRouter, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from pydantic import BaseModel

# 로거 설정
logger = logging.getLogger(__name__)

class APIDocGenerator:
    """API 문서 자동 생성 클래스"""
    
    def __init__(self, app: FastAPI, title: str = "API 문서", 
                 description: str = "FastAPI 애플리케이션의 API 문서입니다."):
        """
        API 문서 생성기 초기화
        
        Args:
            app (FastAPI): FastAPI 애플리케이션 인스턴스
            title (str): 문서 제목
            description (str): 문서 설명
        """
        self.app = app
        self.title = title
        self.description = description
        self.version = getattr(app, "version", "0.1.0")
        self.routes_info = []
        
    def extract_routes(self) -> List[Dict[str, Any]]:
        """
        FastAPI 앱에서 모든 라우트 정보 추출
        
        Returns:
            List[Dict[str, Any]]: 라우트 정보 목록
        """
        routes_info = []
        
        # OpenAPI 스키마 가져오기
        openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            description=self.description,
            routes=self.app.routes
        )
        
        # 경로 순서대로 정렬
        paths = sorted(openapi_schema["paths"].items())
        
        for path, path_item in paths:
            for method, operation in path_item.items():
                if method == "parameters":  # 경로 매개변수는 건너뜀
                    continue
                    
                method = method.upper()
                
                # 기본 라우트 정보
                route_info = {
                    "path": path,
                    "method": method,
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                    "parameters": self._extract_parameters(operation),
                    "request_body": self._extract_request_body(operation),
                    "responses": self._extract_responses(operation),
                    "deprecated": operation.get("deprecated", False)
                }
                
                # 라우트 핸들러 함수 소스코드 추출 (가능한 경우)
                handler_func = self._find_handler_function(path, method)
                if handler_func:
                    route_info["handler_source"] = inspect.getsource(handler_func)
                    route_info["handler_name"] = handler_func.__name__
                    route_info["handler_module"] = handler_func.__module__
                
                routes_info.append(route_info)
        
        self.routes_info = routes_info
        return routes_info
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        OpenAPI 작업에서 매개변수 정보 추출
        
        Args:
            operation (Dict[str, Any]): OpenAPI 작업 객체
            
        Returns:
            List[Dict[str, Any]]: 매개변수 정보 목록
        """
        params = []
        
        for param in operation.get("parameters", []):
            param_info = {
                "name": param.get("name", ""),
                "in": param.get("in", ""),  # path, query, header, cookie
                "description": param.get("description", ""),
                "required": param.get("required", False),
                "schema": param.get("schema", {})
            }
            params.append(param_info)
            
        return params
    
    def _extract_request_body(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        OpenAPI 작업에서 요청 본문 정보 추출
        
        Args:
            operation (Dict[str, Any]): OpenAPI 작업 객체
            
        Returns:
            Dict[str, Any]: 요청 본문 정보
        """
        request_body = operation.get("requestBody", {})
        if not request_body:
            return {}
            
        content = request_body.get("content", {})
        
        # 일반적으로 사용되는 미디어 타입 순서대로 확인
        for media_type in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]:
            if media_type in content:
                return {
                    "media_type": media_type,
                    "schema": content[media_type].get("schema", {}),
                    "required": request_body.get("required", False)
                }
                
        # 첫 번째 미디어 타입 사용 (없으면 빈 dict 반환)
        if content:
            media_type = next(iter(content))
            return {
                "media_type": media_type,
                "schema": content[media_type].get("schema", {}),
                "required": request_body.get("required", False)
            }
            
        return {}
    
    def _extract_responses(self, operation: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        OpenAPI 작업에서 응답 정보 추출
        
        Args:
            operation (Dict[str, Any]): OpenAPI 작업 객체
            
        Returns:
            Dict[str, Dict[str, Any]]: 응답 코드별 정보
        """
        responses = {}
        
        for status_code, response in operation.get("responses", {}).items():
            resp_info = {
                "description": response.get("description", ""),
                "content": {}
            }
            
            content = response.get("content", {})
            for media_type, media_info in content.items():
                resp_info["content"][media_type] = {
                    "schema": media_info.get("schema", {})
                }
                
            responses[status_code] = resp_info
            
        return responses
    
    def _find_handler_function(self, path: str, method: str) -> Optional[callable]:
        """
        경로와 메서드에 해당하는 핸들러 함수 찾기
        
        Args:
            path (str): API 경로
            method (str): HTTP 메서드
            
        Returns:
            Optional[callable]: 핸들러 함수 (없으면 None)
        """
        # FastAPI 경로 패턴을 정규식으로 변환
        path_regex = path
        path_regex = re.sub(r"{([^}]+)}", r"[^/]+", path_regex)
        path_regex = f"^{path_regex}$"
        
        method = method.lower()
        
        # 모든 라우트 확인
        for route in self.app.routes:
            if not isinstance(route, APIRoute):
                continue
                
            if method not in route.methods:
                continue
                
            route_path = route.path
            if re.match(path_regex, route_path) or path == route_path:
                return route.endpoint
                
        return None
    
    def generate_markdown(self, output_path: Optional[str] = None, 
                         include_code: bool = True) -> str:
        """
        마크다운 형식의 API 문서 생성
        
        Args:
            output_path (Optional[str]): 출력 파일 경로 (None이면 반환만 함)
            include_code (bool): 핸들러 함수 소스코드 포함 여부
            
        Returns:
            str: 생성된 마크다운 문서
        """
        if not self.routes_info:
            self.extract_routes()
            
        md_parts = []
        
        # 문서 제목 및 설명
        md_parts.append(f"# {self.title}\n")
        md_parts.append(f"{self.description}\n")
        md_parts.append(f"API 버전: {self.version}\n")
        
        # 태그별 그룹화
        tags = set()
        for route in self.routes_info:
            tags.update(route.get("tags", []))
            
        tags = sorted(tags) if tags else ["기본"]
        
        # 목차 생성
        md_parts.append("## 목차\n")
        for tag in tags:
            tag_slug = tag.lower().replace(" ", "-")
            md_parts.append(f"- [{tag}](#{tag_slug})\n")
        md_parts.append("\n")
        
        # 태그별 API 문서 생성
        for tag in tags:
            tag_routes = [r for r in self.routes_info if tag in r.get("tags", []) or (not r.get("tags") and tag == "기본")]
            
            if not tag_routes:
                continue
                
            md_parts.append(f"## {tag}\n")
            
            for route in tag_routes:
                path = route["path"]
                method = route["method"]
                summary = route["summary"] or path
                
                md_parts.append(f"### {method} {path}\n")
                
                if route["summary"]:
                    md_parts.append(f"**요약:** {route['summary']}\n")
                    
                if route["description"]:
                    md_parts.append(f"{route['description']}\n")
                    
                # 매개변수 정보
                if route["parameters"]:
                    md_parts.append("#### 매개변수\n")
                    md_parts.append("| 이름 | 위치 | 타입 | 필수 | 설명 |\n")
                    md_parts.append("|------|------|------|------|------|\n")
                    
                    for param in route["parameters"]:
                        name = param["name"]
                        param_in = param["in"]
                        required = "✓" if param["required"] else ""
                        description = param["description"]
                        
                        # 스키마에서 타입 추출
                        schema = param["schema"]
                        param_type = schema.get("type", "")
                        if param_type == "array" and "items" in schema:
                            items_type = schema["items"].get("type", "object")
                            param_type = f"array[{items_type}]"
                        elif "enum" in schema:
                            enum_values = ", ".join([f"`{v}`" for v in schema["enum"]])
                            param_type = f"{param_type} enum({enum_values})"
                            
                        md_parts.append(f"| {name} | {param_in} | {param_type} | {required} | {description} |\n")
                    
                    md_parts.append("\n")
                
                # 요청 본문 정보
                if route["request_body"]:
                    md_parts.append("#### 요청 본문\n")
                    media_type = route["request_body"]["media_type"]
                    required = "필수" if route["request_body"]["required"] else "선택"
                    
                    md_parts.append(f"- **미디어 타입:** `{media_type}`\n")
                    md_parts.append(f"- **필수 여부:** {required}\n")
                    
                    schema = route["request_body"]["schema"]
                    if schema:
                        md_parts.append(f"- **스키마:**\n\n```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n")
                    
                    md_parts.append("\n")
                
                # 응답 정보
                if route["responses"]:
                    md_parts.append("#### 응답\n")
                    
                    for status_code, response in route["responses"].items():
                        md_parts.append(f"##### {status_code} - {response['description']}\n")
                        
                        for media_type, content in response["content"].items():
                            md_parts.append(f"- **미디어 타입:** `{media_type}`\n")
                            
                            schema = content["schema"]
                            if schema:
                                md_parts.append(f"- **스키마:**\n\n```json\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n```\n")
                        
                        md_parts.append("\n")
                
                # 핸들러 함수 소스코드 (선택적)
                if include_code and "handler_source" in route:
                    md_parts.append("#### 구현 코드\n")
                    md_parts.append(f"- **함수:** `{route['handler_name']}`\n")
                    md_parts.append(f"- **모듈:** `{route['handler_module']}`\n")
                    md_parts.append(f"```python\n{route['handler_source']}\n```\n")
                
                md_parts.append("\n---\n")
        
        md_content = "\n".join(md_parts)
        
        # 파일로 저장
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            logger.info(f"API 문서가 {output_path}에 저장되었습니다.")
            
        return md_content
    
    def generate_html(self, output_path: Optional[str] = None,
                     include_code: bool = True, 
                     css: Optional[str] = None) -> str:
        """
        HTML 형식의 API 문서 생성
        
        Args:
            output_path (Optional[str]): 출력 파일 경로 (None이면 반환만 함)
            include_code (bool): 핸들러 함수 소스코드 포함 여부
            css (Optional[str]): CSS 스타일시트 경로
            
        Returns:
            str: 생성된 HTML 문서
        """
        # 마크다운 문서 생성
        md_content = self.generate_markdown(output_path=None, include_code=include_code)
        
        try:
            # 마크다운을 HTML로 변환
            import markdown
            html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
            
            # 기본 CSS 스타일 또는 사용자 지정 CSS
            if css and os.path.exists(css):
                with open(css, "r", encoding="utf-8") as f:
                    css_content = f.read()
            else:
                css_content = """
                body {
                    font-family: 'Noto Sans KR', Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    color: #333;
                }
                h1, h2, h3, h4, h5, h6 {
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                    color: #1a1a1a;
                }
                h1 { font-size: 2.2em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
                h2 { font-size: 1.8em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
                h3 { font-size: 1.5em; }
                h4 { font-size: 1.3em; }
                table { border-collapse: collapse; width: 100%; margin: 1em 0; }
                th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
                th { background-color: #f2f2f2; }
                pre { background-color: #f5f5f5; padding: 1em; overflow-x: auto; border-radius: 3px; }
                code { background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
                hr { border: 0; border-top: 1px solid #eee; margin: 2em 0; }
                a { color: #0366d6; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .container { display: flex; flex-direction: row; }
                .toc { position: sticky; top: 20px; width: 250px; max-height: calc(100vh - 40px); overflow-y: auto; padding-right: 20px; }
                .content { flex: 1; }
                @media (max-width: 768px) {
                    .container { flex-direction: column; }
                    .toc { width: 100%; position: relative; }
                }
                """
                
            # HTML 템플릿
            html_template = f"""<!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.title}</title>
                <style>
                {css_content}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        {html_body}
                    </div>
                </div>
                
                <script>
                // 코드 하이라이팅 기능 추가
                document.addEventListener('DOMContentLoaded', function() {{
                    var pres = document.querySelectorAll('pre');
                    for (var i = 0; i < pres.length; i++) {{
                        var pre = pres[i];
                        pre.style.position = 'relative';
                        
                        // 복사 버튼 추가
                        var copyBtn = document.createElement('button');
                        copyBtn.textContent = '복사';
                        copyBtn.style.position = 'absolute';
                        copyBtn.style.right = '5px';
                        copyBtn.style.top = '5px';
                        copyBtn.style.fontSize = '12px';
                        copyBtn.style.padding = '3px 8px';
                        copyBtn.style.border = 'none';
                        copyBtn.style.borderRadius = '3px';
                        copyBtn.style.backgroundColor = '#0366d6';
                        copyBtn.style.color = 'white';
                        copyBtn.style.cursor = 'pointer';
                        
                        copyBtn.addEventListener('click', function(e) {{
                            var code = this.parentElement.querySelector('code');
                            var range = document.createRange();
                            range.selectNode(code);
                            window.getSelection().removeAllRanges();
                            window.getSelection().addRange(range);
                            document.execCommand('copy');
                            window.getSelection().removeAllRanges();
                            
                            this.textContent = '복사됨!';
                            setTimeout(function(btn) {{
                                btn.textContent = '복사';
                            }}, 2000, this);
                        }});
                        
                        pre.appendChild(copyBtn);
                    }}
                }});
                </script>
            </body>
            </html>
            """
            
            # 파일로 저장
            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_template)
                    
                logger.info(f"API 문서가 {output_path}에 저장되었습니다.")
                
            return html_template
            
        except ImportError:
            logger.warning("markdown 패키지가 설치되어 있지 않아 HTML 생성을 건너뜁니다.")
            
            # 패키지가 없어도 기본 HTML 생성
            html_content = f"""<!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{self.title}</title>
            </head>
            <body>
                <h1>{self.title}</h1>
                <p>HTML 문서 생성을 위해 <code>pip install markdown</code>을 실행하여 패키지를 설치하세요.</p>
                <pre>{md_content}</pre>
            </body>
            </html>
            """
            
            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
            return html_content

def generate_api_docs(app: FastAPI, output_dir: str, 
                     title: str = "API 문서", 
                     description: str = "FastAPI 애플리케이션의 API 문서입니다.",
                     formats: List[str] = ["md", "html"],
                     include_code: bool = True,
                     css: Optional[str] = None) -> Dict[str, str]:
    """
    API 문서 생성 유틸리티 함수
    
    Args:
        app (FastAPI): FastAPI 애플리케이션 인스턴스
        output_dir (str): 출력 디렉토리 경로
        title (str): 문서 제목
        description (str): 문서 설명
        formats (List[str]): 생성할 문서 형식 목록 ("md", "html")
        include_code (bool): 핸들러 함수 소스코드 포함 여부
        css (Optional[str]): HTML 문서용 CSS 스타일시트 경로
        
    Returns:
        Dict[str, str]: 형식별 생성된 파일 경로
    """
    generator = APIDocGenerator(app, title, description)
    
    os.makedirs(output_dir, exist_ok=True)
    
    result_files = {}
    filename_base = title.lower().replace(" ", "_")
    
    if "md" in formats:
        md_path = os.path.join(output_dir, f"{filename_base}.md")
        generator.generate_markdown(md_path, include_code)
        result_files["md"] = md_path
        
    if "html" in formats:
        html_path = os.path.join(output_dir, f"{filename_base}.html")
        generator.generate_html(html_path, include_code, css)
        result_files["html"] = html_path
        
    return result_files

# CLI 인터페이스가 필요한 경우 여기에 추가
if __name__ == "__main__":
    import argparse
    import importlib.util
    import sys
    
    parser = argparse.ArgumentParser(description="FastAPI 애플리케이션의 API 문서 생성")
    parser.add_argument("app_path", help="FastAPI 앱 모듈 경로 (예: main:app)")
    parser.add_argument("--output-dir", "-o", default="docs", help="출력 디렉토리 경로")
    parser.add_argument("--title", "-t", default="API 문서", help="문서 제목")
    parser.add_argument("--description", "-d", default="FastAPI 애플리케이션의 API 문서입니다.", help="문서 설명")
    parser.add_argument("--formats", "-f", default="md,html", help="생성할 문서 형식 (쉼표로 구분)")
    parser.add_argument("--include-code", "-c", action="store_true", help="핸들러 함수 소스코드 포함")
    parser.add_argument("--css", help="HTML 문서용 CSS 스타일시트 경로")
    
    args = parser.parse_args()
    
    # FastAPI 앱 모듈 로드
    module_path, app_var = args.app_path.split(":")
    
    if module_path.endswith(".py"):
        module_path = module_path[:-3]
        
    spec = importlib.util.spec_from_file_location(module_path, f"{module_path}.py")
    if not spec or not spec.loader:
        module = importlib.import_module(module_path)
    else:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    
    app = getattr(module, app_var)
    
    formats = args.formats.split(",")
    result_files = generate_api_docs(
        app=app,
        output_dir=args.output_dir,
        title=args.title,
        description=args.description,
        formats=formats,
        include_code=args.include_code,
        css=args.css
    )
    
    print(f"API 문서 생성 완료:")
    for fmt, path in result_files.items():
        print(f"- {fmt.upper()}: {path}") 