"""
Email service for sending transactional emails.
Using MailerSend API for professional transactional email delivery.
"""
import os
import requests
from typing import Optional
from datetime import datetime

from app.models import PendingExternalUser, Deal, User


class EmailService:
    """Handle all email sending operations via MailerSend API"""

    def __init__(self):
        self.api_key = os.getenv("MAILERSEND_API_KEY", "")
        self.api_url = "https://api.mailersend.com/v1/email"
        self.from_email = os.getenv("FROM_EMAIL", "noreply@closeware.com")
        self.from_name = os.getenv("FROM_NAME", "Closeware")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None):
        """Internal method to send email via MailerSend API"""
        if not self.api_key:
            print(f"⚠️  MAILERSEND_API_KEY not set - email not sent to {to_email}")
            return False

        try:
            payload = {
                "from": {
                    "email": self.from_email,
                    "name": self.from_name
                },
                "to": [
                    {
                        "email": to_email
                    }
                ],
                "subject": subject,
                "html": html_body,
                "text": text_body or self._html_to_text(html_body)
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            }

            response = requests.post(self.api_url, json=payload, headers=headers)

            if response.status_code == 202:
                print(f"✅ Email sent to {to_email}: {subject}")
                return True
            else:
                print(f"❌ Failed to send email to {to_email}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)"""
        import re
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def send_external_invite_new_user(
        self,
        invite: PendingExternalUser,
        deal: Deal,
        inviter: User
    ):
        """Send invitation email to new external user"""
        invite_url = f"{self.frontend_url}/signup/invite/{invite.invite_token}"
        expires_date = invite.expires_at.strftime("%B %d, %Y at %I:%M %p")

        subject = f"{inviter.full_name} from {inviter.organization.name if inviter.organization else 'Closeware'} invited you to review a contract"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .deal-info {{ background: #F5F3EE; border-left: 4px solid #D4A017; padding: 16px; margin: 24px 0; border-radius: 4px; }}
        .deal-info strong {{ color: #1A1A18; }}
        .message {{ background: #F5F3EE; padding: 16px; margin: 24px 0; border-radius: 8px; font-style: italic; color: #4A4A45; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .expiry {{ color: #C0392B; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>You've been invited to review a contract</h1>

        <p>Hi {invite.name},</p>

        <p>{inviter.full_name} from <strong>{inviter.organization.name if inviter.organization else 'their organization'}</strong> has invited you to review a contract on Closeware.</p>

        <div class="deal-info">
            <strong>Deal:</strong> {deal.title}<br>
            <strong>Your Role:</strong> {invite.collaborator_role.replace('_', ' ').title()}
        </div>

        {f'<div class="message">"{invite.message}"</div>' if invite.message else ''}

        <p>To access the contract, create your free reviewer account:</p>

        <a href="{invite_url}" class="button">Create Account &amp; View Contract</a>

        <p class="expiry">⏱ This invitation expires on {expires_date}</p>

        <div class="footer">
            <p>Closeware – AI-Powered Deal Execution<br>
            If you didn't expect this invitation, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
You've been invited to review a contract

Hi {invite.name},

{inviter.full_name} from {inviter.organization.name if inviter.organization else 'their organization'} has invited you to review a contract on Closeware.

Deal: {deal.title}
Your Role: {invite.collaborator_role.replace('_', ' ').title()}

{f'Message from {inviter.full_name}: "{invite.message}"' if invite.message else ''}

To access the contract, create your free reviewer account:
{invite_url}

This invitation expires on {expires_date}

---
Closeware – AI-Powered Deal Execution
"""

        return self._send_email(invite.email, subject, html_body, text_body)

    def send_external_user_added_to_deal(
        self,
        user: User,
        deal: Deal,
        inviter: User,
        message: Optional[str] = None
    ):
        """Send notification to existing external user when added to a new deal"""
        deal_url = f"{self.frontend_url}/deals/{deal.id}"

        subject = f"You've been added to \"{deal.title}\""

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .deal-info {{ background: #F5F3EE; border-left: 4px solid #D4A017; padding: 16px; margin: 24px 0; border-radius: 4px; }}
        .message {{ background: #F5F3EE; padding: 16px; margin: 24px 0; border-radius: 8px; font-style: italic; color: #4A4A45; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>You've been added to a new deal</h1>

        <p>Hi {user.full_name},</p>

        <p>{inviter.full_name} from <strong>{inviter.organization.name if inviter.organization else 'Closeware'}</strong> has added you to a new deal.</p>

        <div class="deal-info">
            <strong>Deal:</strong> {deal.title}
        </div>

        {f'<div class="message">"{message}"</div>' if message else ''}

        <a href="{deal_url}" class="button">View Deal</a>

        <div class="footer">
            <p>Closeware – AI-Powered Deal Execution</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
You've been added to a new deal

Hi {user.full_name},

{inviter.full_name} from {inviter.organization.name if inviter.organization else 'Closeware'} has added you to a new deal.

Deal: {deal.title}

{f'Message: "{message}"' if message else ''}

View the deal:
{deal_url}

---
Closeware – AI-Powered Deal Execution
"""

        return self._send_email(user.email, subject, html_body, text_body)

    def send_verification_email(self, user_email: str, user_name: str, token: str):
        """Send email verification link to new user"""
        verify_url = f"{self.frontend_url}/verify-email/{token}"

        subject = "Verify your Closeware account"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .expiry {{ color: #6B6B63; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to Closeware!</h1>

        <p>Hi {user_name},</p>

        <p>Thank you for creating a Closeware account. Please verify your email address to get started.</p>

        <a href="{verify_url}" class="button">Verify Email Address</a>

        <p class="expiry">This link will expire in 24 hours.</p>

        <div class="footer">
            <p>If you didn't create this account, you can safely ignore this email.</p>
            <p>Closeware – AI-Powered Deal Execution</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
Welcome to Closeware!

Hi {user_name},

Thank you for creating a Closeware account. Please verify your email address to get started.

Verify your email:
{verify_url}

This link will expire in 24 hours.

If you didn't create this account, you can safely ignore this email.

---
Closeware – AI-Powered Deal Execution
"""

        return self._send_email(user_email, subject, html_body, text_body)

    def send_password_reset_email(self, user_email: str, user_name: str, token: str):
        """Send password reset link to user"""
        reset_url = f"{self.frontend_url}/reset-password/{token}"

        subject = "Reset your Closeware password"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .expiry {{ color: #C0392B; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reset your password</h1>

        <p>Hi {user_name},</p>

        <p>We received a request to reset your Closeware password. Click the button below to create a new password:</p>

        <a href="{reset_url}" class="button">Reset Password</a>

        <p class="expiry">⏱ This link will expire in 1 hour for security.</p>

        <div class="footer">
            <p>If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.</p>
            <p>Closeware – AI-Powered Deal Execution</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
Reset your password

Hi {user_name},

We received a request to reset your Closeware password. Click the link below to create a new password:

{reset_url}

This link will expire in 1 hour for security.

If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.

---
Closeware – AI-Powered Deal Execution
"""

        return self._send_email(user_email, subject, html_body, text_body)

    def send_signature_request(
        self,
        signer_email: str,
        signer_name: str,
        contract_title: str,
        request_id: str,
        access_token: str,
        requested_by: str,
        message: str = None,
        expires_at: datetime = None
    ):
        """Send signature request email"""
        sign_url = f"{self.frontend_url}/sign/{request_id}?token={access_token}"
        expires_text = f"by {expires_at.strftime('%B %d, %Y')}" if expires_at else ""

        subject = f"Signature Requested: {contract_title}"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .contract-info {{ background: #F5F3EE; border-left: 4px solid #D4A017; padding: 16px; margin: 24px 0; border-radius: 4px; }}
        .message {{ background: #F5F3EE; padding: 16px; margin: 24px 0; border-radius: 8px; font-style: italic; color: #4A4A45; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .warning {{ color: #C0392B; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Signature Requested</h1>

        <p>Hi {signer_name},</p>

        <p><strong>{requested_by}</strong> has requested your signature on the following contract:</p>

        <div class="contract-info">
            <strong>Contract:</strong> {contract_title}
        </div>

        {f'<div class="message">"{message}"</div>' if message else ''}

        <p>Please review the contract and sign {expires_text}:</p>

        <a href="{sign_url}" class="button">Review &amp; Sign Contract</a>

        {f'<p class="warning">⏱ This request expires {expires_text}</p>' if expires_text else ''}

        <div class="footer">
            <p>Closeware – AI-Powered Deal Execution<br>
            If you have questions, please contact {requested_by}.</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
Signature Requested: {contract_title}

Hi {signer_name},

{requested_by} has requested your signature on: {contract_title}

{f'Message: "{message}"' if message else ''}

Review and sign the contract here:
{sign_url}

{f'This request expires {expires_text}' if expires_text else ''}

---
Closeware – AI-Powered Deal Execution
"""

        return self._send_email(signer_email, subject, html_body, text_body)

    def send_contract_fully_executed_notification(
        self,
        owner_email: str,
        owner_name: str,
        contract_title: str,
        contract_draft_id: str,
        deal_name: str
    ):
        """Send notification when all signatures have been collected"""
        contract_url = f"{self.frontend_url}/deals/{contract_draft_id}"

        subject = f"✅ All Signatures Collected: {contract_title}"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .success-badge {{ display: inline-block; background: rgba(74, 124, 89, 0.1); color: #4A7C59; padding: 8px 16px; border-radius: 6px; font-weight: 600; margin-bottom: 24px; }}
        .contract-info {{ background: #F5F3EE; border-left: 4px solid #4A7C59; padding: 16px; margin: 24px 0; border-radius: 4px; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .checkmark {{ font-size: 48px; color: #4A7C59; text-align: center; margin-bottom: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✅</div>
        <h1>Contract Fully Executed</h1>

        <div class="success-badge">All Signatures Collected</div>

        <p>Hi {owner_name},</p>

        <p>Great news! All required signatures have been collected for:</p>

        <div class="contract-info">
            <strong>Contract:</strong> {contract_title}<br>
            <strong>Deal:</strong> {deal_name}
        </div>

        <p>The contract is now <strong>fully executed</strong> and legally binding.</p>

        <a href="{contract_url}" class="button">View Signed Contract</a>

        <p style="color: #6B6B63; font-size: 14px; margin-top: 24px;">
            Next steps: Download the final signed contract and archive it according to your company's document retention policy.
        </p>

        <div class="footer">
            <p>Closeware – AI-Powered Contract Verification<br>
            Never sign a contract that doesn't match reality.</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
Contract Fully Executed - All Signatures Collected

Hi {owner_name},

Great news! All required signatures have been collected for:

Contract: {contract_title}
Deal: {deal_name}

The contract is now fully executed and legally binding.

View signed contract: {contract_url}

Next steps: Download the final signed contract and archive it according to your company's document retention policy.

---
Closeware – AI-Powered Contract Verification
"""

        return self._send_email(owner_email, subject, html_body, text_body)

    def send_signature_request_expired(
        self,
        owner_email: str,
        owner_name: str,
        contract_title: str,
        signer_name: str,
        signer_email: str,
        contract_draft_id: str,
        expired_at: datetime
    ):
        """Send notification that a signature request has expired"""
        contract_url = f"{self.frontend_url}/contracts/{contract_draft_id}"
        expired_date = expired_at.strftime("%B %d, %Y")

        subject = f"⏰ Signature Request Expired: {signer_name}"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1A1A18; background: #FAF9F6; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ font-family: 'Georgia', serif; font-size: 24px; font-weight: 400; color: #1A1A18; margin: 0 0 24px 0; }}
        .warning-badge {{ display: inline-block; background: rgba(192, 57, 43, 0.1); color: #C0392B; padding: 8px 16px; border-radius: 6px; font-weight: 600; margin-bottom: 24px; }}
        .contract-info {{ background: #F5F3EE; border-left: 4px solid #C0392B; padding: 16px; margin: 24px 0; border-radius: 4px; }}
        .button {{ display: inline-block; background: #D4A017; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 500; margin: 24px 0; }}
        .button:hover {{ background: #B8860B; }}
        .footer {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid #E8E6E0; font-size: 13px; color: #6B6B63; }}
        .icon {{ font-size: 48px; text-align: center; margin-bottom: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">⏰</div>
        <h1>Signature Request Expired</h1>

        <div class="warning-badge">Action Required</div>

        <p>Hi {owner_name},</p>

        <p>A signature request has expired without being signed:</p>

        <div class="contract-info">
            <strong>Contract:</strong> {contract_title}<br>
            <strong>Requested From:</strong> {signer_name} ({signer_email})<br>
            <strong>Expired:</strong> {expired_date}
        </div>

        <p><strong>Next Steps:</strong></p>
        <ul style="color: #4A4A45;">
            <li>Review the contract and determine if signature is still needed</li>
            <li>Send a new signature request with updated terms if necessary</li>
            <li>Contact {signer_name} directly if urgent</li>
        </ul>

        <a href="{contract_url}" class="button">View Contract</a>

        <div class="footer">
            <p>Closeware – AI-Powered Contract Verification<br>
            Never sign a contract that doesn't match reality.</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
Signature Request Expired - Action Required

Hi {owner_name},

A signature request has expired without being signed:

Contract: {contract_title}
Requested From: {signer_name} ({signer_email})
Expired: {expired_date}

Next Steps:
- Review the contract and determine if signature is still needed
- Send a new signature request with updated terms if necessary
- Contact {signer_name} directly if urgent

View contract: {contract_url}

---
Closeware – AI-Powered Contract Verification
"""

        return self._send_email(owner_email, subject, html_body, text_body)


# Singleton instance
email_service = EmailService()
