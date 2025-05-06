"""
내보내기 기능 예제

이 스크립트는 다양한 형식으로 내보내기 기능을 시연합니다.
"""
import sys
import os
import asyncio
from pathlib import Path
import json
from pprint import pprint

# 상위 경로를 라이브러리 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.export.export_manager import ExportManager, export_content, markdown_to_html


def create_sample_content():
    """예제용 샘플 콘텐츠 생성"""
    return {
        "title": "샘플 기획서: 커뮤니티 웹사이트 클론",
        "website": {
            "name": "커뮤니티 허브",
            "url": "https://example.com",
            "description": "다양한 주제에 관한 토론과 정보 공유를 위한 커뮤니티 플랫폼"
        },
        "overview": """
이 기획서는 인기 커뮤니티 웹사이트의 주요 기능과 디자인 요소를 분석하고, 
이를 기반으로 한 클론 웹사이트 개발 방향을 제시합니다. 
사용자 경험을 중심으로 핵심 기능을 구현하며, 
모던한 디자인과 반응형 레이아웃을 적용할 것을 제안합니다.
        """,
        "design_analysis": {
            "color_palette": [
                "#1A73E8 (주요 브랜드 색상)",
                "#4285F4 (보조 색상)",
                "#34A853 (성공/긍정 표시)",
                "#FBBC05 (경고/주의 표시)",
                "#EA4335 (오류/부정 표시)",
                "#F8F9FA (배경 색상)",
                "#202124 (텍스트 주요 색상)"
            ],
            "typography": """
- 제목: Roboto Bold, 18-24px
- 본문: Roboto Regular, 14-16px
- 버튼: Roboto Medium, 14px
- 캡션: Roboto Light, 12px
            """,
            "layout": """
전체적으로 그리드 기반 레이아웃을 사용하며, 데스크톱에서는 3단 구조,
태블릿에서는 2단 구조, 모바일에서는 1단 구조로 반응형 디자인을 적용합니다.
헤더는 고정되어 있으며, 사이드바는 토글 가능한 형태로 구현됩니다.
            """
        },
        "functional_analysis": {
            "key_features": [
                "사용자 계정 관리 (가입, 로그인, 프로필)",
                "게시물 작성 및 관리 (텍스트, 이미지, 링크)",
                "댓글 및 대댓글",
                "카테고리별 게시판",
                "인기 게시물 추천 알고리즘",
                "실시간 알림",
                "검색 기능",
                "사용자 간 메시지"
            ],
            "user_interactions": """
사용자는 계정 생성 후 로그인하여 게시물을 작성하거나 다른 사용자의 게시물에 반응할 수 있습니다.
게시물에 대한 댓글, 추천, 공유 기능을 통해 커뮤니티 활동이 촉진됩니다.
관심 주제를 팔로우하여 맞춤형 피드를 구성할 수 있습니다.
            """
        },
        "page_structure": [
            {
                "name": "메인 페이지",
                "description": "사용자 맞춤형 피드와 인기 게시물을 표시",
                "components": [
                    "헤더 (로고, 검색, 사용자 메뉴)",
                    "사이드바 (카테고리, 태그 목록)",
                    "메인 콘텐츠 (게시물 목록)",
                    "트렌딩 섹션 (인기 주제)"
                ]
            },
            {
                "name": "게시물 상세 페이지",
                "description": "게시물 내용과 댓글을 표시",
                "components": [
                    "게시물 콘텐츠",
                    "작성자 정보",
                    "추천/비추천 버튼",
                    "댓글 섹션",
                    "관련 게시물"
                ]
            },
            {
                "name": "사용자 프로필 페이지",
                "description": "사용자 정보와 활동 내역 표시",
                "components": [
                    "프로필 정보 (이미지, 이름, 소개)",
                    "게시물 목록",
                    "댓글 활동",
                    "팔로잉/팔로워"
                ]
            }
        ],
        "tech_stack": [
            "프론트엔드: React, TypeScript, Styled Components",
            "백엔드: Node.js, Express, MongoDB",
            "인증: JWT, OAuth 2.0",
            "배포: Docker, AWS",
            "CI/CD: GitHub Actions",
            "모니터링: Sentry, Google Analytics"
        ],
        "development_recommendations": """
1. 모바일 우선 접근법으로 반응형 설계를 우선시합니다.
2. 컴포넌트 기반 아키텍처를 사용하여 재사용성을 높입니다.
3. SSR(Server-Side Rendering)을 적용하여 초기 로딩 성능과 SEO를 개선합니다.
4. 점진적 향상 기법을 사용하여 다양한 브라우저 환경을 지원합니다.
5. 접근성 가이드라인(WCAG)을 준수하여 모든 사용자가 이용할 수 있도록 합니다.
6. 데이터 캐싱 및 지연 로딩을 통해 성능을 최적화합니다.
7. 사용자 테스트를 통해 UX를 지속적으로 개선합니다.
        """,
        "conclusion": """
이 기획서에서 분석한 디자인과 기능을 바탕으로 현대적이고 사용자 친화적인 커뮤니티 웹사이트를 구현할 수 있습니다.
핵심 기능을 우선적으로 개발하고, 사용자 피드백을 바탕으로 추가 기능을 점진적으로 도입하는 전략이 효과적일 것입니다.
확장성과 유지보수성을 고려한 아키텍처 설계가 장기적으로 성공의 열쇠가 될 것입니다.
        """
    }


