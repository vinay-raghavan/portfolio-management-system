# Notification System Implementation Guide (Section 1.6)

> **Branch:** `phase-1/notifications`  
> **Timeline:** Week 4-5  
> **Goal:** Modular notification system that can send alerts via multiple channels

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Existing Infrastructure](#2-existing-infrastructure)
3. [Implementation Components](#3-implementation-components)
4. [Provider Implementations](#4-provider-implementations)
5. [NotificationService Orchestrator](#5-notificationservice-orchestrator)
6. [Database Models](#6-database-models)
7. [Configuration](#7-configuration)
8. [Celery Tasks](#8-celery-tasks)
9. [Frontend Components](#9-frontend-components)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION TRIGGERS                             │
│  Order Events │ Price Alerts │ Algo Signals │ Risk Breaches         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SERVICE (Orchestrator)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ User Prefs   │  │ Rate Limiter │  │ Deduplication│               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Quiet Hours  │  │ Templates    │  │ Fallback     │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Email Provider │      │  SMS Provider   │      │ WebSocket Prov  │
│  (SMTP/SendGrid)│      │  (Twilio)       │      │ (Real-time UI)  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  User's Inbox   │      │  User's Phone   │      │  Browser/App    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## 2. Existing Infrastructure

### What Already Exists ✅

| Component | Location | Status |
|-----------|----------|--------|
| `NotificationProvider` base class | `backend/app/providers/notification/base.py` | ✅ Complete |
| `NotificationPriority` enum | `backend/app/providers/notification/base.py` | ✅ Complete |
| `NotificationType` enum | `backend/app/providers/notification/base.py` | ✅ Complete |
| `NotificationProviderFactory` | `backend/app/providers/notification/factory.py` | ✅ Complete (empty registry) |
| Frontend notification store | `frontend/src/store/notifications.ts` | ✅ Complete |
| Frontend WebSocket store | `frontend/src/store/websocket.ts` | ✅ Complete |
| Alert checking Celery task | `worker/worker/tasks/alerts.py` | 🟡 Stub only |
| Notification preferences UI | `frontend/src/components/alerts/NotificationPreferences.tsx` | 🟡 Frontend only |

### What Needs Implementation ❌

| Component | Priority | Effort |
|-----------|----------|--------|
| `ConsoleNotificationProvider` (stub) | P0 - Critical | 30 min |
| `NotificationService` orchestrator | P0 - Critical | 2-3 hrs |
| `NotificationPreferences` DB model | P0 - Critical | 1 hr |
| `EmailNotificationProvider` | P1 - High | 2-3 hrs |
| `SMSNotificationProvider` (Twilio) | P1 - High | 2 hrs |
| `WebSocketNotificationProvider` | P1 - High | 3 hrs |
| `WhatsAppNotificationProvider` | P2 - Medium | 2 hrs |
| Notification history model | P2 - Medium | 1 hr |
| Settings configuration | P1 - High | 1 hr |
| Celery tasks integration | P1 - High | 2 hrs |

---

## 3. Implementation Components

### 3.1 Directory Structure

```
backend/app/
├── providers/
│   └── notification/
│       ├── __init__.py           # Exports (exists)
│       ├── base.py               # Abstract base class (exists)
│       ├── factory.py            # Provider factory (exists, needs registration)
│       ├── console.py            # NEW: Console/logging provider (stub)
│       ├── email.py              # NEW: Email provider (SMTP/SendGrid/SES)
│       ├── sms.py                # NEW: SMS provider (Twilio)
│       ├── whatsapp.py           # NEW: WhatsApp provider (Twilio)
│       └── websocket.py          # NEW: WebSocket provider
├── modules/
│   └── notifications/            # NEW: Notification module
│       ├── __init__.py
│       ├── models.py             # NotificationPreferences, NotificationHistory
│       ├── schemas.py            # Pydantic schemas
│       ├── service.py            # NotificationService orchestrator
│       ├── router.py             # API endpoints
│       └── templates.py          # Message templates
└── core/
    └── config.py                 # Add notification settings
```

---

## 4. Provider Implementations

### 4.1 Console Notification Provider (Stub/Dev)

**Purpose:** Development/testing provider that logs notifications to console. Prevents runtime errors when no real providers are configured.

**File:** `backend/app/providers/notification/console.py`

```python
"""Console notification provider for development and testing."""

import logging
from typing import Any

from app.providers.notification.base import (
    NotificationProvider,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class ConsoleNotificationProvider(NotificationProvider):
    """Notification provider that logs to console.
    
    Use this for development/testing when real providers aren't configured.
    Always succeeds and logs the notification details.
    """

    name = "console"
    supports_rich_content = False

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Log notification to console."""
        log_level = {
            NotificationPriority.LOW: logging.DEBUG,
            NotificationPriority.MEDIUM: logging.INFO,
            NotificationPriority.HIGH: logging.WARNING,
            NotificationPriority.CRITICAL: logging.ERROR,
        }.get(priority, logging.INFO)

        logger.log(
            log_level,
            f"[NOTIFICATION] user={user_id} type={notification_type.value} "
            f"priority={priority.value}\n"
            f"  Title: {title}\n"
            f"  Message: {message}\n"
            f"  Data: {data}"
        )
        return True

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Log bulk notification to console."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(
                user_id, title, message, priority, notification_type
            )
        return results

    async def is_available(self, user_id: str) -> bool:
        """Console is always available."""
        return True
```

---

### 4.2 SMS Notification Provider (Twilio)

**Purpose:** Send SMS notifications via Twilio API.

**Reference:** Extracted from [stock-tracker-agent](https://github.com/IAmTomShaw/stock-tracker-agent)

**File:** `backend/app/providers/notification/sms.py`

```python
"""SMS notification provider using Twilio."""

import logging
from typing import Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings
from app.providers.notification.base import (
    NotificationProvider,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class SMSNotificationProvider(NotificationProvider):
    """SMS notification provider using Twilio.

    Requires the following settings:
    - TWILIO_ACCOUNT_SID: Twilio account SID
    - TWILIO_AUTH_TOKEN: Twilio auth token
    - TWILIO_PHONE_NUMBER: Twilio phone number to send from

    Dependencies:
        pip install twilio
    """

    name = "sms"
    supports_rich_content = False
    MAX_SMS_LENGTH = 160  # Standard SMS character limit

    def __init__(self):
        """Initialize Twilio client."""
        self._client: Client | None = None
        self._from_number: str = ""
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Twilio client if credentials are available."""
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)

        if account_sid and auth_token and from_number:
            try:
                self._client = Client(account_sid, auth_token)
                self._from_number = from_number
                logger.info("Twilio SMS client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self._client = None
        else:
            logger.warning(
                "Twilio credentials not configured. SMS notifications disabled."
            )

    async def _get_user_phone(self, user_id: str) -> str | None:
        """Get user's phone number from notification preferences.

        TODO: Implement database lookup for user phone number.
        """
        # Placeholder - implement with NotificationPreferences model
        # from app.modules.notifications.models import NotificationPreferences
        # prefs = await NotificationPreferences.get_by_user(user_id)
        # return prefs.phone_number if prefs and prefs.sms_enabled else None
        return None

    def _format_sms_body(self, title: str, message: str) -> str:
        """Format SMS body within character limit.

        Format: "TITLE: message" truncated to 160 chars
        """
        full_message = f"{title}: {message}"
        if len(full_message) <= self.MAX_SMS_LENGTH:
            return full_message
        # Truncate with ellipsis
        return full_message[:self.MAX_SMS_LENGTH - 3] + "..."

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send SMS notification to a user."""
        if not self._client:
            logger.warning("Twilio client not initialized, skipping SMS")
            return False

        phone_number = await self._get_user_phone(user_id)
        if not phone_number:
            logger.debug(f"No phone number for user {user_id}")
            return False

        sms_body = self._format_sms_body(title, message)

        try:
            self._client.messages.create(
                to=phone_number,
                from_=self._from_number,
                body=sms_body,
            )
            logger.info(f"SMS sent to user {user_id}")
            return True
        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS to {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS to {user_id}: {e}")
            return False

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Send SMS to multiple users."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(
                user_id, title, message, priority, notification_type
            )
        return results

    async def is_available(self, user_id: str) -> bool:
        """Check if SMS is available for user."""
        if not self._client:
            return False
        phone = await self._get_user_phone(user_id)
        return phone is not None
```

---

### 4.3 Email Notification Provider (SMTP/SendGrid)

**Purpose:** Send email notifications with support for HTML content and templates.

**File:** `backend/app/providers/notification/email.py`

```python
"""Email notification provider with SMTP and SendGrid support."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from app.core.config import settings
from app.providers.notification.base import (
    NotificationProvider,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class EmailNotificationProvider(NotificationProvider):
    """Email notification provider supporting SMTP and SendGrid.

    Configuration via settings:
    - EMAIL_PROVIDER: "smtp" | "sendgrid" | "ses"
    - EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD
    - EMAIL_FROM: Sender email address
    - SENDGRID_API_KEY: API key for SendGrid (if using SendGrid)

    Dependencies:
        pip install sendgrid  # If using SendGrid
    """

    name = "email"
    supports_rich_content = True  # Supports HTML emails

    def __init__(self):
        """Initialize email provider based on configuration."""
        self._provider = getattr(settings, "EMAIL_PROVIDER", "smtp")
        self._from_email = getattr(settings, "EMAIL_FROM", "alerts@portfolio.app")
        self._initialized = False
        self._initialize_provider()

    def _initialize_provider(self) -> None:
        """Initialize the configured email provider."""
        if self._provider == "sendgrid":
            self._initialize_sendgrid()
        elif self._provider == "smtp":
            self._initialize_smtp()
        else:
            logger.warning(f"Unknown email provider: {self._provider}")

    def _initialize_smtp(self) -> None:
        """Initialize SMTP settings."""
        self._smtp_host = getattr(settings, "EMAIL_SMTP_HOST", "")
        self._smtp_port = getattr(settings, "EMAIL_SMTP_PORT", 587)
        self._smtp_user = getattr(settings, "EMAIL_SMTP_USER", "")
        self._smtp_password = getattr(settings, "EMAIL_SMTP_PASSWORD", "")

        if self._smtp_host and self._smtp_user:
            self._initialized = True
            logger.info("SMTP email provider initialized")
        else:
            logger.warning("SMTP settings incomplete. Email notifications disabled.")

    def _initialize_sendgrid(self) -> None:
        """Initialize SendGrid client."""
        api_key = getattr(settings, "SENDGRID_API_KEY", "")
        if api_key:
            try:
                from sendgrid import SendGridAPIClient
                self._sendgrid_client = SendGridAPIClient(api_key)
                self._initialized = True
                logger.info("SendGrid email provider initialized")
            except ImportError:
                logger.error("sendgrid package not installed")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {e}")
        else:
            logger.warning("SendGrid API key not configured")

    async def _get_user_email(self, user_id: str) -> str | None:
        """Get user's email address from notification preferences.

        TODO: Implement database lookup.
        """
        # Placeholder - implement with NotificationPreferences model
        return None

    def _build_html_email(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        notification_type: NotificationType,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Build HTML email content."""
        priority_colors = {
            NotificationPriority.LOW: "#6b7280",      # Gray
            NotificationPriority.MEDIUM: "#3b82f6",   # Blue
            NotificationPriority.HIGH: "#f59e0b",     # Amber
            NotificationPriority.CRITICAL: "#ef4444", # Red
        }
        color = priority_colors.get(priority, "#3b82f6")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {color}; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px;
                          font-size: 12px; background: {color}20; color: {color}; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">{title}</h2>
                </div>
                <div class="content">
                    <span class="badge">{notification_type.value.replace('_', ' ').title()}</span>
                    <p style="margin-top: 15px; line-height: 1.6;">{message}</p>
                </div>
            </div>
        </body>
        </html>
        """

    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = to_email

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.sendmail(self._from_email, to_email, msg.as_string())

            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False

    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """Send email via SendGrid."""
        try:
            from sendgrid.helpers.mail import Mail

            message = Mail(
                from_email=self._from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )
            response = self._sendgrid_client.send(message)
            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send email notification to a user."""
        if not self._initialized:
            logger.debug("Email provider not initialized")
            return False

        email = await self._get_user_email(user_id)
        if not email:
            logger.debug(f"No email for user {user_id}")
            return False

        # Build email content
        subject = f"[{priority.value.upper()}] {title}"
        html_content = self._build_html_email(title, message, priority, notification_type, data)
        text_content = f"{title}\n\n{message}"

        # Send via configured provider
        if self._provider == "sendgrid":
            return await self._send_sendgrid(email, subject, html_content, text_content)
        else:
            return await self._send_smtp(email, subject, html_content, text_content)

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Send email to multiple users."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(
                user_id, title, message, priority, notification_type
            )
        return results

    async def is_available(self, user_id: str) -> bool:
        """Check if email is available for user."""
        if not self._initialized:
            return False
        email = await self._get_user_email(user_id)
        return email is not None
```

---

### 4.4 WebSocket Notification Provider

**Purpose:** Real-time notifications to connected browser clients via WebSocket.

**File:** `backend/app/providers/notification/websocket.py`

```python
"""WebSocket notification provider for real-time UI notifications."""

import json
import logging
from typing import Any

from app.providers.notification.base import (
    NotificationProvider,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class WebSocketNotificationProvider(NotificationProvider):
    """WebSocket notification provider for real-time browser notifications.

    Integrates with the existing WebSocket connection manager to push
    notifications directly to connected clients.

    Requires:
    - WebSocket connection manager with user session tracking
    - Frontend WebSocket store to receive messages
    """

    name = "websocket"
    supports_rich_content = True  # Can send structured JSON data

    def __init__(self):
        """Initialize WebSocket provider."""
        self._connection_manager = None
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Get reference to WebSocket connection manager."""
        try:
            # Import connection manager from your WebSocket module
            # from app.api.websocket import connection_manager
            # self._connection_manager = connection_manager
            logger.info("WebSocket notification provider initialized")
        except ImportError:
            logger.warning("WebSocket connection manager not available")

    def _build_notification_payload(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        notification_type: NotificationType,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build WebSocket notification payload.

        Returns JSON-serializable dict matching frontend Notification interface.
        """
        return {
            "type": "notification",
            "payload": {
                "title": title,
                "message": message,
                "priority": priority.value,
                "notification_type": notification_type.value,
                "data": data or {},
            }
        }

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send notification via WebSocket to connected user."""
        if not self._connection_manager:
            logger.debug("WebSocket manager not available")
            return False

        payload = self._build_notification_payload(
            title, message, priority, notification_type, data
        )

        try:
            # Send to user's WebSocket connections
            await self._connection_manager.send_to_user(
                user_id,
                json.dumps(payload),
            )
            logger.debug(f"WebSocket notification sent to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"WebSocket send failed for user {user_id}: {e}")
            return False

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, bool]:
        """Send notification to multiple users via WebSocket."""
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(
                user_id, title, message, priority, notification_type
            )
        return results

    async def is_available(self, user_id: str) -> bool:
        """Check if user has active WebSocket connection."""
        if not self._connection_manager:
            return False
        return self._connection_manager.is_user_connected(user_id)

    async def broadcast(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Broadcast notification to all connected users.

        Returns:
            Number of users notified
        """
        if not self._connection_manager:
            return 0

        payload = self._build_notification_payload(
            title, message, priority, notification_type, data
        )

        try:
            count = await self._connection_manager.broadcast(json.dumps(payload))
            logger.info(f"Broadcast notification sent to {count} users")
            return count
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return 0
```

---

## 5. NotificationService Orchestrator

**Purpose:** Central service that routes notifications to appropriate providers based on user preferences, handles deduplication, rate limiting, and fallback logic.

**File:** `backend/app/modules/notifications/service.py`

```python
"""Notification service orchestrator."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from app.core.config import settings
from app.providers.notification.base import (
    NotificationPriority,
    NotificationType,
)
from app.providers.notification.factory import NotificationProviderFactory

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrates notification delivery across multiple channels.

    Features:
    - Routes to appropriate channels based on user preferences
    - Deduplicates identical notifications within time window
    - Rate limiting per user/channel
    - Fallback to alternate channels on failure
    - Quiet hours enforcement
    - Priority-based channel selection

    Usage:
        service = NotificationService()
        await service.notify(
            user_id="user123",
            title="Order Filled",
            message="Your order for 100 RELIANCE shares has been filled",
            priority=NotificationPriority.MEDIUM,
            notification_type=NotificationType.ORDER_FILLED,
        )
    """

    # Priority to channels mapping (override user preferences for critical)
    PRIORITY_CHANNELS = {
        NotificationPriority.CRITICAL: ["sms", "email", "websocket"],  # All channels
        NotificationPriority.HIGH: ["email", "websocket"],
        NotificationPriority.MEDIUM: ["websocket", "email"],
        NotificationPriority.LOW: ["websocket"],
    }

    # Deduplication window in seconds
    DEDUP_WINDOW_SECONDS = 300  # 5 minutes

    def __init__(self):
        """Initialize notification service."""
        self._dedup_cache: dict[str, datetime] = {}  # hash -> timestamp
        self._rate_limits: dict[str, list[datetime]] = {}  # user_channel -> timestamps

    def _get_dedup_key(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: NotificationType,
    ) -> str:
        """Generate deduplication key for a notification."""
        content = f"{user_id}:{notification_type.value}:{title}:{message}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_duplicate(self, dedup_key: str) -> bool:
        """Check if notification is a duplicate within dedup window."""
        if dedup_key not in self._dedup_cache:
            return False

        last_sent = self._dedup_cache[dedup_key]
        window = timedelta(seconds=self.DEDUP_WINDOW_SECONDS)

        if datetime.now() - last_sent < window:
            logger.debug(f"Duplicate notification suppressed: {dedup_key}")
            return True
        return False

    def _mark_sent(self, dedup_key: str) -> None:
        """Mark notification as sent for deduplication."""
        self._dedup_cache[dedup_key] = datetime.now()

        # Cleanup old entries (keep last 1000)
        if len(self._dedup_cache) > 1000:
            sorted_keys = sorted(
                self._dedup_cache.keys(),
                key=lambda k: self._dedup_cache[k],
            )
            for key in sorted_keys[:500]:
                del self._dedup_cache[key]

    async def _get_user_channels(
        self,
        user_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> list[str]:
        """Get enabled channels for user based on preferences and priority.

        TODO: Implement with NotificationPreferences model lookup.
        """
        # For CRITICAL priority, use all available channels
        if priority == NotificationPriority.CRITICAL:
            return self.PRIORITY_CHANNELS[priority]

        # Placeholder - implement with real preferences lookup
        # prefs = await NotificationPreferences.get_by_user(user_id)
        # return prefs.get_channels_for_type(notification_type)

        # Default: use priority-based channels
        return self.PRIORITY_CHANNELS.get(priority, ["websocket"])

    def _is_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is in user's quiet hours.

        TODO: Implement with user preferences.
        """
        # Placeholder - implement with real preferences
        return False

    async def notify(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        data: dict[str, Any] | None = None,
        skip_dedup: bool = False,
        force_channels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send notification to user via appropriate channels.

        Args:
            user_id: User identifier
            title: Notification title
            message: Notification body
            priority: Priority level
            notification_type: Type of notification
            data: Additional structured data
            skip_dedup: Skip deduplication check
            force_channels: Override channel selection

        Returns:
            Dict with delivery status per channel
        """
        result = {
            "user_id": user_id,
            "notification_type": notification_type.value,
            "channels": {},
            "status": "pending",
        }

        # Check deduplication
        if not skip_dedup:
            dedup_key = self._get_dedup_key(user_id, title, message, notification_type)
            if self._is_duplicate(dedup_key):
                result["status"] = "deduplicated"
                return result

        # Check quiet hours (skip for CRITICAL)
        if priority != NotificationPriority.CRITICAL and self._is_quiet_hours(user_id):
            result["status"] = "quiet_hours"
            logger.debug(f"Notification skipped due to quiet hours for {user_id}")
            return result

        # Get channels to notify
        channels = force_channels or await self._get_user_channels(
            user_id, notification_type, priority
        )

        # Send via each channel
        any_success = False
        for channel_name in channels:
            try:
                provider = NotificationProviderFactory.get_provider(channel_name)

                # Check if channel is available for user
                if not await provider.is_available(user_id):
                    result["channels"][channel_name] = "unavailable"
                    continue

                # Send notification
                success = await provider.send(
                    user_id=user_id,
                    title=title,
                    message=message,
                    priority=priority,
                    notification_type=notification_type,
                    data=data,
                )

                result["channels"][channel_name] = "sent" if success else "failed"
                if success:
                    any_success = True

            except ValueError as e:
                # Provider not registered
                result["channels"][channel_name] = f"error: {e}"
                logger.warning(f"Provider {channel_name} not available: {e}")
            except Exception as e:
                result["channels"][channel_name] = f"error: {e}"
                logger.error(f"Error sending via {channel_name}: {e}")

        # Mark as sent for deduplication
        if any_success and not skip_dedup:
            self._mark_sent(dedup_key)

        result["status"] = "sent" if any_success else "failed"
        return result

    async def notify_bulk(
        self,
        user_ids: list[str],
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
    ) -> dict[str, Any]:
        """Send notification to multiple users.

        Returns:
            Dict with per-user delivery status
        """
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.notify(
                user_id, title, message, priority, notification_type
            )
        return results


# Singleton instance
notification_service = NotificationService()
```

---

## 6. Database Models

### 6.1 Notification Preferences Model

**File:** `backend/app/modules/notifications/models.py`

```python
"""Notification-related database models."""

from datetime import time
from sqlalchemy import Boolean, Column, String, Time, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class NotificationPreferences(Base):
    """User notification preferences.

    Stores per-user configuration for notification channels and preferences.
    """

    __tablename__ = "notification_preferences"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    # Email settings
    email_enabled = Column(Boolean, default=True)
    email_address = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False)

    # SMS settings
    sms_enabled = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)  # E.164 format: +919876543210
    phone_verified = Column(Boolean, default=False)

    # WhatsApp settings
    whatsapp_enabled = Column(Boolean, default=False)
    whatsapp_number = Column(String, nullable=True)

    # Push notification settings
    push_enabled = Column(Boolean, default=True)
    push_tokens = Column(JSON, default=list)  # FCM/APNs tokens

    # In-app (WebSocket) settings
    websocket_enabled = Column(Boolean, default=True)
    sound_enabled = Column(Boolean, default=True)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(Time, default=time(22, 0))  # 10 PM
    quiet_hours_end = Column(Time, default=time(8, 0))     # 8 AM

    # Per-notification-type channel preferences
    # JSON format: {"order_filled": ["email", "websocket"], "price_alert": ["sms", "email"]}
    type_preferences = Column(JSON, default=dict)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

    def get_channels_for_type(self, notification_type: str) -> list[str]:
        """Get enabled channels for a notification type."""
        # Check type-specific preferences first
        if self.type_preferences and notification_type in self.type_preferences:
            return self.type_preferences[notification_type]

        # Fall back to all enabled channels
        channels = []
        if self.websocket_enabled:
            channels.append("websocket")
        if self.email_enabled and self.email_address:
            channels.append("email")
        if self.sms_enabled and self.phone_number:
            channels.append("sms")
        if self.whatsapp_enabled and self.whatsapp_number:
            channels.append("whatsapp")
        return channels

    def is_quiet_hours(self, current_time: time) -> bool:
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled:
            return False

        start = self.quiet_hours_start
        end = self.quiet_hours_end

        if start <= end:
            # Normal range (e.g., 10:00 to 18:00)
            return start <= current_time <= end
        else:
            # Overnight range (e.g., 22:00 to 08:00)
            return current_time >= start or current_time <= end


class NotificationHistory(Base):
    """Notification delivery history.

    Tracks all sent notifications for auditing and analytics.
    """

    __tablename__ = "notification_history"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Notification content
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    data = Column(JSON, nullable=True)

    # Delivery tracking
    channels_attempted = Column(JSON, default=list)  # ["email", "sms"]
    channels_succeeded = Column(JSON, default=list)  # ["email"]
    channels_failed = Column(JSON, default=list)     # ["sms"]

    # Status
    status = Column(String, default="pending")  # pending, sent, failed, deduplicated
    error_message = Column(String, nullable=True)

    # Timestamps handled by Base class mixin

    # Relationships
    user = relationship("User", back_populates="notification_history")
```

### 6.2 Pydantic Schemas

**File:** `backend/app/modules/notifications/schemas.py`

```python
"""Notification schemas for API requests/responses."""

from datetime import time
from pydantic import BaseModel, EmailStr, Field
from typing import Any


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences."""

    email_enabled: bool | None = None
    email_address: EmailStr | None = None

    sms_enabled: bool | None = None
    phone_number: str | None = Field(None, pattern=r"^\+[1-9]\d{1,14}$")  # E.164

    whatsapp_enabled: bool | None = None
    whatsapp_number: str | None = Field(None, pattern=r"^\+[1-9]\d{1,14}$")

    push_enabled: bool | None = None
    websocket_enabled: bool | None = None
    sound_enabled: bool | None = None

    quiet_hours_enabled: bool | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None

    type_preferences: dict[str, list[str]] | None = None


class NotificationPreferencesResponse(BaseModel):
    """Schema for notification preferences response."""

    user_id: str
    email_enabled: bool
    email_address: str | None
    email_verified: bool

    sms_enabled: bool
    phone_number: str | None
    phone_verified: bool

    whatsapp_enabled: bool
    whatsapp_number: str | None

    push_enabled: bool
    websocket_enabled: bool
    sound_enabled: bool

    quiet_hours_enabled: bool
    quiet_hours_start: time | None
    quiet_hours_end: time | None

    type_preferences: dict[str, list[str]]

    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    """Schema for manually sending a notification."""

    user_id: str
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=1000)
    priority: str = "medium"
    notification_type: str = "system_alert"
    data: dict[str, Any] | None = None
    channels: list[str] | None = None  # Force specific channels


class NotificationHistoryResponse(BaseModel):
    """Schema for notification history entry."""

    id: str
    title: str
    message: str
    notification_type: str
    priority: str
    status: str
    channels_succeeded: list[str]
    created_at: str

    class Config:
        from_attributes = True
```

---

## 7. Configuration

Add these settings to `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # ===================
    # NOTIFICATION SETTINGS
    # ===================

    # Email Configuration
    NOTIFICATION_EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: str = "smtp"  # smtp | sendgrid | ses
    EMAIL_SMTP_HOST: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USER: str = ""
    EMAIL_SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "alerts@portfolio.app"
    SENDGRID_API_KEY: str = ""

    # SMS Configuration (Twilio)
    NOTIFICATION_SMS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""  # E.164 format: +1234567890

    # WhatsApp Configuration (Twilio)
    NOTIFICATION_WHATSAPP_ENABLED: bool = False
    TWILIO_WHATSAPP_NUMBER: str = ""  # whatsapp:+1234567890

    # Push Notifications (FCM)
    NOTIFICATION_PUSH_ENABLED: bool = False
    FCM_SERVER_KEY: str = ""
    FCM_PROJECT_ID: str = ""

    # Rate Limiting
    NOTIFICATION_RATE_LIMIT_PER_HOUR: int = 60
    NOTIFICATION_RATE_LIMIT_PER_DAY: int = 200

    # Deduplication
    NOTIFICATION_DEDUP_WINDOW_SECONDS: int = 300  # 5 minutes
```

### Environment Variables (.env.example)

```bash
# ===================
# NOTIFICATIONS
# ===================

# Email (choose one provider)
NOTIFICATION_EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_FROM=alerts@yourapp.com

# Or use SendGrid
# EMAIL_PROVIDER=sendgrid
# SENDGRID_API_KEY=SG.xxxxxx

# SMS (Twilio)
NOTIFICATION_SMS_ENABLED=false
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890

# WhatsApp (Twilio)
NOTIFICATION_WHATSAPP_ENABLED=false
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# Rate Limits
NOTIFICATION_RATE_LIMIT_PER_HOUR=60
NOTIFICATION_RATE_LIMIT_PER_DAY=200
```

---

## 8. Celery Tasks Integration

Update `worker/worker/tasks/alerts.py` to use the notification service:

```python
"""Alert notification Celery tasks."""

import logging
from celery import shared_task

from app.modules.notifications.service import notification_service
from app.providers.notification.base import (
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="worker.tasks.alerts.send_alert_notification")
async def send_alert_notification(
    self,
    user_id: str,
    alert_id: str,
    symbol: str,
    current_price: float,
    target_price: float,
    alert_type: str,
) -> dict:
    """Send notification for a triggered price alert.

    Args:
        user_id: User who created the alert
        alert_id: Alert identifier
        symbol: Stock symbol
        current_price: Current stock price
        target_price: Alert trigger price
        alert_type: "above" or "below"
    """
    logger.info(f"Sending alert notification for {symbol} to user {user_id}")

    title = f"Price Alert: {symbol}"
    message = (
        f"{symbol} is now ₹{current_price:,.2f} "
        f"({'above' if alert_type == 'above' else 'below'} "
        f"your target of ₹{target_price:,.2f})"
    )

    result = await notification_service.notify(
        user_id=user_id,
        title=title,
        message=message,
        priority=NotificationPriority.HIGH,
        notification_type=NotificationType.PRICE_ALERT,
        data={
            "alert_id": alert_id,
            "symbol": symbol,
            "current_price": current_price,
            "target_price": target_price,
            "alert_type": alert_type,
        },
    )

    logger.info(f"Alert notification result: {result}")
    return result


@shared_task(bind=True, name="worker.tasks.alerts.send_order_notification")
async def send_order_notification(
    self,
    user_id: str,
    order_id: str,
    symbol: str,
    quantity: int,
    price: float,
    side: str,
    status: str,
) -> dict:
    """Send notification for order status change."""

    notification_types = {
        "placed": NotificationType.ORDER_PLACED,
        "filled": NotificationType.ORDER_FILLED,
        "cancelled": NotificationType.ORDER_CANCELLED,
        "rejected": NotificationType.ORDER_REJECTED,
    }

    titles = {
        "placed": f"Order Placed: {symbol}",
        "filled": f"Order Filled: {symbol}",
        "cancelled": f"Order Cancelled: {symbol}",
        "rejected": f"Order Rejected: {symbol}",
    }

    title = titles.get(status, f"Order Update: {symbol}")
    message = f"{side.upper()} {quantity} {symbol} @ ₹{price:,.2f} - {status.upper()}"

    return await notification_service.notify(
        user_id=user_id,
        title=title,
        message=message,
        priority=NotificationPriority.MEDIUM,
        notification_type=notification_types.get(status, NotificationType.SYSTEM_ALERT),
        data={
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "side": side,
            "status": status,
        },
    )


@shared_task(bind=True, name="worker.tasks.alerts.send_risk_alert")
async def send_risk_alert(
    self,
    user_id: str,
    alert_type: str,
    message: str,
    data: dict | None = None,
) -> dict:
    """Send critical risk management alert.

    Risk alerts always use CRITICAL priority and all available channels.
    """
    risk_types = {
        "kill_switch": NotificationType.KILL_SWITCH_TRIGGERED,
        "margin_warning": NotificationType.MARGIN_WARNING,
        "risk_limit_warning": NotificationType.RISK_LIMIT_WARNING,
        "risk_limit_breach": NotificationType.RISK_LIMIT_BREACH,
    }

    return await notification_service.notify(
        user_id=user_id,
        title=f"⚠️ Risk Alert: {alert_type.replace('_', ' ').title()}",
        message=message,
        priority=NotificationPriority.CRITICAL,
        notification_type=risk_types.get(alert_type, NotificationType.SYSTEM_ALERT),
        data=data,
        skip_dedup=True,  # Always send risk alerts
    )
```

---

## 9. Frontend Integration

### 9.1 Existing Frontend Store

The frontend notification store already exists at `frontend/src/store/notifications.ts`. It provides:

- `addNotification()` - Add a new notification to the store
- `markAsRead(id)` - Mark notification as read
- `markAllAsRead()` - Mark all as read
- `removeNotification(id)` - Remove a notification
- `clearAll()` - Clear all notifications
- Persistence via localStorage (last 20 notifications)

### 9.2 WebSocket Integration

Update the WebSocket handler to process notification messages:

```typescript
// frontend/src/lib/websocket.ts

interface NotificationPayload {
  type: 'notification';
  payload: {
    title: string;
    message: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    notification_type: string;
    data: Record<string, unknown>;
  };
}

// In your WebSocket message handler:
const handleWebSocketMessage = (event: MessageEvent) => {
  const data = JSON.parse(event.data);

  if (data.type === 'notification') {
    const { payload } = data as NotificationPayload;

    // Map priority to notification type
    const typeMap: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
      low: 'info',
      medium: 'info',
      high: 'warning',
      critical: 'error',
    };

    // Add to notification store
    useNotificationStore.getState().addNotification({
      type: typeMap[payload.priority] || 'info',
      title: payload.title,
      message: payload.message,
      data: payload.data,
    });

    // Show toast for high priority
    if (payload.priority === 'high' || payload.priority === 'critical') {
      showToast({
        type: typeMap[payload.priority],
        title: payload.title,
        message: payload.message,
      });
    }

    // Play sound if enabled
    if (payload.priority !== 'low') {
      playNotificationSound();
    }
  }
};
```

### 9.3 Notification Preferences API Hook

```typescript
// frontend/src/hooks/useNotificationPreferences.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface NotificationPreferences {
  email_enabled: boolean;
  email_address: string | null;
  sms_enabled: boolean;
  phone_number: string | null;
  whatsapp_enabled: boolean;
  websocket_enabled: boolean;
  sound_enabled: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  type_preferences: Record<string, string[]>;
}

export function useNotificationPreferences() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: () => api.get<NotificationPreferences>('/api/v1/notifications/preferences'),
  });

  const mutation = useMutation({
    mutationFn: (data: Partial<NotificationPreferences>) =>
      api.patch('/api/v1/notifications/preferences', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });

  return {
    preferences: query.data,
    isLoading: query.isLoading,
    updatePreferences: mutation.mutate,
    isUpdating: mutation.isPending,
  };
}
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# tests/unit/providers/notification/test_console_provider.py

import pytest
from app.providers.notification.console import ConsoleNotificationProvider
from app.providers.notification.base import NotificationPriority, NotificationType


class TestConsoleNotificationProvider:
    """Tests for console notification provider."""

    @pytest.fixture
    def provider(self):
        return ConsoleNotificationProvider()

    @pytest.mark.asyncio
    async def test_send_returns_true(self, provider):
        """Console provider should always succeed."""
        result = await provider.send(
            user_id="user123",
            title="Test",
            message="Test message",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_is_always_available(self, provider):
        """Console provider should be available for all users."""
        assert await provider.is_available("any_user") is True

    @pytest.mark.asyncio
    async def test_send_bulk(self, provider):
        """Bulk send should succeed for all users."""
        result = await provider.send_bulk(
            user_ids=["user1", "user2", "user3"],
            title="Bulk Test",
            message="Test message",
        )
        assert all(result.values())
```

### 10.2 Integration Tests

```python
# tests/integration/test_notification_service.py

import pytest
from app.modules.notifications.service import NotificationService
from app.providers.notification.base import NotificationPriority, NotificationType
from app.providers.notification.factory import NotificationProviderFactory
from app.providers.notification.console import ConsoleNotificationProvider


class TestNotificationService:
    """Integration tests for notification service."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Register console provider for testing."""
        NotificationProviderFactory.register("console", ConsoleNotificationProvider)
        yield
        # Cleanup
        NotificationProviderFactory._providers.clear()
        NotificationProviderFactory._instances.clear()

    @pytest.fixture
    def service(self):
        return NotificationService()

    @pytest.mark.asyncio
    async def test_notify_sends_to_channels(self, service):
        """Should send to available channels."""
        result = await service.notify(
            user_id="user123",
            title="Test Notification",
            message="This is a test",
            force_channels=["console"],
        )

        assert result["status"] == "sent"
        assert result["channels"]["console"] == "sent"

    @pytest.mark.asyncio
    async def test_deduplication(self, service):
        """Should deduplicate identical notifications."""
        # First send
        result1 = await service.notify(
            user_id="user123",
            title="Duplicate Test",
            message="Same message",
            force_channels=["console"],
        )

        # Immediate duplicate
        result2 = await service.notify(
            user_id="user123",
            title="Duplicate Test",
            message="Same message",
            force_channels=["console"],
        )

        assert result1["status"] == "sent"
        assert result2["status"] == "deduplicated"

    @pytest.mark.asyncio
    async def test_skip_dedup_flag(self, service):
        """Should skip deduplication when flag is set."""
        # First send
        await service.notify(
            user_id="user123",
            title="Skip Dedup",
            message="Test",
            force_channels=["console"],
        )

        # With skip_dedup=True
        result = await service.notify(
            user_id="user123",
            title="Skip Dedup",
            message="Test",
            force_channels=["console"],
            skip_dedup=True,
        )

        assert result["status"] == "sent"
```

---

## 11. Implementation Checklist

### Week 4: Core Infrastructure

- [ ] Create `ConsoleNotificationProvider` (stub for development)
- [ ] Register console provider in factory
- [ ] Create `NotificationService` orchestrator
- [ ] Create `NotificationPreferences` model
- [ ] Create database migration for preferences table
- [ ] Add notification settings to config.py
- [ ] Write unit tests for console provider
- [ ] Write integration tests for service

### Week 5: Provider Implementations

- [ ] Implement `EmailNotificationProvider` (SMTP)
- [ ] Test email with Gmail SMTP
- [ ] Implement `SMSNotificationProvider` (Twilio)
- [ ] Test SMS sending
- [ ] Implement `WebSocketNotificationProvider`
- [ ] Integrate with existing WebSocket manager
- [ ] Update Celery alert tasks to use notification service
- [ ] Frontend: Update WebSocket handler for notifications
- [ ] Frontend: Create notification preferences page
- [ ] End-to-end testing of full notification flow

### Future (Phase 2)

- [ ] WhatsApp provider (Twilio)
- [ ] Push notifications (FCM)
- [ ] Notification history model
- [ ] Analytics dashboard for notifications
- [ ] Template system for messages
- [ ] Webhook provider for external integrations

---

## 12. API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/notifications/preferences` | Get user preferences |
| PATCH | `/api/v1/notifications/preferences` | Update preferences |
| POST | `/api/v1/notifications/verify-email` | Send email verification |
| POST | `/api/v1/notifications/verify-phone` | Send phone verification (SMS) |
| POST | `/api/v1/notifications/test` | Send test notification |
| GET | `/api/v1/notifications/history` | Get notification history |

---

## References

- **Twilio SMS Pattern:** Extracted from [stock-tracker-agent](https://github.com/IAmTomShaw/stock-tracker-agent)
- **Twilio Python SDK:** https://www.twilio.com/docs/libraries/python
- **SendGrid Python SDK:** https://github.com/sendgrid/sendgrid-python
- **FCM (Firebase Cloud Messaging):** https://firebase.google.com/docs/cloud-messaging

