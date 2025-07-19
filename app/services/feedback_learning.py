"""
사용자 피드백 기반 학습 시스템
여행 후 피드백을 수집하고 분석하여 추천 품질 개선
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import func

from app.models import User, TravelPlan
from app.config import settings

logger = logging.getLogger(__name__)
Base = declarative_base()


class FeedbackType(Enum):
    """피드백 타입"""
    RATING = "rating"           # 전체 평점
    PLACE_FEEDBACK = "place"    # 장소별 피드백
    TIMING_FEEDBACK = "timing"  # 시간 배분 피드백
    ROUTE_FEEDBACK = "route"    # 동선 피드백
    PREFERENCE = "preference"   # 선호도 업데이트


@dataclass
class PlaceFeedback:
    """장소별 피드백"""
    place_id: str
    place_name: str
    visited: bool
    rating: Optional[int]  # 1-5
    actual_duration: Optional[int]  # 실제 체류 시간 (분)
    recommended_duration: int  # 추천 체류 시간
    comments: Optional[str]
    tags: List[str]


@dataclass
class RouteFeedback:
    """동선 피드백"""
    day: int
    efficiency_rating: int  # 1-5
    total_distance: float
    walking_time: int
    transport_issues: List[str]
    suggestions: List[str]


@dataclass
class TravelFeedback:
    """전체 여행 피드백"""
    travel_plan_id: int
    user_id: int
    overall_rating: int  # 1-5
    place_feedbacks: List[PlaceFeedback]
    route_feedbacks: List[RouteFeedback]
    timing_satisfaction: int  # 1-5
    weather_adaptation: int  # 1-5
    would_recommend: bool
    highlights: List[str]
    improvements: List[str]
    additional_comments: Optional[str]


class UserFeedback(Base):
    """사용자 피드백 모델"""
    __tablename__ = "user_feedbacks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    travel_plan_id = Column(Integer, ForeignKey("travel_plans.id"))
    feedback_type = Column(String(50))
    feedback_data = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    # 학습 결과
    learning_applied = Column(Integer, default=0)  # 학습 적용 여부
    impact_score = Column(Float, default=0.0)  # 영향도 점수


class UserPreferenceHistory(Base):
    """사용자 선호도 변화 추적"""
    __tablename__ = "user_preference_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    preference_type = Column(String(50))  # culture, nature, food 등
    old_value = Column(Float)
    new_value = Column(Float)
    reason = Column(String(200))  # 변경 이유
    feedback_id = Column(Integer, ForeignKey("user_feedbacks.id"))
    created_at = Column(DateTime, default=func.now())


class PlacePerformance(Base):
    """장소별 성과 추적"""
    __tablename__ = "place_performance"
    
    id = Column(Integer, primary_key=True)
    place_id = Column(String(100))
    place_name = Column(String(200))
    place_type = Column(String(50))
    
    # 통계 데이터
    total_recommendations = Column(Integer, default=0)
    total_visits = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    skip_rate = Column(Float, default=0.0)  # 건너뛴 비율
    
    # 시간 관련
    recommended_duration_avg = Column(Integer)  # 평균 추천 시간
    actual_duration_avg = Column(Integer)  # 평균 실제 체류 시간
    
    # 페르소나별 성과
    persona_performance = Column(JSON)  # {"adventurer": 4.5, "cultural": 4.2, ...}
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class FeedbackLearningService:
    """피드백 학습 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def collect_feedback(
        self, 
        user_id: int, 
        travel_plan_id: int,
        feedback_data: Dict[str, Any]
    ) -> TravelFeedback:
        """여행 후 피드백 수집"""
        
        # 피드백 데이터 검증 및 정규화
        travel_feedback = self._parse_feedback_data(user_id, travel_plan_id, feedback_data)
        
        # 피드백 저장
        await self._save_feedback(travel_feedback)
        
        # 즉시 학습 적용
        await self._apply_immediate_learning(travel_feedback)
        
        # 장소 성과 업데이트
        await self._update_place_performance(travel_feedback)
        
        return travel_feedback
    
    def _parse_feedback_data(
        self, 
        user_id: int, 
        travel_plan_id: int,
        raw_data: Dict[str, Any]
    ) -> TravelFeedback:
        """원시 피드백 데이터 파싱"""
        
        # 장소별 피드백 파싱
        place_feedbacks = []
        for place_data in raw_data.get("places", []):
            place_fb = PlaceFeedback(
                place_id=place_data["place_id"],
                place_name=place_data["place_name"],
                visited=place_data.get("visited", True),
                rating=place_data.get("rating"),
                actual_duration=place_data.get("actual_duration"),
                recommended_duration=place_data.get("recommended_duration", 120),
                comments=place_data.get("comments"),
                tags=place_data.get("tags", [])
            )
            place_feedbacks.append(place_fb)
        
        # 동선 피드백 파싱
        route_feedbacks = []
        for route_data in raw_data.get("routes", []):
            route_fb = RouteFeedback(
                day=route_data["day"],
                efficiency_rating=route_data.get("efficiency_rating", 3),
                total_distance=route_data.get("total_distance", 0),
                walking_time=route_data.get("walking_time", 0),
                transport_issues=route_data.get("transport_issues", []),
                suggestions=route_data.get("suggestions", [])
            )
            route_feedbacks.append(route_fb)
        
        return TravelFeedback(
            travel_plan_id=travel_plan_id,
            user_id=user_id,
            overall_rating=raw_data.get("overall_rating", 3),
            place_feedbacks=place_feedbacks,
            route_feedbacks=route_feedbacks,
            timing_satisfaction=raw_data.get("timing_satisfaction", 3),
            weather_adaptation=raw_data.get("weather_adaptation", 3),
            would_recommend=raw_data.get("would_recommend", True),
            highlights=raw_data.get("highlights", []),
            improvements=raw_data.get("improvements", []),
            additional_comments=raw_data.get("additional_comments")
        )
    
    async def _save_feedback(self, feedback: TravelFeedback):
        """피드백 데이터베이스 저장"""
        
        # 전체 피드백 저장
        overall_feedback = UserFeedback(
            user_id=feedback.user_id,
            travel_plan_id=feedback.travel_plan_id,
            feedback_type=FeedbackType.RATING.value,
            feedback_data={
                "overall_rating": feedback.overall_rating,
                "timing_satisfaction": feedback.timing_satisfaction,
                "weather_adaptation": feedback.weather_adaptation,
                "would_recommend": feedback.would_recommend,
                "highlights": feedback.highlights,
                "improvements": feedback.improvements,
                "additional_comments": feedback.additional_comments
            }
        )
        self.db.add(overall_feedback)
        
        # 장소별 피드백 저장
        for place_fb in feedback.place_feedbacks:
            place_feedback_db = UserFeedback(
                user_id=feedback.user_id,
                travel_plan_id=feedback.travel_plan_id,
                feedback_type=FeedbackType.PLACE_FEEDBACK.value,
                feedback_data=asdict(place_fb)
            )
            self.db.add(place_feedback_db)
        
        # 동선 피드백 저장
        for route_fb in feedback.route_feedbacks:
            route_feedback_db = UserFeedback(
                user_id=feedback.user_id,
                travel_plan_id=feedback.travel_plan_id,
                feedback_type=FeedbackType.ROUTE_FEEDBACK.value,
                feedback_data=asdict(route_fb)
            )
            self.db.add(route_feedback_db)
        
        self.db.commit()
    
    async def _apply_immediate_learning(self, feedback: TravelFeedback):
        """즉시 적용 가능한 학습 수행"""
        
        # 사용자 선호도 업데이트
        await self._update_user_preferences(feedback)
        
        # 시간 배분 학습
        await self._learn_timing_patterns(feedback)
        
        # 동선 효율성 학습
        await self._learn_route_efficiency(feedback)
    
    async def _update_user_preferences(self, feedback: TravelFeedback):
        """사용자 선호도 업데이트"""
        
        # 높은 평점 장소의 태그 분석
        liked_tags = {}
        disliked_tags = {}
        
        for place_fb in feedback.place_feedbacks:
            if place_fb.rating:
                for tag in place_fb.tags:
                    if place_fb.rating >= 4:
                        liked_tags[tag] = liked_tags.get(tag, 0) + 1
                    elif place_fb.rating <= 2:
                        disliked_tags[tag] = disliked_tags.get(tag, 0) + 1
        
        # 선호도 점수 계산
        preference_updates = {}
        
        # 태그를 카테고리로 매핑
        tag_category_map = {
            "문화": "culture",
            "역사": "culture",
            "박물관": "culture",
            "자연": "nature",
            "공원": "nature",
            "산": "nature",
            "맛집": "food",
            "음식": "food",
            "카페": "food",
            "쇼핑": "shopping",
            "시장": "shopping",
            "액티비티": "activity",
            "체험": "activity"
        }
        
        for tag, count in liked_tags.items():
            category = tag_category_map.get(tag)
            if category:
                preference_updates[category] = preference_updates.get(category, 0) + count * 0.1
        
        for tag, count in disliked_tags.items():
            category = tag_category_map.get(tag)
            if category:
                preference_updates[category] = preference_updates.get(category, 0) - count * 0.05
        
        # 사용자 선호도 업데이트 (실제로는 User 모델에 preference 필드 추가 필요)
        logger.info(f"사용자 {feedback.user_id} 선호도 업데이트: {preference_updates}")
    
    async def _learn_timing_patterns(self, feedback: TravelFeedback):
        """시간 배분 패턴 학습"""
        
        timing_insights = {
            "over_time": [],  # 시간 초과한 장소
            "under_time": [],  # 시간 부족한 장소
            "optimal_time": []  # 적절한 시간
        }
        
        for place_fb in feedback.place_feedbacks:
            if place_fb.actual_duration and place_fb.visited:
                time_diff = place_fb.actual_duration - place_fb.recommended_duration
                time_ratio = place_fb.actual_duration / place_fb.recommended_duration
                
                if time_ratio > 1.3:  # 30% 이상 초과
                    timing_insights["over_time"].append({
                        "place_id": place_fb.place_id,
                        "type": self._get_place_type(place_fb.tags),
                        "recommended": place_fb.recommended_duration,
                        "actual": place_fb.actual_duration,
                        "ratio": time_ratio
                    })
                elif time_ratio < 0.7:  # 30% 이상 부족
                    timing_insights["under_time"].append({
                        "place_id": place_fb.place_id,
                        "type": self._get_place_type(place_fb.tags),
                        "recommended": place_fb.recommended_duration,
                        "actual": place_fb.actual_duration,
                        "ratio": time_ratio
                    })
                else:
                    timing_insights["optimal_time"].append({
                        "place_id": place_fb.place_id,
                        "type": self._get_place_type(place_fb.tags)
                    })
        
        # 인사이트 저장
        if timing_insights["over_time"] or timing_insights["under_time"]:
            timing_feedback = UserFeedback(
                user_id=feedback.user_id,
                travel_plan_id=feedback.travel_plan_id,
                feedback_type=FeedbackType.TIMING_FEEDBACK.value,
                feedback_data=timing_insights
            )
            self.db.add(timing_feedback)
            self.db.commit()
    
    async def _learn_route_efficiency(self, feedback: TravelFeedback):
        """동선 효율성 학습"""
        
        route_insights = {
            "efficient_routes": [],
            "inefficient_routes": [],
            "transport_preferences": {},
            "distance_tolerance": 0
        }
        
        total_efficiency_score = 0
        for route_fb in feedback.route_feedbacks:
            total_efficiency_score += route_fb.efficiency_rating
            
            if route_fb.efficiency_rating >= 4:
                route_insights["efficient_routes"].append({
                    "day": route_fb.day,
                    "distance": route_fb.total_distance,
                    "walking_time": route_fb.walking_time
                })
            elif route_fb.efficiency_rating <= 2:
                route_insights["inefficient_routes"].append({
                    "day": route_fb.day,
                    "distance": route_fb.total_distance,
                    "walking_time": route_fb.walking_time,
                    "issues": route_fb.transport_issues
                })
            
            # 교통 수단 선호도 분석
            for issue in route_fb.transport_issues:
                if "대중교통" in issue:
                    route_insights["transport_preferences"]["transit"] = \
                        route_insights["transport_preferences"].get("transit", 0) - 1
                elif "도보" in issue:
                    route_insights["transport_preferences"]["walking"] = \
                        route_insights["transport_preferences"].get("walking", 0) - 1
        
        # 평균 효율성 점수
        avg_efficiency = total_efficiency_score / len(feedback.route_feedbacks) if feedback.route_feedbacks else 3
        route_insights["average_efficiency"] = avg_efficiency
        
        # 거리 허용치 계산
        if route_insights["efficient_routes"]:
            avg_distance = sum(r["distance"] for r in route_insights["efficient_routes"]) / len(route_insights["efficient_routes"])
            route_insights["distance_tolerance"] = avg_distance
        
        logger.info(f"동선 효율성 학습 결과: {route_insights}")
    
    async def _update_place_performance(self, feedback: TravelFeedback):
        """장소 성과 업데이트"""
        
        for place_fb in feedback.place_feedbacks:
            # 기존 성과 데이터 조회
            place_perf = self.db.query(PlacePerformance).filter_by(
                place_id=place_fb.place_id
            ).first()
            
            if not place_perf:
                place_perf = PlacePerformance(
                    place_id=place_fb.place_id,
                    place_name=place_fb.place_name,
                    place_type=self._get_place_type(place_fb.tags)
                )
                self.db.add(place_perf)
            
            # 통계 업데이트
            place_perf.total_recommendations += 1
            
            if place_fb.visited:
                place_perf.total_visits += 1
                
                # 평점 업데이트
                if place_fb.rating:
                    if place_perf.average_rating == 0:
                        place_perf.average_rating = place_fb.rating
                    else:
                        # 이동 평균 계산
                        place_perf.average_rating = (
                            place_perf.average_rating * (place_perf.total_visits - 1) + place_fb.rating
                        ) / place_perf.total_visits
                
                # 체류 시간 업데이트
                if place_fb.actual_duration:
                    if place_perf.actual_duration_avg is None:
                        place_perf.actual_duration_avg = place_fb.actual_duration
                    else:
                        place_perf.actual_duration_avg = (
                            place_perf.actual_duration_avg * (place_perf.total_visits - 1) + place_fb.actual_duration
                        ) / place_perf.total_visits
            
            # 건너뛴 비율 계산
            place_perf.skip_rate = 1 - (place_perf.total_visits / place_perf.total_recommendations)
            
        self.db.commit()
    
    def _get_place_type(self, tags: List[str]) -> str:
        """태그에서 장소 타입 추출"""
        tag_str = " ".join(tags).lower()
        
        if any(word in tag_str for word in ["음식", "맛집", "레스토랑", "카페"]):
            return "food"
        elif any(word in tag_str for word in ["문화", "박물관", "미술관", "역사"]):
            return "cultural"
        elif any(word in tag_str for word in ["자연", "공원", "산", "해변"]):
            return "nature"
        elif any(word in tag_str for word in ["쇼핑", "시장", "백화점"]):
            return "shopping"
        elif any(word in tag_str for word in ["액티비티", "체험", "레저"]):
            return "activity"
        else:
            return "attraction"
    
    async def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """사용자별 학습된 인사이트 조회"""
        
        # 최근 피드백 조회
        recent_feedbacks = self.db.query(UserFeedback).filter_by(
            user_id=user_id
        ).order_by(UserFeedback.created_at.desc()).limit(10).all()
        
        insights = {
            "preference_trends": {},
            "timing_preferences": {},
            "route_preferences": {},
            "favorite_places": [],
            "avoid_places": []
        }
        
        # 피드백 분석
        for feedback in recent_feedbacks:
            if feedback.feedback_type == FeedbackType.PLACE_FEEDBACK.value:
                place_data = feedback.feedback_data
                if place_data.get("rating", 0) >= 4:
                    insights["favorite_places"].append({
                        "place_id": place_data["place_id"],
                        "name": place_data["place_name"],
                        "rating": place_data["rating"]
                    })
                elif place_data.get("rating", 0) <= 2:
                    insights["avoid_places"].append({
                        "place_id": place_data["place_id"],
                        "name": place_data["place_name"],
                        "rating": place_data["rating"]
                    })
        
        return insights
    
    async def get_place_recommendations(
        self, place_type: str, persona_type: str
    ) -> List[Dict[str, Any]]:
        """성과 기반 장소 추천"""
        
        # 높은 성과 장소 조회
        top_places = self.db.query(PlacePerformance).filter(
            PlacePerformance.place_type == place_type,
            PlacePerformance.average_rating >= 4.0,
            PlacePerformance.skip_rate < 0.3
        ).order_by(PlacePerformance.average_rating.desc()).limit(10).all()
        
        recommendations = []
        for place in top_places:
            # 페르소나별 성과 확인
            persona_perf = place.persona_performance or {}
            persona_rating = persona_perf.get(persona_type, place.average_rating)
            
            if persona_rating >= 4.0:
                recommendations.append({
                    "place_id": place.place_id,
                    "place_name": place.place_name,
                    "average_rating": place.average_rating,
                    "persona_rating": persona_rating,
                    "recommended_duration": place.actual_duration_avg or 120,
                    "visit_rate": 1 - place.skip_rate
                })
        
        return recommendations


def get_feedback_learning_service(db: Session) -> FeedbackLearningService:
    """피드백 학습 서비스 인스턴스 생성"""
    return FeedbackLearningService(db)