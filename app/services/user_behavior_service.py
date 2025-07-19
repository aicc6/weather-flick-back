"""사용자 행동 추적 및 분석 서비스"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from fastapi import Request

from app.models import (
    User, UserActivityLog, TravelPlan, Review, 
    ReviewLike, TravelCourseLike, RecommendLike,
    TouristAttraction, Restaurant, Accommodation,
    CulturalFacility, Shopping
)


class UserBehaviorService:
    """사용자 행동 데이터 수집 및 분석 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def track_user_activity(
        self, 
        user_id: UUID,
        activity_type: str,
        activity_data: Dict[str, Any],
        request: Request = None
    ) -> UserActivityLog:
        """사용자 활동 기록"""
        
        # IP 주소와 User-Agent 추출
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host
            user_agent = request.headers.get("user-agent")
        
        # 활동 로그 생성
        activity_log = UserActivityLog(
            user_id=user_id,
            activity_type=activity_type,
            activity_data=activity_data,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=activity_data.get("session_id")
        )
        
        self.db.add(activity_log)
        self.db.commit()
        
        # 사용자 프로필 업데이트 (암묵적 선호도 학습)
        await self._update_implicit_preferences(user_id, activity_type, activity_data)
        
        return activity_log
    
    async def _update_implicit_preferences(
        self,
        user_id: UUID,
        activity_type: str,
        activity_data: Dict[str, Any]
    ):
        """암묵적 선호도 업데이트"""
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return
        
        # 현재 preferences 가져오기
        preferences = user.preferences or {}
        implicit_prefs = preferences.get("implicit", {})
        
        # 활동 유형별 선호도 업데이트
        if activity_type == "destination_view":
            # 여행지 조회 시 태그 카운트 증가
            destination_id = activity_data.get("destination_id")
            if destination_id:
                tags = self._get_destination_tags(destination_id)
                tag_counts = implicit_prefs.get("tag_counts", {})
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                implicit_prefs["tag_counts"] = tag_counts
        
        elif activity_type == "plan_created":
            # 여행 계획 생성 시 지역 선호도 업데이트
            region = activity_data.get("region")
            if region:
                region_counts = implicit_prefs.get("region_counts", {})
                region_counts[region] = region_counts.get(region, 0) + 1
                implicit_prefs["region_counts"] = region_counts
        
        elif activity_type == "review_created":
            # 리뷰 작성 시 평점 기반 선호도 업데이트
            rating = activity_data.get("rating", 0)
            destination_id = activity_data.get("destination_id")
            if rating >= 4 and destination_id:
                tags = self._get_destination_tags(destination_id)
                liked_tags = implicit_prefs.get("liked_tags", {})
                for tag in tags:
                    liked_tags[tag] = liked_tags.get(tag, 0) + (rating - 3)
                implicit_prefs["liked_tags"] = liked_tags
        
        elif activity_type in ["like_added", "bookmark_added"]:
            # 좋아요/북마크 시 강한 선호도 신호
            destination_id = activity_data.get("destination_id")
            if destination_id:
                tags = self._get_destination_tags(destination_id)
                liked_tags = implicit_prefs.get("liked_tags", {})
                for tag in tags:
                    liked_tags[tag] = liked_tags.get(tag, 0) + 2
                implicit_prefs["liked_tags"] = liked_tags
        
        # 체류 시간 기록
        if activity_type == "page_view" and "duration" in activity_data:
            duration = activity_data["duration"]
            if duration > 30:  # 30초 이상 체류 시
                page_type = activity_data.get("page_type")
                engagement = implicit_prefs.get("engagement", {})
                engagement[page_type] = engagement.get(page_type, 0) + duration
                implicit_prefs["engagement"] = engagement
        
        # 업데이트된 preferences 저장
        preferences["implicit"] = implicit_prefs
        preferences["last_updated"] = datetime.now().isoformat()
        user.preferences = preferences
        
        self.db.commit()
    
    def _get_destination_tags(self, destination_id: str) -> List[str]:
        """여행지의 태그 목록 가져오기"""
        tags = []
        
        # 각 테이블에서 태그 조회
        tables = [
            TouristAttraction, Restaurant, Accommodation,
            CulturalFacility, Shopping
        ]
        
        for table in tables:
            destination = self.db.query(table).filter(
                table.content_id == destination_id
            ).first()
            if destination and hasattr(destination, 'tags'):
                tags.extend(destination.tags or [])
                break
        
        return tags
    
    async def get_user_preferences_profile(self, user_id: UUID) -> Dict[str, Any]:
        """사용자의 종합적인 선호도 프로필 생성"""
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {}
        
        # 명시적 선호도
        explicit_prefs = {
            "preferred_region": user.preferred_region,
            "preferred_theme": user.preferred_theme,
            "tags": user.preferences.get("tags", []) if user.preferences else []
        }
        
        # 암묵적 선호도
        implicit_prefs = user.preferences.get("implicit", {}) if user.preferences else {}
        
        # 최근 활동 분석
        recent_activities = self._analyze_recent_activities(user_id)
        
        # 협업 필터링을 위한 유사 사용자 찾기
        similar_users = self._find_similar_users(user_id)
        
        return {
            "user_id": str(user_id),
            "explicit_preferences": explicit_prefs,
            "implicit_preferences": implicit_prefs,
            "recent_activities": recent_activities,
            "similar_users": similar_users,
            "profile_completeness": self._calculate_profile_completeness(user)
        }
    
    def _analyze_recent_activities(
        self, 
        user_id: UUID, 
        days: int = 30
    ) -> Dict[str, Any]:
        """최근 활동 분석"""
        
        since_date = datetime.now() - timedelta(days=days)
        
        # 최근 활동 로그 조회
        activities = self.db.query(UserActivityLog).filter(
            and_(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= since_date
            )
        ).all()
        
        # 활동 유형별 집계
        activity_summary = {}
        for activity in activities:
            activity_type = activity.activity_type
            activity_summary[activity_type] = activity_summary.get(activity_type, 0) + 1
        
        # 최근 조회한 여행지
        recent_views = []
        for activity in activities:
            if activity.activity_type == "destination_view":
                destination_id = activity.activity_data.get("destination_id")
                if destination_id:
                    recent_views.append({
                        "destination_id": destination_id,
                        "viewed_at": activity.created_at.isoformat()
                    })
        
        return {
            "activity_summary": activity_summary,
            "recent_destination_views": recent_views[-10:],  # 최근 10개
            "total_activities": len(activities)
        }
    
    def _find_similar_users(
        self, 
        user_id: UUID, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """유사한 사용자 찾기 (협업 필터링)"""
        
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.preferences:
            return []
        
        user_tags = set(user.preferences.get("tags", []))
        if not user_tags:
            return []
        
        # 태그 기반 유사도 계산
        similar_users = []
        
        other_users = self.db.query(User).filter(
            User.user_id != user_id,
            User.preferences.isnot(None)
        ).limit(100).all()  # 성능을 위해 제한
        
        for other_user in other_users:
            other_tags = set(other_user.preferences.get("tags", []))
            if other_tags:
                # Jaccard 유사도 계산
                intersection = len(user_tags & other_tags)
                union = len(user_tags | other_tags)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.2:  # 20% 이상 유사도
                    similar_users.append({
                        "user_id": str(other_user.user_id),
                        "similarity_score": similarity,
                        "shared_tags": list(user_tags & other_tags)
                    })
        
        # 유사도 높은 순으로 정렬
        similar_users.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similar_users[:limit]
    
    def _calculate_profile_completeness(self, user: User) -> float:
        """프로필 완성도 계산"""
        
        completeness = 0.0
        total_fields = 8
        
        if user.nickname:
            completeness += 1
        if user.profile_image:
            completeness += 1
        if user.bio:
            completeness += 1
        if user.preferred_region:
            completeness += 1
        if user.preferred_theme:
            completeness += 1
        if user.preferences and user.preferences.get("tags"):
            completeness += 1
        if user.preferences and user.preferences.get("implicit"):
            completeness += 1
        if user.last_login:
            completeness += 1
        
        return (completeness / total_fields) * 100
    
    async def get_personalized_recommendations(
        self,
        user_id: UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """개인화된 추천 생성"""
        
        # 사용자 프로필 가져오기
        user_profile = await self.get_user_preferences_profile(user_id)
        
        # 컨텍스트 정보 (시간, 위치, 날씨 등)
        current_context = context or {}
        
        # 추천 점수 계산
        recommendations = []
        
        # 1. 콘텐츠 기반 필터링
        content_based = await self._content_based_filtering(user_profile)
        
        # 2. 협업 필터링
        collaborative = await self._collaborative_filtering(user_profile)
        
        # 3. 하이브리드 점수 계산
        all_destinations = {}
        
        # 콘텐츠 기반 점수 통합
        for dest in content_based:
            dest_id = dest["id"]
            all_destinations[dest_id] = {
                **dest,
                "content_score": dest["score"],
                "collaborative_score": 0
            }
        
        # 협업 필터링 점수 통합
        for dest in collaborative:
            dest_id = dest["id"]
            if dest_id in all_destinations:
                all_destinations[dest_id]["collaborative_score"] = dest["score"]
            else:
                all_destinations[dest_id] = {
                    **dest,
                    "content_score": 0,
                    "collaborative_score": dest["score"]
                }
        
        # 최종 점수 계산 (가중 평균)
        for dest_id, dest_data in all_destinations.items():
            final_score = (
                0.6 * dest_data["content_score"] +
                0.4 * dest_data["collaborative_score"]
            )
            
            # 컨텍스트 보정
            if current_context:
                final_score = self._apply_context_boost(
                    final_score, dest_data, current_context
                )
            
            dest_data["final_score"] = final_score
            recommendations.append(dest_data)
        
        # 점수 기준 정렬
        recommendations.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 다양성 확보
        diversified = self._ensure_diversity(recommendations)
        
        return diversified[:20]  # 상위 20개 반환
    
    async def _content_based_filtering(
        self, 
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """콘텐츠 기반 필터링"""
        
        recommendations = []
        
        # 사용자의 선호 태그 가져오기
        explicit_tags = user_profile["explicit_preferences"]["tags"]
        implicit_tags = user_profile["implicit_preferences"].get("liked_tags", {})
        
        # 태그 가중치 계산
        tag_weights = {}
        for tag in explicit_tags:
            tag_weights[tag] = 2.0  # 명시적 선호도는 높은 가중치
        
        for tag, count in implicit_tags.items():
            tag_weights[tag] = tag_weights.get(tag, 0) + (count * 0.1)
        
        if not tag_weights:
            return []
        
        # 각 여행지 테이블에서 추천 점수 계산
        tables = [
            (TouristAttraction, "tourist_attraction"),
            (Restaurant, "restaurant"),
            (Accommodation, "accommodation"),
            (CulturalFacility, "cultural_facility"),
            (Shopping, "shopping")
        ]
        
        for table, type_name in tables:
            destinations = self.db.query(table).limit(100).all()
            
            for dest in destinations:
                if not hasattr(dest, 'tags') or not dest.tags:
                    continue
                
                # 태그 매칭 점수 계산
                score = 0
                matched_tags = []
                
                for tag in dest.tags:
                    if tag in tag_weights:
                        score += tag_weights[tag]
                        matched_tags.append(tag)
                
                if score > 0:
                    recommendations.append({
                        "id": dest.content_id,
                        "name": dest.name,
                        "type": type_name,
                        "score": score,
                        "matched_tags": matched_tags,
                        "tags": dest.tags,
                        "rating": getattr(dest, 'rating', 4.0)
                    })
        
        return recommendations
    
    async def _collaborative_filtering(
        self, 
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """협업 필터링"""
        
        recommendations = []
        similar_users = user_profile["similar_users"]
        
        if not similar_users:
            return []
        
        # 유사 사용자들이 좋아한 여행지 찾기
        destination_scores = {}
        
        for similar_user in similar_users[:5]:  # 상위 5명만
            user_id = UUID(similar_user["user_id"])
            similarity = similar_user["similarity_score"]
            
            # 해당 사용자의 좋아요 목록
            likes = self.db.query(RecommendLike).filter(
                RecommendLike.user_id == user_id
            ).all()
            
            for like in likes:
                dest_id = like.recommend_id
                if dest_id not in destination_scores:
                    destination_scores[dest_id] = 0
                destination_scores[dest_id] += similarity
            
            # 높은 평점 리뷰
            reviews = self.db.query(Review).filter(
                Review.user_id == user_id,
                Review.rating >= 4
            ).all()
            
            for review in reviews:
                dest_id = review.content_id
                if dest_id not in destination_scores:
                    destination_scores[dest_id] = 0
                destination_scores[dest_id] += similarity * (review.rating / 5)
        
        # 점수가 높은 여행지 정보 가져오기
        for dest_id, score in destination_scores.items():
            # 각 테이블에서 여행지 정보 조회
            destination_info = self._get_destination_info(dest_id)
            if destination_info:
                recommendations.append({
                    **destination_info,
                    "score": score
                })
        
        return recommendations
    
    def _get_destination_info(self, destination_id: str) -> Optional[Dict[str, Any]]:
        """여행지 정보 조회"""
        
        tables = [
            (TouristAttraction, "tourist_attraction"),
            (Restaurant, "restaurant"),
            (Accommodation, "accommodation"),
            (CulturalFacility, "cultural_facility"),
            (Shopping, "shopping")
        ]
        
        for table, type_name in tables:
            dest = self.db.query(table).filter(
                table.content_id == destination_id
            ).first()
            
            if dest:
                return {
                    "id": dest.content_id,
                    "name": dest.name,
                    "type": type_name,
                    "tags": getattr(dest, 'tags', []),
                    "rating": getattr(dest, 'rating', 4.0),
                    "address": getattr(dest, 'address', '')
                }
        
        return None
    
    def _apply_context_boost(
        self,
        base_score: float,
        destination: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """컨텍스트 기반 점수 보정"""
        
        boosted_score = base_score
        
        # 시간대별 보정
        current_hour = context.get("hour", datetime.now().hour)
        if destination["type"] == "restaurant":
            if current_hour in [11, 12, 13, 18, 19, 20]:  # 식사 시간
                boosted_score *= 1.5
        elif destination["type"] == "accommodation":
            if current_hour >= 20:  # 저녁 시간
                boosted_score *= 1.3
        
        # 날씨별 보정
        weather = context.get("weather")
        if weather:
            tags = destination.get("tags", [])
            if weather == "비" and any(tag in ["#실내", "#박물관", "#전시"] for tag in tags):
                boosted_score *= 1.4
            elif weather == "맑음" and any(tag in ["#야외", "#공원", "#산책"] for tag in tags):
                boosted_score *= 1.4
        
        # 계절별 보정
        season = context.get("season")
        if season:
            if season == "summer" and any(tag in ["#해변", "#수영장", "#계곡"] for tag in destination.get("tags", [])):
                boosted_score *= 1.3
            elif season == "winter" and any(tag in ["#스키", "#온천", "#실내"] for tag in destination.get("tags", [])):
                boosted_score *= 1.3
        
        return boosted_score
    
    def _ensure_diversity(
        self, 
        recommendations: List[Dict[str, Any]], 
        diversity_factor: float = 0.3
    ) -> List[Dict[str, Any]]:
        """추천 결과의 다양성 확보"""
        
        if len(recommendations) <= 5:
            return recommendations
        
        diversified = []
        selected_types = set()
        selected_tags = set()
        
        # 점수 높은 순으로 선택하되, 다양성 고려
        for rec in recommendations:
            rec_type = rec["type"]
            rec_tags = set(rec.get("tags", []))
            
            # 타입 다양성
            type_penalty = 0
            if rec_type in selected_types:
                type_penalty = 0.2
            
            # 태그 다양성
            tag_overlap = len(rec_tags & selected_tags)
            tag_penalty = tag_overlap * 0.05
            
            # 다양성 페널티 적용
            adjusted_score = rec["final_score"] * (1 - type_penalty - tag_penalty)
            rec["diversity_adjusted_score"] = adjusted_score
            
            diversified.append(rec)
            selected_types.add(rec_type)
            selected_tags.update(rec_tags)
        
        # 조정된 점수로 재정렬
        diversified.sort(key=lambda x: x["diversity_adjusted_score"], reverse=True)
        
        # 탐색 요소 추가 (Exploration)
        exploration_count = int(len(diversified) * diversity_factor)
        if exploration_count > 0:
            # 하위 점수 중 일부를 무작위로 상위로 이동
            import random
            lower_half = diversified[len(diversified)//2:]
            exploration_items = random.sample(
                lower_half, 
                min(exploration_count, len(lower_half))
            )
            
            # 상위 20% 위치에 무작위 삽입
            for item in exploration_items:
                insert_pos = random.randint(0, len(diversified) // 5)
                diversified.remove(item)
                diversified.insert(insert_pos, item)
        
        return diversified


# 싱글톤 패턴으로 서비스 인스턴스 관리
_service_instances = {}

def get_user_behavior_service(db: Session) -> UserBehaviorService:
    """UserBehaviorService 인스턴스 가져오기"""
    
    # 세션별로 서비스 인스턴스 관리
    session_id = id(db)
    if session_id not in _service_instances:
        _service_instances[session_id] = UserBehaviorService(db)
    
    return _service_instances[session_id]