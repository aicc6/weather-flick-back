import random
import string
from datetime import datetime, timedelta, timezone

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import EmailServiceError
from app.logging_config import get_logger
from app.models import EmailVerification


class EmailService:
    """이메일 서비스"""

    def __init__(self):
        self.logger = get_logger("email_service")
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.mail_username,
            MAIL_PASSWORD=settings.mail_password,
            MAIL_FROM=settings.mail_from,
            MAIL_PORT=settings.mail_port,
            MAIL_SERVER=settings.mail_server,
            MAIL_STARTTLS=settings.mail_starttls,
            MAIL_SSL_TLS=settings.mail_ssl_tls,
            MAIL_FROM_NAME=settings.mail_from_name,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        self.fastmail = FastMail(self.conf)

    def generate_verification_code(self) -> str:
        """6자리 인증 코드 생성"""
        return "".join(random.choices(string.digits, k=6))

    async def send_verification_email(
        self, email: str, code: str, nickname: str = None
    ):
        """인증 이메일 발송"""
        try:
            # 이메일 템플릿
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Weather Flick 이메일 인증</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f6f9;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 64px;
                        height: 64px;
                        border-radius: 12px;
                        margin: 0 auto 20px;
                        display: block;
                        box-shadow: 0 4px 12px rgba(255,255,255,0.2);
                    }}
                    .header h1 {{
                        margin: 0 0 10px 0;
                        font-size: 28px;
                        font-weight: 700;
                    }}
                    .header p {{
                        margin: 0;
                        font-size: 16px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                        background: white;
                    }}
                    .verification-code {{
                        background: linear-gradient(135deg, #f8faff 0%, #e8f4fd 100%);
                        border: 3px dashed #667eea;
                        padding: 25px;
                        text-align: center;
                        border-radius: 12px;
                        margin: 30px 0;
                        font-size: 32px;
                        font-weight: 700;
                        color: #667eea;
                        letter-spacing: 4px;
                        font-family: 'Courier New', monospace;
                    }}
                    .highlight {{
                        background: linear-gradient(135deg, #fff5f5 0%, #fef2f2 100%);
                        border-left: 4px solid #ef4444;
                        padding: 20px;
                        margin: 25px 0;
                        border-radius: 8px;
                        font-weight: 600;
                        color: #dc2626;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 30px;
                        background: #f8fafc;
                        color: #64748b;
                        font-size: 14px;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .footer p {{
                        margin: 8px 0;
                    }}
                    h2 {{
                        color: #1e293b;
                        font-size: 24px;
                        margin: 0 0 20px 0;
                        font-weight: 600;
                    }}
                    p {{
                        margin: 16px 0;
                        color: #475569;
                        font-size: 16px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://wf-dev.seongjunlee.dev/newicon.jpg" height="200" width="200" alt="Weather Flick Logo" class="logo">
                        <h1>Weather Flick</h1>
                        <p>이메일 인증</p>
                    </div>
                    <div class="content">
                        <h2>안녕하세요{f", {nickname}" if nickname else ""}!</h2>
                        <p>Weather Flick 회원가입을 위한 이메일 인증 코드입니다.</p>

                        <div class="verification-code">
                            {code}
                        </div>

                        <div class="highlight">
                            <strong>⏰ 인증 코드는 10분 후에 만료됩니다.</strong>
                        </div>

                        <p>이 인증 코드를 앱에 입력하여 이메일 인증을 완료해주세요.</p>

                        <p>본인이 요청하지 않은 경우 이 이메일을 무시하셔도 됩니다.</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 Weather Flick. All rights reserved.</p>
                        <p>이 이메일은 자동으로 발송되었습니다.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            message = MessageSchema(
                subject="Weather Flick 이메일 인증",
                recipients=[email],
                body=html_content,
                subtype="html",
            )

            await self.fastmail.send_message(message)
            return True

        except Exception as e:
            self.logger.error(
                f"인증 이메일 발송 실패: {email}", extra={"error": str(e)}
            )
            raise EmailServiceError(
                message="인증 이메일 발송에 실패했습니다.",
                code="EMAIL_SEND_FAILED",
                details=[{"field": "email", "message": f"이메일 전송 실패: {str(e)}"}],
            )

    async def send_welcome_email(self, email: str, nickname: str):
        """환영 이메일 발송"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Weather Flick에 오신 것을 환영합니다!</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f6f9;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        color: white;
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 64px;
                        height: 64px;
                        border-radius: 12px;
                        margin: 0 auto 20px;
                        display: block;
                        box-shadow: 0 4px 12px rgba(255,255,255,0.2);
                    }}
                    .header h1 {{
                        margin: 0 0 10px 0;
                        font-size: 28px;
                        font-weight: 700;
                    }}
                    .header p {{
                        margin: 0;
                        font-size: 16px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                        background: white;
                    }}
                    .features {{
                        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                        border-radius: 12px;
                        padding: 25px;
                        margin: 25px 0;
                        border-left: 4px solid #10b981;
                    }}
                    .features ul {{
                        margin: 15px 0;
                        padding-left: 20px;
                    }}
                    .features li {{
                        margin: 12px 0;
                        font-size: 16px;
                        color: #065f46;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 30px;
                        background: #f8fafc;
                        color: #64748b;
                        font-size: 14px;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .footer p {{
                        margin: 8px 0;
                    }}
                    h2 {{
                        color: #1e293b;
                        font-size: 24px;
                        margin: 0 0 20px 0;
                        font-weight: 600;
                    }}
                    p {{
                        margin: 16px 0;
                        color: #475569;
                        font-size: 16px;
                    }}
                    .celebration {{
                        font-size: 20px;
                        color: #10b981;
                        font-weight: 600;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://wf-dev.seongjunlee.dev/newicon.jpg" height="200" width="200" alt="Weather Flick Logo" class="logo">
                        <h1>Weather Flick</h1>
                        <p>환영합니다!</p>
                    </div>
                    <div class="content">
                        <h2>안녕하세요, {nickname}님!</h2>
                        <p class="celebration">Weather Flick에 가입해주셔서 감사합니다! 🎉</p>

                        <div class="features">
                            <p><strong>이제 다음과 같은 서비스를 이용하실 수 있습니다:</strong></p>
                            <ul>
                                <li>🌤️ 실시간 날씨 정보</li>
                                <li>🌬️ 대기질 정보</li>
                                <li>🗺️ 지역 정보 및 맛집 추천</li>
                                <li>📱 개인화된 날씨 알림</li>
                                <li>🎯 날씨 기반 여행지 추천</li>
                            </ul>
                        </div>

                        <p>즐거운 Weather Flick 이용되세요!</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 Weather Flick. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            message = MessageSchema(
                subject="Weather Flick에 오신 것을 환영합니다!",
                recipients=[email],
                body=html_content,
                subtype="html",
            )

            await self.fastmail.send_message(message)
            return True

        except Exception as e:
            self.logger.error(
                f"환영 이메일 발송 실패: {email}", extra={"error": str(e)}
            )
            raise EmailServiceError(
                message="환영 이메일 발송에 실패했습니다.",
                code="WELCOME_EMAIL_SEND_FAILED",
            )

    async def send_temporary_password_email(self, email: str, temporary_password: str, nickname: str = None):
        """임시 비밀번호 이메일 발송"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Weather Flick 임시 비밀번호</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f4f6f9;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                        color: white;
                        padding: 40px 30px;
                        text-align: center;
                    }}
                    .logo {{
                        width: 64px;
                        height: 64px;
                        border-radius: 12px;
                        margin: 0 auto 20px;
                        display: block;
                        box-shadow: 0 4px 12px rgba(255,255,255,0.2);
                    }}
                    .header h1 {{
                        margin: 0 0 10px 0;
                        font-size: 28px;
                        font-weight: 700;
                    }}
                    .header p {{
                        margin: 0;
                        font-size: 16px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                        background: white;
                    }}
                    .temp-password {{
                        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                        border: 3px solid #f59e0b;
                        padding: 25px;
                        text-align: center;
                        border-radius: 12px;
                        margin: 30px 0;
                        font-size: 28px;
                        font-weight: 700;
                        color: #92400e;
                        letter-spacing: 2px;
                        font-family: 'Courier New', monospace;
                    }}
                    .warning {{
                        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                        border-left: 4px solid #ef4444;
                        padding: 25px;
                        margin: 25px 0;
                        border-radius: 8px;
                    }}
                    .warning h3 {{
                        margin: 0 0 15px 0;
                        color: #dc2626;
                        font-size: 18px;
                    }}
                    .warning ul {{
                        margin: 15px 0;
                        padding-left: 20px;
                    }}
                    .warning li {{
                        margin: 10px 0;
                        color: #7f1d1d;
                    }}
                    .security-notice {{
                        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                        border: 1px solid #cbd5e1;
                        padding: 25px;
                        border-radius: 12px;
                        margin: 25px 0;
                        border-left: 4px solid #3b82f6;
                    }}
                    .security-notice h4 {{
                        margin: 0 0 15px 0;
                        color: #1e40af;
                        font-size: 16px;
                    }}
                    .security-notice ul {{
                        margin: 15px 0;
                        padding-left: 20px;
                    }}
                    .security-notice li {{
                        margin: 8px 0;
                        color: #334155;
                    }}
                    .footer {{
                        text-align: center;
                        padding: 30px;
                        background: #f8fafc;
                        color: #64748b;
                        font-size: 14px;
                        border-top: 1px solid #e2e8f0;
                    }}
                    .footer p {{
                        margin: 8px 0;
                    }}
                    h2 {{
                        color: #1e293b;
                        font-size: 24px;
                        margin: 0 0 20px 0;
                        font-weight: 600;
                    }}
                    p {{
                        margin: 16px 0;
                        color: #475569;
                        font-size: 16px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://wf-dev.seongjunlee.dev/newicon.jpg" height="200" width="200" alt="Weather Flick Logo" class="logo">
                        <h1>Weather Flick</h1>
                        <p>임시 비밀번호 발급</p>
                    </div>
                    <div class="content">
                        <h2>안녕하세요{f", {nickname}" if nickname else ""}!</h2>
                        <p>요청하신 임시 비밀번호가 발급되었습니다.</p>

                        <div class="temp-password">
                            {temporary_password}
                        </div>

                        <div class="warning">
                            <h3>⚠️ 보안 주의사항</h3>
                            <ul>
                                <li><strong>이 임시 비밀번호는 24시간 후에 사용이 권장되지 않습니다.</strong></li>
                                <li><strong>로그인 후 즉시 새로운 비밀번호로 변경해주세요.</strong></li>
                                <li>이 이메일을 다른 사람과 공유하지 마세요.</li>
                                <li>본인이 요청하지 않았다면 즉시 고객센터에 문의하세요.</li>
                            </ul>
                        </div>

                        <div class="security-notice">
                            <h4>🔒 보안 가이드라인</h4>
                            <p>새 비밀번호는 다음 조건을 만족해야 합니다:</p>
                            <ul>
                                <li>8자 이상의 길이</li>
                                <li>대문자, 소문자, 숫자, 특수문자 포함</li>
                                <li>이전 비밀번호와 다른 비밀번호</li>
                            </ul>
                        </div>

                        <p>Weather Flick을 안전하게 이용해주셔서 감사합니다.</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 Weather Flick. All rights reserved.</p>
                        <p>이 이메일은 자동으로 발송되었습니다.</p>
                        <p>문의사항이 있으시면 고객센터로 연락주세요.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            message = MessageSchema(
                subject="Weather Flick 임시 비밀번호 발급",
                recipients=[email],
                body=html_content,
                subtype="html",
            )

            await self.fastmail.send_message(message)
            return True

        except Exception as e:
            self.logger.error(
                f"임시 비밀번호 이메일 발송 실패: {email}", extra={"error": str(e)}
            )
            raise EmailServiceError(
                message="임시 비밀번호 이메일 발송에 실패했습니다.",
                code="TEMP_PASSWORD_EMAIL_SEND_FAILED",
                details=[{"field": "email", "message": f"이메일 전송 실패: {str(e)}"}],
            )


# 이메일 인증 관리 클래스
class EmailVerificationService:
    """이메일 인증 관리 서비스"""

    def __init__(self):
        self.email_service = EmailService()
        self.logger = get_logger("email_verification")

    async def create_verification(
        self, db: Session, email: str, nickname: str = None
    ) -> str | None:
        """인증 코드 생성 및 이메일 발송"""
        try:
            # 기존 미사용 인증 코드 삭제
            db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.is_used == False,  # noqa: E712
            ).delete()

            # 새 인증 코드 생성
            code = self.email_service.generate_verification_code()
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

            verification = EmailVerification(
                email=email, code=code, expires_at=expires_at
            )

            db.add(verification)
            db.commit()

            # 이메일 발송
            success = await self.email_service.send_verification_email(
                email, code, nickname
            )

            if success:
                return code
            else:
                # 이메일 발송 실패 시 인증 코드 삭제
                db.delete(verification)
                db.commit()
                return None

        except EmailServiceError:
            # EmailServiceError는 이미 적절한 예외이므로 그대로 전파
            db.rollback()
            raise
        except Exception as e:
            self.logger.error(f"인증 코드 생성 실패: {email}", extra={"error": str(e)})
            db.rollback()
            raise EmailServiceError(
                message="인증 코드 생성에 실패했습니다.",
                code="VERIFICATION_CODE_CREATION_FAILED",
            )

    def verify_code(self, db: Session, email: str, code: str) -> bool:
        """인증 코드 검증"""
        try:
            verification = (
                db.query(EmailVerification)
                .filter(
                    EmailVerification.email == email,
                    EmailVerification.code == code,
                    EmailVerification.is_used == False,  # noqa: E712
                    EmailVerification.expires_at > datetime.now(timezone.utc),
                )
                .order_by(EmailVerification.id.desc())
                .first()
            )

            if verification:
                verification.is_used = True
                db.commit()
                return True
            else:
                return False

        except Exception as e:
            print(f"인증 코드 검증 실패: {e}")
            return False

    def is_email_verified(self, db: Session, email: str) -> bool:
        """이메일이 인증되었는지 확인"""
        try:
            verification = (
                db.query(EmailVerification)
                .filter(
                    EmailVerification.email == email,
                    EmailVerification.is_used == True,  # noqa: E712
                )
                .first()
            )

            return verification is not None

        except Exception as e:
            print(f"이메일 인증 상태 확인 실패: {e}")
            return False


# 서비스 인스턴스
email_service = EmailService()
email_verification_service = EmailVerificationService()
