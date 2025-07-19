"""추천 시스템 평가 메트릭"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from uuid import UUID

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models import (
    User, UserActivityLog, Review, 
    RecommendLike, TravelPlan, TravelPlanDestination
)


class RecommendationMetrics:
    """추천 시스템 성능 평가 메트릭"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_user_metrics(
        self, 
        user_id: UUID,
        period_days: int = 30
    ) -> Dict[str, float]:
        """개별 사용자의 추천 성능 메트릭 계산"""
        
        start_date = datetime.now() - timedelta(days=period_days)
        
        metrics = {
            "precision": self._calculate_precision(user_id, start_date),
            "recall": self._calculate_recall(user_id, start_date),
            "click_through_rate": self._calculate_ctr(user_id, start_date),
            "conversion_rate": self._calculate_conversion_rate(user_id, start_date),
            "diversity_score": self._calculate_diversity(user_id, start_date),
            "novelty_score": self._calculate_novelty(user_id, start_date),
            "satisfaction_score": self._calculate_satisfaction(user_id, start_date),
            "engagement_score": self._calculate_engagement(user_id, start_date)
        }
        
        # F1 Score 계산
        if metrics["precision"] > 0 and metrics["recall"] > 0:
            metrics["f1_score"] = 2 * (metrics["precision"] * metrics["recall"]) / (metrics["precision"] + metrics["recall"])
        else:
            metrics["f1_score"] = 0.0
        
        return metrics
    
    def _calculate_precision(self, user_id: UUID, start_date: datetime) -> float:
        """정밀도: 추천된 항목 중 실제로 상호작용한 비율"""
        
        # 추천된 항목 조회
        recommended_items = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_viewed",
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        if not recommended_items:
            return 0.0
        
        recommended_ids = set()
        for log in recommended_items:
            if "recommendations" in log.activity_data:
                for rec in log.activity_data["recommendations"]:
                    recommended_ids.add(rec.get("id"))
        
        # 상호작용한 항목 조회
        interacted_items = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type.in_([
                    "destination_view", "like_added", "bookmark_added"
                ]),
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        interacted_ids = set()
        for log in interacted_items:
            dest_id = log.activity_data.get("destination_id")
            if dest_id:
                interacted_ids.add(dest_id)
        
        # 교집합 계산
        relevant_recommended = recommended_ids & interacted_ids
        
        return len(relevant_recommended) / len(recommended_ids) if recommended_ids else 0.0
    
    def _calculate_recall(self, user_id: UUID, start_date: datetime) -> float:
        """재현율: 사용자가 상호작용한 항목 중 추천된 비율"""
        
        # 상호작용한 항목 조회
        interacted_items = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type.in_([
                    "destination_view", "like_added", "bookmark_added"
                ]),
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        if not interacted_items:
            return 0.0
        
        interacted_ids = set()
        for log in interacted_items:
            dest_id = log.activity_data.get("destination_id")
            if dest_id:
                interacted_ids.add(dest_id)
        
        # 추천된 항목 조회
        recommended_items = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_viewed",
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        recommended_ids = set()
        for log in recommended_items:
            if "recommendations" in log.activity_data:
                for rec in log.activity_data["recommendations"]:
                    recommended_ids.add(rec.get("id"))
        
        # 교집합 계산
        relevant_recommended = recommended_ids & interacted_ids
        
        return len(relevant_recommended) / len(interacted_ids) if interacted_ids else 0.0
    
    def _calculate_ctr(self, user_id: UUID, start_date: datetime) -> float:
        """클릭률: 추천 노출 대비 클릭 비율"""
        
        # 추천 노출 수
        impressions = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_viewed",
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        # 추천 클릭 수
        clicks = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_clicked",
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        return (clicks / impressions) if impressions > 0 else 0.0
    
    def _calculate_conversion_rate(self, user_id: UUID, start_date: datetime) -> float:
        """전환율: 추천 클릭 후 실제 행동(계획 생성, 예약 등)으로 이어진 비율"""
        
        # 추천 클릭 수
        clicks = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_clicked",
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        # 전환 행동 수 (계획 생성, 리뷰 작성 등)
        conversions = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type.in_([
                    "plan_created", "review_created", "booking_completed"
                ]),
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        return (conversions / clicks) if clicks > 0 else 0.0
    
    def _calculate_diversity(self, user_id: UUID, start_date: datetime) -> float:
        """다양성: 추천된 항목의 카테고리/태그 다양성"""
        
        # 추천된 항목들의 태그 수집
        recommended_items = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_viewed",
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        all_tags = []
        for log in recommended_items:
            if "recommendations" in log.activity_data:
                for rec in log.activity_data["recommendations"]:
                    tags = rec.get("tags", [])
                    all_tags.extend(tags)
        
        if not all_tags:
            return 0.0
        
        # 태그 분포의 엔트로피 계산
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        total_tags = len(all_tags)
        entropy = 0.0
        
        for count in tag_counts.values():
            p = count / total_tags
            if p > 0:
                entropy -= p * np.log2(p)
        
        # 정규화 (0-1 범위)
        max_entropy = np.log2(len(tag_counts)) if len(tag_counts) > 1 else 1
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0
        
        return diversity_score
    
    def _calculate_novelty(self, user_id: UUID, start_date: datetime) -> float:
        """참신성: 사용자가 이전에 보지 않은 새로운 항목의 비율"""
        
        # 이전에 본 항목들
        historical_views = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "destination_view",
                UserActivityLog.created_at < start_date
            )
        ).all()
        
        historical_ids = set()
        for log in historical_views:
            dest_id = log.activity_data.get("destination_id")
            if dest_id:
                historical_ids.add(dest_id)
        
        # 최근 추천된 항목들
        recent_recommendations = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "recommendation_viewed",
                UserActivityLog.created_at >= start_date
            )
        ).all()
        
        recommended_ids = []
        for log in recent_recommendations:
            if "recommendations" in log.activity_data:
                for rec in log.activity_data["recommendations"]:
                    recommended_ids.append(rec.get("id"))
        
        if not recommended_ids:
            return 0.0
        
        # 새로운 항목의 비율
        novel_items = [item_id for item_id in recommended_ids if item_id not in historical_ids]
        
        return len(novel_items) / len(recommended_ids)
    
    def _calculate_satisfaction(self, user_id: UUID, start_date: datetime) -> float:
        """만족도: 리뷰 평점, 좋아요 등을 기반으로 한 만족도"""
        
        # 평균 리뷰 평점
        avg_rating = self.db.query(func.avg(Review.rating)).filter(
            and_(
                Review.user_id == user_id,
                Review.created_at >= start_date
            )
        ).scalar() or 0.0
        
        # 좋아요 비율
        total_views = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "destination_view",
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        likes = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "like_added",
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        like_rate = (likes / total_views) if total_views > 0 else 0.0
        
        # 만족도 점수 계산 (평점 50%, 좋아요율 50%)
        satisfaction = (avg_rating / 5.0) * 0.5 + like_rate * 0.5
        
        return satisfaction
    
    def _calculate_engagement(self, user_id: UUID, start_date: datetime) -> float:
        """참여도: 사용자의 전반적인 참여 수준"""
        
        # 총 활동 수
        total_activities = self.db.query(func.count(UserActivityLog.log_id)).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        # 활동 다양성 (서로 다른 활동 유형 수)
        unique_activities = self.db.query(
            func.count(func.distinct(UserActivityLog.activity_type))
        ).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= start_date
            )
        ).scalar() or 0
        
        # 평균 세션 시간
        page_views = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_type == "page_view",
                UserActivityLog.created_at >= start_date,
                UserActivityLog.activity_data.has_key("duration")
            )
        ).all()
        
        avg_duration = 0.0
        if page_views:
            total_duration = sum(
                log.activity_data.get("duration", 0) 
                for log in page_views
            )
            avg_duration = total_duration / len(page_views)
        
        # 정규화된 참여도 점수
        activity_score = min(total_activities / 100, 1.0)  # 100개 활동을 최대로
        diversity_score = min(unique_activities / 10, 1.0)  # 10가지 활동을 최대로
        duration_score = min(avg_duration / 300, 1.0)  # 5분을 최대로
        
        engagement = (activity_score + diversity_score + duration_score) / 3
        
        return engagement
    
    def calculate_system_metrics(self, period_days: int = 30) -> Dict[str, float]:
        """전체 시스템의 추천 성능 메트릭"""
        
        start_date = datetime.now() - timedelta(days=period_days)
        
        # 활성 사용자 조회
        active_users = self.db.query(func.distinct(UserActivityLog.user_id)).filter(
            UserActivityLog.created_at >= start_date
        ).all()
        
        if not active_users:
            return {
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1_score": 0.0,
                "avg_ctr": 0.0,
                "avg_conversion_rate": 0.0,
                "avg_diversity": 0.0,
                "avg_novelty": 0.0,
                "avg_satisfaction": 0.0,
                "avg_engagement": 0.0,
                "active_users": 0
            }
        
        # 각 사용자의 메트릭 계산 및 평균
        all_metrics = []
        for (user_id,) in active_users:
            user_metrics = self.calculate_user_metrics(user_id, period_days)
            all_metrics.append(user_metrics)
        
        # 평균 계산
        avg_metrics = {}
        metric_names = all_metrics[0].keys() if all_metrics else []
        
        for metric in metric_names:
            values = [m[metric] for m in all_metrics if m[metric] is not None]
            avg_metrics[f"avg_{metric}"] = np.mean(values) if values else 0.0
        
        avg_metrics["active_users"] = len(active_users)
        
        return avg_metrics
    
    def get_recommendation_report(
        self,
        user_id: Optional[UUID] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """추천 시스템 성능 리포트 생성"""
        
        if user_id:
            # 개별 사용자 리포트
            metrics = self.calculate_user_metrics(user_id, period_days)
            
            return {
                "type": "user",
                "user_id": str(user_id),
                "period_days": period_days,
                "metrics": metrics,
                "interpretation": self._interpret_metrics(metrics),
                "recommendations": self._get_improvement_suggestions(metrics)
            }
        else:
            # 시스템 전체 리포트
            metrics = self.calculate_system_metrics(period_days)
            
            return {
                "type": "system",
                "period_days": period_days,
                "metrics": metrics,
                "interpretation": self._interpret_system_metrics(metrics),
                "recommendations": self._get_system_improvement_suggestions(metrics)
            }
    
    def _interpret_metrics(self, metrics: Dict[str, float]) -> Dict[str, str]:
        """메트릭 해석"""
        
        interpretations = {}
        
        # Precision 해석
        if metrics["precision"] >= 0.5:
            interpretations["precision"] = "높음: 추천의 정확도가 우수합니다."
        elif metrics["precision"] >= 0.3:
            interpretations["precision"] = "보통: 추천의 정확도가 적절합니다."
        else:
            interpretations["precision"] = "낮음: 추천의 정확도 개선이 필요합니다."
        
        # Diversity 해석
        if metrics["diversity_score"] >= 0.7:
            interpretations["diversity"] = "높음: 다양한 추천을 제공하고 있습니다."
        elif metrics["diversity_score"] >= 0.4:
            interpretations["diversity"] = "보통: 적절한 수준의 다양성을 유지하고 있습니다."
        else:
            interpretations["diversity"] = "낮음: 추천의 다양성을 높일 필요가 있습니다."
        
        # Engagement 해석
        if metrics["engagement_score"] >= 0.6:
            interpretations["engagement"] = "높음: 사용자가 활발히 참여하고 있습니다."
        elif metrics["engagement_score"] >= 0.3:
            interpretations["engagement"] = "보통: 일반적인 수준의 참여도를 보이고 있습니다."
        else:
            interpretations["engagement"] = "낮음: 사용자 참여를 유도할 방안이 필요합니다."
        
        return interpretations
    
    def _interpret_system_metrics(self, metrics: Dict[str, float]) -> Dict[str, str]:
        """시스템 메트릭 해석"""
        
        interpretations = {}
        
        # 전반적인 성능
        avg_f1 = metrics.get("avg_f1_score", 0)
        if avg_f1 >= 0.5:
            interpretations["overall"] = "우수: 추천 시스템이 효과적으로 작동하고 있습니다."
        elif avg_f1 >= 0.3:
            interpretations["overall"] = "양호: 추천 시스템이 적절히 작동하지만 개선 여지가 있습니다."
        else:
            interpretations["overall"] = "개선 필요: 추천 시스템의 전반적인 개선이 필요합니다."
        
        # 사용자 활성도
        active_users = metrics.get("active_users", 0)
        interpretations["user_activity"] = f"지난 {30}일 동안 {active_users}명의 활성 사용자가 있었습니다."
        
        return interpretations
    
    def _get_improvement_suggestions(self, metrics: Dict[str, float]) -> List[str]:
        """개선 제안사항"""
        
        suggestions = []
        
        if metrics["precision"] < 0.3:
            suggestions.append("사용자 선호도 학습 알고리즘을 개선하세요.")
        
        if metrics["diversity_score"] < 0.4:
            suggestions.append("추천 결과의 다양성을 높이기 위해 탐색 요소를 추가하세요.")
        
        if metrics["novelty_score"] < 0.5:
            suggestions.append("사용자에게 새로운 콘텐츠를 더 많이 노출시키세요.")
        
        if metrics["engagement_score"] < 0.3:
            suggestions.append("사용자 인터페이스를 개선하여 참여를 유도하세요.")
        
        if metrics["conversion_rate"] < 0.1:
            suggestions.append("추천 결과의 표시 방식을 개선하여 전환율을 높이세요.")
        
        return suggestions
    
    def _get_system_improvement_suggestions(self, metrics: Dict[str, float]) -> List[str]:
        """시스템 전체 개선 제안사항"""
        
        suggestions = []
        
        avg_precision = metrics.get("avg_precision", 0)
        avg_diversity = metrics.get("avg_diversity", 0)
        
        if avg_precision < 0.3:
            suggestions.append("전체적인 추천 알고리즘 성능 개선이 필요합니다.")
        
        if avg_diversity < 0.4:
            suggestions.append("시스템 전반의 추천 다양성을 높이는 정책을 도입하세요.")
        
        if metrics.get("active_users", 0) < 100:
            suggestions.append("사용자 유입을 늘리기 위한 마케팅 전략이 필요합니다.")
        
        return suggestions


# 싱글톤 패턴
_metrics_instances = {}

def get_recommendation_metrics(db: Session) -> RecommendationMetrics:
    """RecommendationMetrics 인스턴스 가져오기"""
    
    session_id = id(db)
    if session_id not in _metrics_instances:
        _metrics_instances[session_id] = RecommendationMetrics(db)
    
    return _metrics_instances[session_id]