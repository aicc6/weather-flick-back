import random
import string
from datetime import UTC, datetime, timedelta
from typing import Any

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

    async def send_temporary_password_email(
        self, email: str, temporary_password: str, nickname: str = None
    ):
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
            expires_at = datetime.now(UTC) + timedelta(minutes=10)

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
                    EmailVerification.expires_at > datetime.now(UTC),
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

    # ===========================================
    # 알림 관련 메서드
    # ===========================================

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        template_data: dict[str, Any] | None = None,
        template_name: str | None = None,
    ) -> bool:
        """알림 이메일 전송"""
        try:
            # 템플릿 사용 시 HTML 생성
            if template_name:
                html_content = self._render_notification_template(
                    template_name, template_data or {}
                )
            else:
                html_content = self._create_notification_html(subject, content)

            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=html_content,
                subtype="html",
            )

            fm = FastMail(self.conf)
            await fm.send_message(message)

            self.logger.info(f"Notification email sent successfully to {to_email}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to send notification email to {to_email}: {str(e)}"
            )
            return False

    async def send_weather_alert_email(
        self,
        to_email: str,
        location: str,
        weather_condition: str,
        temperature: int,
        alert_type: str = "weather_change",
    ) -> bool:
        """날씨 알림 이메일 전송"""
        try:
            # 입력 값 검증 및 정규화
            if not location:
                location = "알 수 없는 지역"
            else:
                location = str(location).strip()
                # 너무 긴 지역명 처리
                if len(location) > 50:
                    location = location[:50]
            
            if not weather_condition:
                weather_condition = "정보 없음"
            else:
                weather_condition = str(weather_condition).strip()
            
            # 온도 값 검증
            try:
                temperature = int(temperature)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid temperature value: {temperature}")
                temperature = 0
            
            self.logger.info(f"Sending weather alert email to {to_email} for location: {location}")

            if alert_type == "weather_change":
                subject = f"🌤️ {location} 날씨 변화 알림"
                content = f"현재 {weather_condition}, 기온 {temperature}°C"
            elif alert_type == "rain_alert":
                subject = f"🌧️ {location} 비 예보 알림"
                content = (
                    f"비 예보가 있습니다. 우산을 준비하세요! (현재 기온: {temperature}°C)"
                )
            elif alert_type == "extreme_weather":
                subject = f"⚠️ {location} 악천후 경보"
                content = f"악천후 경보: {weather_condition} (기온: {temperature}°C)"
            else:
                subject = f"🌤️ {location} 날씨 정보"
                content = f"날씨: {weather_condition}, 기온: {temperature}°C"

            template_data = {
                "location": location,
                "weather_condition": weather_condition,
                "temperature": str(temperature),
                "alert_type": alert_type,
            }
            
        except Exception as e:
            self.logger.error(f"Error preparing weather alert email: {str(e)}")
            self.logger.error(f"Parameters: location={location}, condition={weather_condition}, temp={temperature}")
            # 기본값으로 설정
            subject = "날씨 알림"
            content = "날씨 정보가 업데이트되었습니다."
            template_data = {"alert_type": "error"}

        return await self.send_notification_email(
            to_email=to_email,
            subject=subject,
            content=content,
            template_data=template_data,
            template_name="weather_alert",
        )

    async def send_travel_plan_email(
        self,
        to_email: str,
        plan_title: str,
        message: str,
        notification_type: str = "travel_update",
    ) -> bool:
        """여행 계획 관련 이메일 전송"""

        if notification_type == "travel_update":
            subject = f"✈️ 여행 계획 업데이트: {plan_title}"
        elif notification_type == "travel_reminder":
            subject = f"📅 여행 계획 리마인더: {plan_title}"
        elif notification_type == "travel_recommendation":
            subject = f"🌟 여행 추천: {plan_title}"
        else:
            subject = f"✈️ {plan_title}"

        template_data = {
            "plan_title": plan_title,
            "message": message,
            "notification_type": notification_type,
        }

        return await self.send_notification_email(
            to_email=to_email,
            subject=subject,
            content=message,
            template_data=template_data,
            template_name="travel_plan",
        )

    async def send_marketing_email(
        self, to_email: str, subject: str, content: str, campaign_id: str | None = None
    ) -> bool:
        """마케팅 이메일 전송"""

        template_data = {"campaign_id": campaign_id or "", "content": content}

        return await self.send_notification_email(
            to_email=to_email,
            subject=subject,
            content=content,
            template_data=template_data,
            template_name="marketing",
        )

    async def send_contact_answer_email(
        self, to_email: str, contact_title: str, answer_content: str, contact_id: int
    ) -> bool:
        """문의 답변 이메일 전송"""

        subject = "문의하신 내용에 답변이 등록되었습니다"

        # HTML 템플릿 생성
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .message-box {{
                    background: #f0f9ff;
                    border-left: 4px solid #3b82f6;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .inquiry-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #1e40af;
                    margin-bottom: 10px;
                }}
                .answer-content {{
                    background: #f8fafc;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    white-space: pre-wrap;
                }}
                .cta-button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    margin-top: 20px;
                }}
                .footer {{
                    text-align: center;
                    padding: 30px;
                    background: #f8fafc;
                    color: #64748b;
                    font-size: 14px;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Weather Flick</h1>
                    <p style="margin-top: 10px; font-size: 18px;">문의 답변 알림</p>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b;">안녕하세요!</h2>
                    <p>문의하신 내용에 대한 답변이 등록되었습니다.</p>

                    <div class="message-box">
                        <div class="inquiry-title">📝 문의 제목</div>
                        <div>{contact_title}</div>
                    </div>

                    <h3 style="color: #1e293b; margin-top: 30px;">💬 답변 내용</h3>
                    <div class="answer-content">{answer_content}</div>

                    <p style="margin-top: 30px;">자세한 내용은 Weather Flick 웹사이트에서 확인하실 수 있습니다.</p>

                    <a href="https://wf-dev.seongjunlee.dev/contact" class="cta-button">답변 확인하기</a>
                </div>
                <div class="footer">
                    <p>이 이메일은 Weather Flick에서 발송되었습니다.</p>
                    <p>궁금하신 점이 있으시면 언제든지 문의해주세요.</p>
                </div>
            </div>
        </body>
        </html>
        """

        message = MessageSchema(
            subject=subject, recipients=[to_email], body=html_content, subtype="html"
        )

        try:
            await self.fastmail.send_message(message)
            self.logger.info(f"Contact answer email sent to {to_email}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send contact answer email: {str(e)}")
            return False

    def _create_notification_html(self, subject: str, content: str) -> str:
        """기본 알림 HTML 템플릿 생성"""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f6f9;
                }}
                .container {{
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
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px 30px;
                    border-top: 1px solid #E5E7EB;
                    color: #6B7280;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Weather Flick</div>
                    <h1>{subject}</h1>
                </div>
                <div class="content">
                    <div>{content.replace(chr(10), '<br>')}</div>
                </div>
                <div class="footer">
                    <p>이 이메일은 Weather Flick에서 발송되었습니다.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    def _render_notification_template(
        self, template_name: str, data: dict[str, Any]
    ) -> str:
        """알림 템플릿 렌더링"""
        templates = {
            "weather_alert": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>날씨 알림</title>
                <style>
                    body {{ font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f6f9; }}
                    .container {{ background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                    .weather-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .location {{ font-size: 20px; font-weight: bold; color: #2563eb; }}
                    .weather-info {{ font-size: 18px; margin: 10px 0; }}
                    .temperature {{ font-size: 24px; font-weight: bold; color: #dc2626; }}
                    .content {{ padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌤️ 날씨 알림</h1>
                    </div>
                    <div class="content">
                        <div class="weather-card">
                            <div class="location">📍 {location}</div>
                            <div class="weather-info">날씨: {weather_condition}</div>
                            <div class="temperature">🌡️ {temperature}°C</div>
                        </div>
                        <p>Weather Flick에서 제공하는 실시간 날씨 정보입니다.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "travel_plan": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>여행 계획 알림</title>
                <style>
                    body {{ font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f6f9; }}
                    .container {{ background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                    .plan-card {{ background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .plan-title {{ font-size: 20px; font-weight: bold; color: #0ea5e9; }}
                    .message {{ font-size: 16px; margin: 15px 0; line-height: 1.6; }}
                    .content {{ padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✈️ 여행 계획 알림</h1>
                    </div>
                    <div class="content">
                        <div class="plan-card">
                            <div class="plan-title">✈️ {plan_title}</div>
                            <div class="message">{message}</div>
                        </div>
                        <p>더 자세한 정보는 Weather Flick 앱에서 확인하세요.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "marketing": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Weather Flick 소식</title>
                <style>
                    body {{ font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f6f9; }}
                    .container {{ background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
                    .marketing-card {{ background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .content {{ font-size: 16px; line-height: 1.6; }}
                    .main-content {{ padding: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📢 Weather Flick 소식</h1>
                    </div>
                    <div class="main-content">
                        <div class="marketing-card">
                            <div class="content">{content}</div>
                        </div>
                        <p>Weather Flick 팀이 전해드리는 특별한 소식입니다.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
        }

        template_html = templates.get(template_name, templates["weather_alert"])
        return template_html.format(**data)


# 서비스 인스턴스
email_service = EmailService()
email_verification_service = EmailVerificationService()
