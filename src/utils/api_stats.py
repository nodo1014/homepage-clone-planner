"""
API 사용량 통계 시각화 유틸리티

이 모듈은 API 사용량 모니터링 데이터를 시각화하는 CLI 도구를 제공합니다.
"""
import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from tabulate import tabulate
import json
import logging
from pathlib import Path

# API 모니터링 모듈 가져오기
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.api.api_monitor import get_api_monitor, ApiMonitor

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_api_usage_stats(api_name: Optional[str] = None) -> Dict[str, Any]:
    """
    API 사용량 통계를 가져옵니다.
    
    Args:
        api_name (Optional[str]): 특정 API 이름 (None이면 전체)
        
    Returns:
        Dict[str, Any]: 사용량 통계
    """
    monitor = get_api_monitor()
    return await monitor.get_usage_stats(api_name)


def format_cost(cost: float) -> str:
    """
    비용을 보기 좋게 형식화합니다.
    
    Args:
        cost (float): 비용 값
        
    Returns:
        str: 형식화된 비용 문자열
    """
    if cost < 0.01:
        return f"${cost:.6f}"
    elif cost < 1.0:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"


def format_number(num: int) -> str:
    """
    숫자를 읽기 쉬운 형식으로 변환합니다.
    
    Args:
        num (int): 숫자
        
    Returns:
        str: 형식화된 숫자 문자열
    """
    return f"{num:,}"


def display_api_summary(stats: Dict[str, Any]) -> None:
    """
    API 사용량 요약을 표시합니다.
    
    Args:
        stats (Dict[str, Any]): API 사용량 통계
    """
    if "_summary" not in stats:
        print("전체 사용량 요약 정보가 없습니다.")
        return
    
    summary = stats["_summary"]
    print("\n=== 전체 API 사용량 요약 ===")
    print(f"총 API 호출 수: {format_number(summary['total_calls'])}")
    print(f"성공: {format_number(summary['success_count'])} ({summary['success_rate']:.1f}%)")
    print(f"오류: {format_number(summary['error_count'])}")
    print(f"총 비용: {format_cost(summary['total_cost'])}")
    print("")


