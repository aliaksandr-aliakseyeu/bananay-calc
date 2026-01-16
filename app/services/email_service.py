"""Email service for sending emails."""
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.core.config import settings


class EmailService:
    """Email service that can send real emails via SMTP or log them to a file."""

    @staticmethod
    def _send_real_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> None:
        """
        Send real email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content (optional)
        """
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            raise ValueError("SMTP settings are not configured")

        msg = MIMEMultipart('alternative')
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        try:
            if settings.SMTP_USE_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)

            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            print(f"✅ Email sent successfully to {to_email}")
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            raise

    @staticmethod
    def send_verification_email(email: str, token: str) -> None:
        """
        Send email verification email.

        Args:
            email: User email address
            token: Verification token
        """
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        subject = "Подтвердите ваш email - Bananay"

        text_body = f"""
        Здравствуйте!

        Спасибо за регистрацию в Bananay.

        Пожалуйста, подтвердите ваш email адрес, перейдя по ссылке:
        {verification_link}

        Ссылка действительна в течение 24 часов.

        Если вы не регистрировались на нашем сервисе, проигнорируйте это письмо.

        С уважением,
        Команда Bananay
        """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Подтверждение email адреса</h2>
                <p>Здравствуйте!</p>
                <p>Спасибо за регистрацию в Bananay.</p>
                <p>Пожалуйста, подтвердите ваш email адрес, нажав на кнопку ниже:</p>
                <a href="{verification_link}" class="button">Подтвердить email</a>
                <p>Или перейдите по ссылке: <a href="{verification_link}">{verification_link}</a></p>
                <p>Ссылка действительна в течение 24 часов.</p>
                <p>Если вы не регистрировались на нашем сервисе, проигнорируйте это письмо.</p>
                <div class="footer">
                    <p>С уважением,<br>Команда Bananay</p>
                </div>
            </div>
        </body>
        </html>
        """

        print(f"\n📧 Sending verification email to: {email}")
        print(f"   USE_REAL_EMAIL setting: {settings.USE_REAL_EMAIL}")
        print(f"   SMTP configured: {bool(settings.SMTP_HOST and settings.SMTP_USER)}")

        if settings.USE_REAL_EMAIL:
            print("   → Attempting to send REAL email via SMTP...")
            EmailService._send_real_email(email, subject, html_body, text_body)
        else:
            print("   → Logging to file (mock mode)")
            email_content = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
                            TO: {email}
                            SUBJECT: {subject}

                            BODY:
                            {text_body}
                            {'=' * 80}

                        """
            EmailService._log_email(email_content)

    @staticmethod
    def send_approval_notification(email: str, company_name: str) -> None:
        """
        Send account approval notification.

        Args:
            email: User email address
            company_name: Company name
        """
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
        subject = "Ваш аккаунт одобрен! - Bananay"

        text_body = f"""
        Здравствуйте!

        Отличные новости! Ваш аккаунт для компании "{company_name}" был одобрен.

        Теперь вы можете использовать все функции нашего сервиса:
        {dashboard_url}

        С уважением,
        Команда Bananay
        """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .success {{
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🎉 Аккаунт одобрен!</h2>
                <div class="success">
                    <p><strong>Отличные новости!</strong></p>
                    <p>Ваш аккаунт для компании <strong>"{company_name}"</strong> был одобрен.</p>
                </div>
                <p>Теперь вы можете использовать все функции нашего сервиса.</p>
                <a href="{dashboard_url}" class="button">Перейти в личный кабинет</a>
                <div class="footer">
                    <p>С уважением,<br>Команда Bananay</p>
                </div>
            </div>
        </body>
        </html>
        """

        print(f"\n📧 Sending approval notification to: {email}")

        if settings.USE_REAL_EMAIL:
            print("   → Attempting to send REAL email via SMTP...")
            EmailService._send_real_email(email, subject, html_body, text_body)
        else:
            print("   → Logging to file (mock mode)")
            email_content = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
                            TO: {email}
                            SUBJECT: {subject}

                            BODY:
                            {text_body}
                            {'=' * 80}

                        """
            EmailService._log_email(email_content)

    @staticmethod
    def send_rejection_notification(email: str, company_name: str, reason: str = "") -> None:
        """
        Send account rejection notification.

        Args:
            email: User email address
            company_name: Company name
            reason: Rejection reason
        """
        subject = "Заявка отклонена - Bananay"
        reason_text = f"\n\nПричина: {reason}" if reason else ""
        reason_html = f"<p><strong>Причина:</strong> {reason}</p>" if reason else ""

        text_body = f"""
        Здравствуйте!

        К сожалению, ваша заявка для компании "{company_name}" была отклонена.{reason_text}

        Если у вас есть вопросы, свяжитесь с нами: support@bananay.com

        С уважением,
        Команда Bananay
        """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .warning {{
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                .contact {{
                    background-color: #e7f3ff;
                    border-left: 4px solid #2196F3;
                    padding: 10px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Заявка отклонена</h2>
                <div class="warning">
                    <p>Здравствуйте!</p>
                    <p>К сожалению, ваша заявка для компании
                    <strong>"{company_name}"</strong> была отклонена.</p>
                    {reason_html}
                </div>
                <div class="contact">
                    <p>Если у вас есть вопросы, свяжитесь с нами:
                    <a href="mailto:support@bananay.com">support@bananay.com</a></p>
                </div>
                <div class="footer">
                    <p>С уважением,<br>Команда Bananay</p>
                </div>
            </div>
        </body>
        </html>
        """

        print(f"\n📧 Sending rejection notification to: {email}")

        if settings.USE_REAL_EMAIL:
            print("   → Attempting to send REAL email via SMTP...")
            EmailService._send_real_email(email, subject, html_body, text_body)
        else:
            print("   → Logging to file (mock mode)")
            email_content = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
                            TO: {email}
                            SUBJECT: {subject}

                            BODY:
                            {text_body}
                            {'=' * 80}

                        """
            EmailService._log_email(email_content)

    @staticmethod
    def _log_email(content: str) -> None:
        """
        Log email content to file.

        Args:
            content: Email content to log
        """
        log_file = Path(settings.EMAIL_LOG_FILE)

        if not log_file.exists():
            log_file.touch()

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(content)


email_service = EmailService()
