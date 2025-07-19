"""A/B 테스트 서비스"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models import User, UserActivityLog


class ABTestingService:
    """A/B 테스트 관리 및 실행 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 활성 실험 정의
        self.active_experiments = {
            "recommendation_algorithm": {
                "name": "추천 알고리즘 비교",
                "description": "기존 태그 기반 vs 개인화 하이브리드 알고리즘",
                "variants": {
                    "control": {
                        "name": "기존 태그 기반",
                        "weight": 0.5
                    },
                    "treatment": {
                        "name": "개인화 하이브리드",
                        "weight": 0.5
                    }
                },
                "metrics": ["click_rate", "conversion_rate", "engagement_time"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            "ui_personalization": {
                "name": "UI 개인화 테스트",
                "description": "정적 UI vs 동적 개인화 UI",
                "variants": {
                    "control": {
                        "name": "정적 UI",
                        "weight": 0.7
                    },
                    "treatment": {
                        "name": "동적 개인화 UI",
                        "weight": 0.3
                    }
                },
                "metrics": ["session_duration", "pages_per_session", "bounce_rate"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            "exploration_level": {
                "name": "탐색 수준 최적화",
                "description": "추천의 다양성 수준 테스트",
                "variants": {
                    "low": {
                        "name": "낮은 탐색 (10%)",
                        "weight": 0.33,
                        "params": {"exploration_factor": 0.1}
                    },
                    "medium": {
                        "name": "중간 탐색 (30%)",
                        "weight": 0.34,
                        "params": {"exploration_factor": 0.3}
                    },
                    "high": {
                        "name": "높은 탐색 (50%)",
                        "weight": 0.33,
                        "params": {"exploration_factor": 0.5}
                    }
                },
                "metrics": ["discovery_rate", "satisfaction_score", "return_rate"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        }
    
    def get_user_variant(
        self, 
        user_id: UUID, 
        experiment_name: str
    ) -> Optional[Dict[str, Any]]:
        """사용자의 실험 변형 할당"""
        
        experiment = self.active_experiments.get(experiment_name)
        if not experiment:
            return None
        
        # 실험 기간 확인
        if not self._is_experiment_active(experiment):
            return None
        
        # 사용자 ID와 실험 이름을 조합하여 일관된 할당
        hash_input = f"{user_id}:{experiment_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        normalized_value = (hash_value % 10000) / 10000.0
        
        # 가중치에 따라 변형 할당
        cumulative_weight = 0.0
        for variant_key, variant_data in experiment["variants"].items():
            cumulative_weight += variant_data["weight"]
            if normalized_value <= cumulative_weight:
                return {
                    "experiment": experiment_name,
                    "variant": variant_key,
                    "variant_data": variant_data,
                    "assigned_at": datetime.now().isoformat()
                }
        
        # 기본값 (발생하지 않아야 함)
        return {
            "experiment": experiment_name,
            "variant": "control",
            "variant_data": experiment["variants"]["control"],
            "assigned_at": datetime.now().isoformat()
        }
    
    def _is_experiment_active(self, experiment: Dict[str, Any]) -> bool:
        """실험 활성 상태 확인"""
        
        try:
            start_date = datetime.strptime(experiment["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(experiment["end_date"], "%Y-%m-%d")
            current_date = datetime.now()
            
            return start_date <= current_date <= end_date
        except:
            return True  # 날짜 파싱 실패 시 활성으로 간주
    
    async def track_experiment_event(
        self,
        user_id: UUID,
        experiment_name: str,
        variant: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """실험 이벤트 추적"""
        
        # UserActivityLog를 활용하여 실험 이벤트 기록
        activity_data = {
            "experiment": experiment_name,
            "variant": variant,
            "event_type": event_type,
            "event_data": event_data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        activity_log = UserActivityLog(
            user_id=user_id,
            activity_type=f"experiment_{event_type}",
            activity_data=activity_data
        )
        
        self.db.add(activity_log)
        self.db.commit()
    
    def get_experiment_results(
        self,
        experiment_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """실험 결과 집계"""
        
        experiment = self.active_experiments.get(experiment_name)
        if not experiment:
            return {"error": "Experiment not found"}
        
        # 기간 설정
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # 변형별 결과 집계
        results = {
            "experiment": experiment_name,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "variants": {}
        }
        
        for variant_key in experiment["variants"].keys():
            # 해당 변형의 사용자 수
            variant_users = self.db.query(
                func.count(func.distinct(UserActivityLog.user_id))
            ).filter(
                and_(
                    UserActivityLog.activity_type.like("experiment_%"),
                    UserActivityLog.activity_data["experiment"].astext == experiment_name,
                    UserActivityLog.activity_data["variant"].astext == variant_key,
                    UserActivityLog.created_at >= start_date,
                    UserActivityLog.created_at <= end_date
                )
            ).scalar()
            
            # 메트릭별 결과 계산
            metrics = {}
            for metric in experiment["metrics"]:
                metric_value = self._calculate_metric(
                    experiment_name, variant_key, metric, start_date, end_date
                )
                metrics[metric] = metric_value
            
            results["variants"][variant_key] = {
                "users": variant_users or 0,
                "metrics": metrics
            }
        
        # 통계적 유의성 계산
        results["statistical_significance"] = self._calculate_significance(results)
        
        return results
    
    def _calculate_metric(
        self,
        experiment_name: str,
        variant: str,
        metric: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """특정 메트릭 계산"""
        
        # 기본 쿼리
        base_query = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.activity_data["experiment"].astext == experiment_name,
                UserActivityLog.activity_data["variant"].astext == variant,
                UserActivityLog.created_at >= start_date,
                UserActivityLog.created_at <= end_date
            )
        )
        
        if metric == "click_rate":
            # 클릭률 계산
            views = base_query.filter(
                UserActivityLog.activity_type == "experiment_recommendation_viewed"
            ).count()
            
            clicks = base_query.filter(
                UserActivityLog.activity_type == "experiment_recommendation_clicked"
            ).count()
            
            rate = (clicks / views * 100) if views > 0 else 0
            
            return {
                "value": round(rate, 2),
                "views": views,
                "clicks": clicks,
                "unit": "%"
            }
        
        elif metric == "conversion_rate":
            # 전환율 계산 (추천 -> 계획 생성)
            recommendations = base_query.filter(
                UserActivityLog.activity_type == "experiment_recommendation_viewed"
            ).count()
            
            conversions = base_query.filter(
                UserActivityLog.activity_type == "experiment_plan_created"
            ).count()
            
            rate = (conversions / recommendations * 100) if recommendations > 0 else 0
            
            return {
                "value": round(rate, 2),
                "recommendations": recommendations,
                "conversions": conversions,
                "unit": "%"
            }
        
        elif metric == "engagement_time":
            # 평균 체류 시간
            engagement_logs = base_query.filter(
                UserActivityLog.activity_type == "page_view",
                UserActivityLog.activity_data.has_key("duration")
            ).all()
            
            if engagement_logs:
                total_duration = sum(
                    log.activity_data.get("duration", 0) 
                    for log in engagement_logs
                )
                avg_duration = total_duration / len(engagement_logs)
                
                return {
                    "value": round(avg_duration, 2),
                    "count": len(engagement_logs),
                    "unit": "seconds"
                }
            
            return {"value": 0, "count": 0, "unit": "seconds"}
        
        elif metric == "discovery_rate":
            # 새로운 카테고리 발견율
            unique_categories = base_query.filter(
                UserActivityLog.activity_type == "destination_view"
            ).distinct(
                UserActivityLog.activity_data["category"].astext
            ).count()
            
            total_views = base_query.filter(
                UserActivityLog.activity_type == "destination_view"
            ).count()
            
            rate = (unique_categories / total_views * 100) if total_views > 0 else 0
            
            return {
                "value": round(rate, 2),
                "unique_categories": unique_categories,
                "total_views": total_views,
                "unit": "%"
            }
        
        else:
            return {"value": 0, "unit": "unknown"}
    
    def _calculate_significance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """통계적 유의성 계산 (간단한 버전)"""
        
        variants = results["variants"]
        if len(variants) != 2:
            return {"significant": False, "message": "두 개의 변형만 비교 가능"}
        
        # Control과 Treatment 찾기
        control_key = None
        treatment_key = None
        
        for key in variants:
            if "control" in key.lower():
                control_key = key
            else:
                treatment_key = key
        
        if not control_key or not treatment_key:
            return {"significant": False, "message": "Control/Treatment 구분 불가"}
        
        # 주요 메트릭에 대한 유의성 검정 (간단한 비율 차이)
        significance_results = {}
        
        for metric in results["experiment"]["metrics"]:
            control_value = variants[control_key]["metrics"].get(metric, {}).get("value", 0)
            treatment_value = variants[treatment_key]["metrics"].get(metric, {}).get("value", 0)
            
            if control_value > 0:
                improvement = ((treatment_value - control_value) / control_value) * 100
                
                # 간단한 규칙: 10% 이상 개선이면 유의미
                is_significant = abs(improvement) >= 10
                
                significance_results[metric] = {
                    "control": control_value,
                    "treatment": treatment_value,
                    "improvement": round(improvement, 2),
                    "significant": is_significant
                }
        
        return significance_results
    
    def get_user_experiments(self, user_id: UUID) -> List[Dict[str, Any]]:
        """사용자가 참여 중인 실험 목록"""
        
        user_experiments = []
        
        for exp_name, exp_data in self.active_experiments.items():
            variant = self.get_user_variant(user_id, exp_name)
            if variant:
                user_experiments.append({
                    "experiment": exp_name,
                    "name": exp_data["name"],
                    "variant": variant["variant"],
                    "variant_name": variant["variant_data"]["name"]
                })
        
        return user_experiments


# 싱글톤 패턴
_ab_service_instances = {}

def get_ab_testing_service(db: Session) -> ABTestingService:
    """ABTestingService 인스턴스 가져오기"""
    
    session_id = id(db)
    if session_id not in _ab_service_instances:
        _ab_service_instances[session_id] = ABTestingService(db)
    
    return _ab_service_instances[session_id]