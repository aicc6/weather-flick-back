from pydantic_settings import BaseSettings

# 1. .env 파일을 읽어들일 설정 클래스를 간단하게 정의합니다.
#    이 클래스는 .env 파일에서 KAKAO_API_KEY 만 찾아보도록 설정됩니다.
class EnvChecker(BaseSettings):
    kakao_api_key: str = "키를 찾지 못했습니다. .env 파일을 확인해주세요."

    class Config:
        env_file = ".env"
        case_sensitive = False

# 2. 설정을 로드합니다. 이 코드가 실행되는 순간 .env 파일의 내용이 메모리로 들어옵니다.
print("'.env' 파일에서 값을 불러오는 중...")
try:
    env_settings = EnvChecker()
    loaded_key = env_settings.kakao_api_key
    print("...불러오기 성공!")
except Exception as e:
    loaded_key = f"값을 불러오는 중 오류 발생: {e}"


# 3. 불러온 KAKAO_API_KEY 값을 직접 출력합니다.
print("\n============== 확인 결과 ==============")
print(f" KAKAO_API_KEY = {loaded_key}")
print("=======================================")
print("\n이 값이 카카오 개발자 사이트의 'REST API 키'와 정확히 일치해야 합니다.")
print("만약 다르거나, '키를 찾지 못했습니다'라고 나온다면,")
print("`.env` 파일이 잘못 저장되었거나 내용이 틀린 것입니다.")