async def run_examples():
    """다양한 내보내기 기능 예제 실행"""
    print("=== 내보내기 기능 예제 시작 ===")
    
    # 샘플 콘텐츠 생성
    content = create_sample_content()
    
    # 출력 디렉터리 설정
    output_dir = Path.cwd() / "export_results"
    output_dir.mkdir(exist_ok=True)
    print(f"출력 디렉터리: {output_dir}\n")
    
    # ExportManager 인스턴스 생성
    export_manager = ExportManager(output_dir=output_dir)
    
    # 마크다운으로 내보내기
    print("1. 마크다운으로 내보내기...")
    md_path = export_manager.export_to_format(
        content=content,
        format_type='md',
        filename="커뮤니티_기획서"
    )
    print(f"   마크다운 파일 생성됨: {md_path}")
    
    # HTML로 내보내기
    print("\n2. HTML로 내보내기...")
    html_path = export_manager.export_to_format(
        content=content,
        format_type='html',
        filename="커뮤니티_기획서"
    )
    print(f"   HTML 파일 생성됨: {html_path}")
    
    # PowerPoint로 내보내기
    print("\n3. PowerPoint로 내보내기...")
    pptx_path = export_manager.export_to_format(
        content=content,
        format_type='pptx',
        filename="커뮤니티_기획서"
    )
    print(f"   PowerPoint 파일 생성됨: {pptx_path}")
    
    # JSON으로 내보내기
    print("\n4. JSON으로 내보내기...")
    json_path = export_manager.export_to_format(
        content=content,
        format_type='json',
        filename="커뮤니티_기획서"
    )
    print(f"   JSON 파일 생성됨: {json_path}")
    
    # ZIP으로 내보내기 (여러 형식 포함)
    print("\n5. ZIP으로 내보내기 (여러 형식 포함)...")
    zip_path = export_manager.export_to_format(
        content=content,
        format_type='zip',
        filename="커뮤니티_기획서",
        include_formats=['md', 'html', 'pptx', 'json']
    )
    print(f"   ZIP 파일 생성됨: {zip_path}")
    
    # 유틸리티 함수 사용 예: 여러 형식으로 한 번에 내보내기
    print("\n6. 유틸리티 함수를 사용하여 한 번에 여러 형식으로 내보내기...")
    result = export_content(
        content=content,
        formats=['md', 'html', 'pptx'],
        output_dir=output_dir,
        filename="유틸리티_함수_테스트"
    )
    print("   내보내기 결과:")
    for fmt, path in result.items():
        print(f"   - {fmt}: {path}")
    
    # 마크다운을 HTML로 변환 유틸리티 함수 예제
    print("\n7. 기존 마크다운 파일을 HTML로 변환...")
    html_from_md_path = markdown_to_html(
        markdown_path=md_path,
        output_path=output_dir / "마크다운에서_변환.html"
    )
    print(f"   변환된 HTML 파일: {html_from_md_path}")
    
    print("\n모든 내보내기 예제가 완료되었습니다.")
    print(f"결과물은 {output_dir} 디렉터리에 저장되었습니다.")


if __name__ == "__main__":
    asyncio.run(run_examples()) 