def display_api_details(stats: Dict[str, Any]) -> None:
    """
    각 API별 상세 사용량을 표시합니다.
    
    Args:
        stats (Dict[str, Any]): API 사용량 통계
    """
    # 요약 정보는 제외
    if "_summary" in stats:
        del stats["_summary"]
    
    if not stats:
        print("API 사용량 정보가 없습니다.")
        return
    
    print("\n=== API별 사용량 상세 정보 ===")
    
    for api_name, api_stats in stats.items():
        print(f"\n## {api_name.upper()} API")
        print(f"총 호출 수: {format_number(api_stats['total_calls'])}")
        print(f"성공률: {api_stats['success_rate']:.1f}%")
        print(f"총 비용: {format_cost(api_stats['total_cost'])}")
        
        # 오늘 사용량
        today = api_stats.get("today", {})
        print(f"오늘 호출 수: {format_number(today.get('calls', 0))}")
        print(f"오늘 비용: {format_cost(today.get('cost', 0.0))}")
        
        # 이번 달 사용량
        this_month = api_stats.get("this_month", {})
        print(f"이번 달 호출 수: {format_number(this_month.get('calls', 0))}")
        print(f"이번 달 비용: {format_cost(this_month.get('cost', 0.0))}")
        
        # 예산 정보
        budget = this_month.get("budget", None)
        if budget:
            budget_percent = this_month.get("budget_used_percent", 0)
            print(f"월 예산: {format_cost(budget)} (사용: {budget_percent:.1f}%)")
        
        # 제한 정보
        limits = api_stats.get("limits", {})
        print("\n제한 설정:")
        for limit_type, limit_value in limits.items():
            if limit_value is not None:
                print(f"  - {limit_type}: {format_number(limit_value)}")
        
        # 토큰 정보 (해당하는 경우)
        tokens = api_stats.get("tokens", None)
        if tokens and isinstance(tokens, dict):
            print("\n토큰 사용량:")
            for token_type, token_count in tokens.items():
                print(f"  - {token_type}: {format_number(token_count)}")
        
        # 마지막 업데이트 시간
        last_updated = api_stats.get("last_updated", "")
        if last_updated:
            try:
                # ISO 형식 날짜를 datetime으로 파싱
                update_time = datetime.fromisoformat(last_updated)
                print(f"\n마지막 업데이트: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, TypeError):
                print(f"\n마지막 업데이트: {last_updated}")


def generate_usage_table(stats: Dict[str, Any]) -> List[List[str]]:
    """
    API 사용량 테이블을 생성합니다.
    
    Args:
        stats (Dict[str, Any]): API 사용량 통계
        
    Returns:
        List[List[str]]: 테이블 형식의 데이터
    """
    # 요약 정보는 제외
    table_data = []
    headers = ["API", "총 호출", "성공률", "오늘 호출", "이번 달 호출", "총 비용", "월 예산", "예산 사용"]
    
    for api_name, api_stats in stats.items():
        if api_name == "_summary":
            continue
        
        today = api_stats.get("today", {})
        this_month = api_stats.get("this_month", {})
        
        row = [
            api_name.upper(),
            format_number(api_stats['total_calls']),
            f"{api_stats['success_rate']:.1f}%",
            format_number(today.get('calls', 0)),
            format_number(this_month.get('calls', 0)),
            format_cost(api_stats['total_cost']),
            format_cost(this_month.get('budget', 0)) if this_month.get('budget') else "없음",
            f"{this_month.get('budget_used_percent', 0):.1f}%" if this_month.get('budget') else "N/A"
        ]
        
        table_data.append(row)
    
    return [headers] + table_data


def display_usage_table(stats: Dict[str, Any]) -> None:
    """
    API 사용량을 테이블 형식으로 표시합니다.
    
    Args:
        stats (Dict[str, Any]): API 사용량 통계
    """
    # 요약 정보만 있는 경우 건너뜀
    if len(stats) <= 1 and "_summary" in stats:
        print("API 사용량 정보가 없습니다.")
        return
    
    # 테이블 데이터 생성
    table_data = generate_usage_table(stats)
    
    if len(table_data) <= 1:  # 헤더만 있는 경우
        print("API 사용량 정보가 없습니다.")
        return
    
    # 테이블 표시
    headers = table_data[0]
    rows = table_data[1:]
    print("\n" + tabulate(rows, headers=headers, tablefmt="grid"))


def export_stats_to_json(stats: Dict[str, Any], output_file: str) -> None:
    """
    API 사용량 통계를 JSON 파일로 내보냅니다.
    
    Args:
        stats (Dict[str, Any]): API 사용량 통계
        output_file (str): 출력 파일 경로
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\nAPI 사용량 통계가 {output_file}에 저장되었습니다.")
    except Exception as e:
        print(f"\n오류: 파일 저장 실패 - {str(e)}")


async def main():
    """CLI 도구의 메인 함수"""
    parser = argparse.ArgumentParser(description='API 사용량 통계 조회 도구')
    parser.add_argument('--api', help='조회할 특정 API 이름')
    parser.add_argument('--format', choices=['text', 'table', 'json'], default='table',
                      help='출력 형식 (text, table, json)')
    parser.add_argument('--output', help='통계 내보내기 파일 경로')
    parser.add_argument('--clear', action='store_true', help='API 사용량 데이터 초기화')
    parser.add_argument('--prune', type=int, help='N일보다 오래된 데이터 정리')
    
    args = parser.parse_args()
    
    # API 모니터 인스턴스 가져오기
    monitor = get_api_monitor()
    
    # 데이터 초기화
    if args.clear:
        await monitor.clear_usage_data(args.api)
        print(f"API 사용량 데이터가 초기화되었습니다." + 
              (f" ({args.api})" if args.api else ""))
        return
    
    # 오래된 데이터 정리
    if args.prune:
        await monitor.prune_old_data(older_than_days=args.prune)
        print(f"{args.prune}일보다 오래된 데이터가 정리되었습니다.")
        return
    
    # 사용량 통계 가져오기
    stats = await get_api_usage_stats(args.api)
    
    # 출력 형식에 따라 표시
    if args.format == 'text':
        display_api_summary(stats)
        display_api_details(stats)
    elif args.format == 'table':
        if "_summary" in stats:
            summary = stats["_summary"]
            print(f"\n총 API 호출: {format_number(summary['total_calls'])} "
                 f"(성공률: {summary['success_rate']:.1f}%, "
                 f"총 비용: {format_cost(summary['total_cost'])})")
        display_usage_table(stats)
    elif args.format == 'json':
        print(json.dumps(stats, indent=2))
    
    # 파일로 내보내기
    if args.output:
        export_stats_to_json(stats, args.output)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n작업이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc() 