"""이메일 인증 설정"""

import os
from dotenv import load_dotenv

load_dotenv()

# 이메일 인증 활성화 여부
EMAIL_VERIFICATION_ENABLED = os.getenv("EMAIL_VERIFICATION_ENABLED", "true").lower() == "true"

# 개발 환경에서는 이메일 인증을 비활성화할 수 있음
if os.getenv("ENVIRONMENT", "development") == "development":
    EMAIL_VERIFICATION_ENABLED = os.getenv("EMAIL_VERIFICATION_ENABLED", "false").lower() == "true"