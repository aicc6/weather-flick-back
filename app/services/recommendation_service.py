from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.services.kma_weather_service import kma_weather_service
from app.models import Destination, User
from sqlalchemy import or_

class RecommendationService:
    # 날씨 상태와 관련 태그 매핑
    WEATHER_TO_TAGS_MAPPING = {
        "맑음": ["#야외", "#산책", "#공원", "#자연"],
        "구름많음": ["#산책", "#경치", "#나들이"],
        "흐림": ["#실내", "#카페", "#박물관", "#쇼핑"],
        "비": ["#실내", "#박물관", "#미술관", "#아쿠아리움", "#카페"],
        "비/눈": ["#실내", "#카페", "#쇼핑"],
        "눈": ["#실내", "#겨울경치", "#스파", "#카페"],
        "소나기": ["#실내", "#급방문", "#카페"]
    }

    def calculate_personalization_score(self, destination: Destination, user: User) -> float:
        """개인화 점수 계산"""
        score = 0.0
        if user.preferences and destination.tags:
            user_prefs = set(user.preferences)
            dest_tags = set(destination.tags)
            common_tags = user_prefs.intersection(dest_tags)
            # 일치하는 태그 하나당 1.0점 추가
            score += len(common_tags) * 1.0
        return score

    async def get_weather_based_recommendations(
        self, db: Session, province: str, city: str, user: User
    ) -> List[tuple[Destination, float]]:
        """
        날씨 및 개인 선호도 기반 여행지 추천 로직
        1. 현재 날씨 정보를 가져온다.
        2. 날씨에 맞는 태그를 결정한다.
        3. 해당 지역과 태그에 맞는 여행지를 DB에서 조회한다.
        """
        try:
            # 1. 현재 날씨 정보 가져오기 (kma_weather_service 사용)
            coords = kma_weather_service.get_city_coordinates(city)
            if not coords:
                # 기본적으로는 city로 검색하지만, province 전체로 확장 검색도 가능
                return []

            weather_data = await kma_weather_service.get_current_weather(coords["nx"], coords["ny"])
            weather_condition = weather_data.get("sky_condition", "맑음") # SKY 값 기준

            # 2. 날씨에 맞는 추천 태그 결정
            relevant_tags = self.WEATHER_TO_TAGS_MAPPING.get(weather_condition, [])

            # 3. DB에서 조건에 맞는 여행지 조회
            if not relevant_tags:
                # 추천 태그가 없으면 해당 지역의 모든 여행지 반환
                return db.query(Destination).filter(Destination.province == province).all()

            # 태그 중 하나라도 포함되면 추천
            tag_filters = [Destination.tags.contains([tag]) for tag in relevant_tags]

            weather_recommendations = db.query(Destination).filter(
                Destination.province == province,
                or_(*tag_filters)
            ).all()

            # 개인화 점수 반영하여 최종 추천 목록 생성
            final_recommendations = []
            for dest in weather_recommendations:
                # 기본 점수(평점) + 개인화 점수
                personal_score = self.calculate_personalization_score(dest, user)
                final_score = (dest.rating or 3.0) + personal_score
                final_recommendations.append((dest, final_score))

            # 최종 점수 기준으로 내림차순 정렬
            final_recommendations.sort(key=lambda x: x[1], reverse=True)

            return final_recommendations

        except Exception as e:
            # 오류 처리 (예: 로깅)
            print(f"Error in get_weather_based_recommendations: {e}")
            return []

recommendation_service = RecommendationService()
