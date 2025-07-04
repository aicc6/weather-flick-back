from flask import Blueprint, current_app, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Blueprint 및 limiter 초기화 (실제 구현에서는 앱 초기화 시 설정)
bp = Blueprint("travel", __name__)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


@bp.route("/travel-recommendations", methods=["POST"])
@limiter.limit("10 per minute")
def generate_travel_recommendations():
    """여행 추천 생성"""
    try:
        data = request.get_json()

        # 입력 검증
        required_fields = ["region", "period", "days", "who", "styles", "schedule"]
        if not all(field in data for field in required_fields):
            return (
                jsonify({"success": False, "message": "필수 필드가 누락되었습니다."}),
                400,
            )

        # 추천 로직 (실제로는 더 복잡한 알고리즘 적용)
        recommendations = {
            "summary": {
                "region": data["region"],
                "period": data["period"],
                "days": int(data["days"]),
                "who": data["who"],
                "styles": (
                    data["styles"].split(",")
                    if isinstance(data["styles"], str)
                    else data["styles"]
                ),
                "schedule": data["schedule"],
            },
            "itinerary": generate_itinerary_data(data),
            "weather_info": {
                "forecast": "맑음, 평균 기온 20°C",
                "recommendation": "야외 활동하기 좋은 날씨입니다!",
            },
            "tips": generate_travel_tips(data),
        }

        return jsonify({"success": True, "data": recommendations})

    except Exception as e:
        current_app.logger.error(f"Travel recommendation error: {str(e)}")
        return (
            jsonify({"success": False, "message": "추천 생성 중 오류가 발생했습니다."}),
            500,
        )


def generate_itinerary_data(data):
    """일정 데이터 생성"""
    days_count = int(data["days"])
    region = data["region"]
    styles = (
        data["styles"].split(",") if isinstance(data["styles"], str) else data["styles"]
    )
    schedule_type = data["schedule"]

    itinerary = []

    # 스타일별 장소 타입 매핑
    style_places = {
        "activity": ["체험관", "액티비티센터", "어드벤처파크"],
        "hotplace": ["포토존", "감성카페", "SNS명소"],
        "nature": ["공원", "해변", "산책로"],
        "landmark": ["관광명소", "박물관", "유명건축물"],
        "healing": ["스파", "온천", "힐링카페"],
        "culture": ["박물관", "미술관", "전통마을"],
        "local": ["전통시장", "로컬카페", "골목길"],
        "shopping": ["쇼핑몰", "아울렛", "전통시장"],
        "food": ["맛집", "로컬푸드", "시장음식"],
    }

    for day in range(1, days_count + 1):
        places_per_day = 3 if schedule_type == "relaxed" else 5

        day_places = []
        for i in range(places_per_day):
            # 스타일에 맞는 장소 선택
            if styles and len(styles) > 0:
                style = styles[i % len(styles)]
                place_types = style_places.get(style, ["관광지"])
                place_type = place_types[i % len(place_types)]
            else:
                place_type = "관광지"

            place = {
                "id": f"{day}-{i+1}",
                "name": f"{region} {place_type} {day}-{i+1}",
                "category": place_type,
                "time": f"{9 + i*2:02d}:00 - {11 + i*2:02d}:00",
                "description": f"{place_type}에서 즐기는 특별한 경험",
                "rating": round(4.0 + (i * 0.1), 1),
                "tags": [place_type, "추천", "인기"],
            }
            day_places.append(place)

        itinerary.append(
            {"day": day, "date": f"2024-06-{day + 14:02d}", "places": day_places}
        )

    return itinerary


def generate_travel_tips(data):
    """여행 팁 생성"""
    tips = []

    styles = (
        data["styles"].split(",") if isinstance(data["styles"], str) else data["styles"]
    )
    who = data["who"]
    schedule_type = data["schedule"]

    if "hotplace" in styles:
        tips.append(
            "SNS 핫플레이스가 포함된 일정으로 인스타 감성 사진을 남기실 수 있어요"
        )

    if "food" in styles:
        tips.append("맛집 위주로 구성된 일정으로 미식 여행을 즐기실 수 있어요")

    if "nature" in styles:
        tips.append("자연과 함께하는 코스로 힐링과 휴식을 취하실 수 있어요")

    if schedule_type == "relaxed":
        tips.append("널널한 일정으로 여유롭게 즐기실 수 있도록 구성했어요")
    else:
        tips.append("알찬 일정으로 다양한 경험을 하실 수 있도록 구성했어요")

    if who == "couple":
        tips.append("연인과 함께하는 로맨틱한 코스들이 포함되어 있어요")
    elif who == "family":
        tips.append("가족 모두가 즐길 수 있는 안전한 코스로 구성했어요")
    elif who == "friends":
        tips.append("친구들과 함께 즐길 수 있는 액티비티 중심으로 구성했어요")

    return tips[:3]  # 최대 3개 팁만 반환
