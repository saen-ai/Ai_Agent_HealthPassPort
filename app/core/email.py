import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.core.logging import logger
from typing import List, Optional


async def send_email(
    to: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    Send an email using Gmail SMTP.
    
    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body
        
    Returns:
        bool: True if email sent successfully
    """
    logger.info(f"📧 Sending email to {', '.join(to)}")
    logger.debug(f"SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}, User: {settings.SMTP_USER}")
    
    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.EMAIL_FROM
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        
        # Attach plain text
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        # Attach HTML if provided
        if html_body:
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
        
        # Send email
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info(f"✅ Email sent successfully to {', '.join(to)}")
            return True
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {str(e)}")
            logger.error("⚠️  Check if you're using an App Password (not regular password) for Gmail")
            logger.error(f"   SMTP User: {settings.SMTP_USER}")
            logger.error(f"   SMTP Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            return False
        except aiosmtplib.SMTPException as e:
            logger.error(f"❌ SMTP error sending email to {to}: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to}: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """
    Send password reset email.
    
    Args:
        email: Recipient email address
        reset_token: Password reset token
        
    Returns:
        bool: True if email sent successfully
    """
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    
    subject = "Reset Your Password - Health Passport"
    
    body = f"""
    Hello,
    
    You requested to reset your password for Health Passport.
    
    Click the link below to reset your password:
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Health Passport Team
    """
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Reset Your Password</h2>
                <p>Hello,</p>
                <p>You requested to reset your password for Health Passport.</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    This link will expire in 1 hour.
                </p>
                <p style="color: #666; font-size: 14px;">
                    If you didn't request this, please ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    Best regards,<br>
                    Health Passport Team
                </p>
            </div>
        </body>
    </html>
    """
    
    return await send_email([email], subject, body, html_body)


async def send_welcome_email(email: str, name: str) -> bool:
    """
    Send welcome email to new users.
    
    Args:
        email: Recipient email address
        name: User's name
        
    Returns:
        bool: True if email sent successfully
    """
    subject = "Welcome to Health Passport!"
    
    body = f"""
    Hello {name},
    
    Welcome to Health Passport! We're excited to have you on board.
    
    You can now log in to your account and start managing your health data.
    
    Best regards,
    Health Passport Team
    """
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Welcome to Health Passport!</h2>
                <p>Hello {name},</p>
                <p>Welcome to Health Passport! We're excited to have you on board.</p>
                <p>You can now log in to your account and start managing your health data.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    Best regards,<br>
                    Health Passport Team
                </p>
            </div>
        </body>
    </html>
    """
    
    return await send_email([email], subject, body, html_body)


async def send_patient_welcome_email(
    email: str, 
    name: str, 
    patient_id: str, 
    password: str, 
    clinic_name: str
) -> bool:
    """
    Send welcome email to new patients with their login credentials.
    
    Args:
        email: Recipient email address
        name: Patient's name
        patient_id: Generated Patient ID
        password: Initial password
        clinic_name: Name of the clinic
        
    Returns:
        bool: True if email sent successfully
    """
    subject = f"Welcome to {clinic_name} - Your Patient Portal Access"
    
    body = f"""
    Hello {name},
    
    Your patient account has been created at {clinic_name}!
    
    You can now access your Patient Portal using the following credentials:
    
    Patient ID: {patient_id}
    Password: {password}
    
    Please login at the Patient Portal to view your health records, lab results, and messages from your healthcare provider.
    
    For security, we recommend changing your password after your first login.
    
    If you have any questions, please contact {clinic_name}.
    
    Best regards,
    {clinic_name}
    """
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0ea5e9;">Welcome to {clinic_name}!</h2>
                <p>Hello {name},</p>
                <p>Your patient account has been created! You can now access your Patient Portal.</p>
                
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #334155;">Your Login Credentials</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Patient ID:</td>
                            <td style="padding: 8px 0; font-weight: bold; font-family: monospace; font-size: 18px; color: #0ea5e9;">{patient_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b;">Password:</td>
                            <td style="padding: 8px 0; font-weight: bold; font-family: monospace; font-size: 18px;">{password}</td>
                        </tr>
                    </table>
                </div>
                
                <p>Through the Patient Portal, you can:</p>
                <ul style="color: #475569;">
                    <li>View your health records</li>
                    <li>Access lab results</li>
                    <li>Message your healthcare provider</li>
                    <li>See visit notes</li>
                </ul>
                
                <p style="color: #dc2626; font-size: 14px;">
                    <strong>Security Note:</strong> We recommend changing your password after your first login.
                </p>
                
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">
                <p style="color: #94a3b8; font-size: 12px;">
                    If you have any questions, please contact {clinic_name}.<br>
                    Best regards,<br>
                    <strong>{clinic_name}</strong>
                </p>
            </div>
        </body>
    </html>
    """
    
    return await send_email([email], subject, body, html_body)


async def send_otp_email(email: str, otp_code: str, purpose: str = "signup") -> bool:
    """
    Send OTP verification email.
    
    Args:
        email: Recipient email address
        otp_code: 4-digit OTP code
        purpose: Purpose of OTP (signup or login)
        
    Returns:
        bool: True if email sent successfully
    """
    purpose_text = "create your account" if purpose == "signup" else "log in"
    
    subject = f"Your {purpose.capitalize()} Verification Code - Health Passport"
    
    body = f"""
    Hello,
    
    Your verification code for Health Passport is: {otp_code}
    
    Use this code to {purpose_text}. This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    Health Passport Team
    """
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Verification Code</h2>
                <p>Hello,</p>
                <p>Your verification code for Health Passport is:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background-color: #f3f4f6; border: 2px solid #4F46E5; 
                                border-radius: 8px; padding: 20px; display: inline-block;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                                     color: #4F46E5; font-family: monospace;">
                            {otp_code}
                        </span>
                    </div>
                </div>
                <p>Use this code to {purpose_text}. This code will expire in 10 minutes.</p>
                <p style="color: #666; font-size: 14px;">
                    If you didn't request this code, please ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    Best regards,<br>
                    Health Passport Team
                </p>
            </div>
        </body>
    </html>
    """
    
    return await send_email([email], subject, body, html_body)
