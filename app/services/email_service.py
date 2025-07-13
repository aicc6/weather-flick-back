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
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .verification-code {{ background: #fff; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; font-size: 24px; font-weight: bold; color: #667eea; border: 2px dashed #667eea; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌤️ Weather Flick</h1>
                        <p>이메일 인증</p>
                    </div>
                    <div class="content">
                        <h2>안녕하세요{f", {nickname}" if nickname else ""}!</h2>
                        <p>Weather Flick 회원가입을 위한 이메일 인증 코드입니다.</p>

                        <div class="verification-code">
                            {code}
                        </div>

                        <p><strong>인증 코드는 10분 후에 만료됩니다.</strong></p>

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
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌤️ Weather Flick</h1>
                        <p>환영합니다!</p>
                    </div>
                    <div class="content">
                        <h2>안녕하세요, {nickname}님!</h2>
                        <p>Weather Flick에 가입해주셔서 감사합니다! 🎉</p>

                        <p>이제 다음과 같은 서비스를 이용하실 수 있습니다:</p>
                        <ul>
                            <li>🌤️ 실시간 날씨 정보</li>
                            <li>🌬️ 대기질 정보</li>
                            <li>🗺️ 지역 정보 및 맛집 추천</li>
                            <li>📱 개인화된 날씨 알림</li>
                        </ul>

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
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .temp-password {{ background: #fff; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0; font-size: 20px; font-weight: bold; color: #e74c3c; border: 2px solid #e74c3c; }}
                    .warning {{ background: #fff5f5; border-left: 4px solid #e74c3c; padding: 15px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                    .security-notice {{ background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌤️ Weather Flick</h1>
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
