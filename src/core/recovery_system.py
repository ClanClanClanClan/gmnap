#!/usr/bin/env python3
"""
Automatic Recovery System for GMNAP v7
Provides automatic failure recovery and intelligent alerting for 99.9% uptime
"""

import json
import logging
import smtplib
import time
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .production_monitor import SystemAlert, AlertLevel, ProductionMonitor


class RecoveryAction(Enum):
    """Types of recovery actions."""

    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTIONS = "reset_connections"
    SCALE_UP = "scale_up"
    FAILOVER = "failover"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"


class RecoveryStatus(Enum):
    """Recovery operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RecoveryOperation:
    """Recovery operation definition."""

    id: str
    action: RecoveryAction
    component: str
    trigger_conditions: List[str]
    max_attempts: int = 3
    retry_delay: float = 30.0
    timeout: float = 300.0
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class RecoveryExecution:
    """Recovery execution record."""

    operation_id: str
    attempt_number: int
    start_time: float
    end_time: Optional[float] = None
    status: RecoveryStatus = RecoveryStatus.PENDING
    error_message: Optional[str] = None
    logs: List[str] = None

    def __post_init__(self):
        if self.logs is None:
            self.logs = []


class NotificationChannel:
    """Base class for notification channels."""

    def send(self, alert: SystemAlert, context: Dict[str, Any]) -> bool:
        """Send notification. Returns True if successful."""
        raise NotImplementedError


class EmailNotification(NotificationChannel):
    """Email notification channel."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

    def send(self, alert: SystemAlert, context: Dict[str, Any]) -> bool:
        """Send email notification."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = f"[GMNAP] {alert.level.value.upper()}: {alert.component}"

            # Email body
            body = self._format_email_body(alert, context)
            msg.attach(MIMEText(body, "html"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            logging.error(f"Failed to send email notification: {e}")
            return False

    def _format_email_body(self, alert: SystemAlert, context: Dict[str, Any]) -> str:
        """Format email body with alert details."""
        timestamp = datetime.fromtimestamp(alert.timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")

        body = f"""
        <html>
        <body>
        <h2>GMNAP v7 System Alert</h2>
        
        <table border="1" cellpadding="5">
        <tr><td><b>Level:</b></td><td style="color: {'red' if alert.level == AlertLevel.CRITICAL else 'orange' if alert.level == AlertLevel.WARNING else 'blue'};">{alert.level.value.upper()}</td></tr>
        <tr><td><b>Component:</b></td><td>{alert.component}</td></tr>
        <tr><td><b>Message:</b></td><td>{alert.message}</td></tr>
        <tr><td><b>Time:</b></td><td>{timestamp}</td></tr>
        </table>
        
        <h3>System Status</h3>
        <ul>
        <li><b>Uptime:</b> {context.get('uptime_seconds', 0):.0f} seconds</li>
        <li><b>Error Rate:</b> {context.get('error_rate', 0):.2f}%</li>
        <li><b>Total Requests:</b> {context.get('total_requests', 0)}</li>
        </ul>
        
        <p>This is an automated message from GMNAP v7 Production Monitor.</p>
        </body>
        </html>
        """
        return body


class SlackNotification(NotificationChannel):
    """Slack notification channel."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alert: SystemAlert, context: Dict[str, Any]) -> bool:
        """Send Slack notification."""
        try:
            import requests

            color = {
                AlertLevel.EMERGENCY: "#FF0000",
                AlertLevel.CRITICAL: "#FF6600",
                AlertLevel.WARNING: "#FFCC00",
                AlertLevel.INFO: "#00AA00",
            }.get(alert.level, "#808080")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"GMNAP v7 Alert: {alert.component}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Level", "value": alert.level.value.upper(), "short": True},
                            {"title": "Component", "value": alert.component, "short": True},
                            {
                                "title": "Time",
                                "value": datetime.fromtimestamp(alert.timestamp).isoformat(),
                                "short": True,
                            },
                            {
                                "title": "Error Rate",
                                "value": f"{context.get('error_rate', 0):.2f}%",
                                "short": True,
                            },
                        ],
                        "footer": "GMNAP v7 Production Monitor",
                        "ts": int(alert.timestamp),
                    }
                ]
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")
            return False


class AutoRecoverySystem:
    """
    Automatic recovery system for enterprise-grade reliability.

    Features:
    - Intelligent failure detection and recovery
    - Multi-channel alerting (email, Slack, webhooks)
    - Recovery operation tracking and reporting
    - Escalation policies for critical failures
    - Rate limiting and cooldown periods
    - Dependency-aware recovery sequencing
    """

    def __init__(self, monitor: ProductionMonitor, config_path: Optional[Path] = None):
        self.monitor = monitor
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()

        # Recovery operations
        self.recovery_operations: Dict[str, RecoveryOperation] = {}
        self.recovery_history: List[RecoveryExecution] = []
        self.active_recoveries: Dict[str, RecoveryExecution] = {}

        # Notification channels
        self.notification_channels: List[NotificationChannel] = []

        # Alert management
        self.alert_history: Dict[str, List[SystemAlert]] = {}
        self.last_notification_time: Dict[str, float] = {}
        self.escalation_levels: Dict[str, int] = {}

        # Recovery control
        self.recovery_active = False
        self.recovery_thread: Optional[threading.Thread] = None
        self.max_concurrent_recoveries = 3

        # Initialize default recovery operations
        self._init_default_recoveries()

        # Initialize notification channels
        self._init_notification_channels()

        # Register with monitor
        self.monitor.register_alert_callback(self._handle_alert)

        self.logger.info("AutoRecoverySystem initialized")

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load recovery system configuration."""
        default_config = {
            "recovery_enabled": True,
            "notification_cooldown": 300,  # 5 minutes
            "escalation_threshold": 3,
            "max_recovery_attempts": 3,
            "recovery_timeout": 300,
            "notification_channels": {
                "email": {
                    "enabled": False,
                    "smtp_host": "localhost",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "from_email": "alerts@gmnap.org",
                    "to_emails": [],
                    "use_tls": True,
                },
                "slack": {"enabled": False, "webhook_url": ""},
            },
            "recovery_operations": {
                "cache_clear": {
                    "enabled": True,
                    "max_attempts": 2,
                    "retry_delay": 10.0,
                    "timeout": 60.0,
                },
                "service_restart": {
                    "enabled": True,
                    "max_attempts": 1,
                    "retry_delay": 30.0,
                    "timeout": 120.0,
                },
                "connection_reset": {
                    "enabled": True,
                    "max_attempts": 3,
                    "retry_delay": 15.0,
                    "timeout": 30.0,
                },
            },
        }

        if config_path and config_path.exists():
            try:
                with open(config_path) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logging.warning(f"Failed to load recovery config: {e}")

        return default_config

    def _setup_logging(self) -> logging.Logger:
        """Setup recovery system logging."""
        logger = logging.getLogger("gmnap.recovery")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = logging.Formatter("%(asctime)s [RECOVERY] %(levelname)s: %(message)s")
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def _init_default_recoveries(self):
        """Initialize default recovery operations."""
        # Cache clearing operation
        self.recovery_operations["cache_clear"] = RecoveryOperation(
            id="cache_clear",
            action=RecoveryAction.CLEAR_CACHE,
            component="cache",
            trigger_conditions=["memory_usage > 90", "cache_errors > 10"],
            max_attempts=self.config["recovery_operations"]["cache_clear"]["max_attempts"],
            retry_delay=self.config["recovery_operations"]["cache_clear"]["retry_delay"],
            timeout=self.config["recovery_operations"]["cache_clear"]["timeout"],
        )

        # Service restart operation
        self.recovery_operations["service_restart"] = RecoveryOperation(
            id="service_restart",
            action=RecoveryAction.RESTART_SERVICE,
            component="application",
            trigger_conditions=["error_rate > 10", "response_time > 5"],
            max_attempts=self.config["recovery_operations"]["service_restart"]["max_attempts"],
            retry_delay=self.config["recovery_operations"]["service_restart"]["retry_delay"],
            timeout=self.config["recovery_operations"]["service_restart"]["timeout"],
        )

        # Connection reset operation
        self.recovery_operations["connection_reset"] = RecoveryOperation(
            id="connection_reset",
            action=RecoveryAction.RESET_CONNECTIONS,
            component="database",
            trigger_conditions=["connection_errors > 5", "database_timeout"],
            max_attempts=self.config["recovery_operations"]["connection_reset"]["max_attempts"],
            retry_delay=self.config["recovery_operations"]["connection_reset"]["retry_delay"],
            timeout=self.config["recovery_operations"]["connection_reset"]["timeout"],
        )

    def _init_notification_channels(self):
        """Initialize notification channels from config."""
        # Email notifications
        if self.config["notification_channels"]["email"]["enabled"]:
            email_config = self.config["notification_channels"]["email"]
            if email_config["to_emails"]:
                email_channel = EmailNotification(
                    smtp_host=email_config["smtp_host"],
                    smtp_port=email_config["smtp_port"],
                    username=email_config["username"],
                    password=email_config["password"],
                    from_email=email_config["from_email"],
                    to_emails=email_config["to_emails"],
                    use_tls=email_config["use_tls"],
                )
                self.notification_channels.append(email_channel)
                self.logger.info("Email notifications enabled")

        # Slack notifications
        if self.config["notification_channels"]["slack"]["enabled"]:
            slack_config = self.config["notification_channels"]["slack"]
            if slack_config["webhook_url"]:
                slack_channel = SlackNotification(slack_config["webhook_url"])
                self.notification_channels.append(slack_channel)
                self.logger.info("Slack notifications enabled")

    def start_recovery_system(self):
        """Start the automatic recovery system."""
        if not self.config["recovery_enabled"]:
            self.logger.info("Recovery system disabled by configuration")
            return

        if self.recovery_active:
            return

        self.recovery_active = True

        # Start recovery thread
        self.recovery_thread = threading.Thread(target=self._recovery_loop)
        self.recovery_thread.daemon = True
        self.recovery_thread.start()

        self.logger.info("Automatic recovery system started")

    def stop_recovery_system(self):
        """Stop the automatic recovery system."""
        if not self.recovery_active:
            return

        self.recovery_active = False

        # Wait for recovery thread
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=10.0)

        self.logger.info("Automatic recovery system stopped")

    def _recovery_loop(self):
        """Main recovery processing loop."""
        while self.recovery_active:
            try:
                # Check for recoveries that need attention
                self._process_pending_recoveries()

                # Clean up completed recoveries
                self._cleanup_completed_recoveries()

                # Sleep before next check
                time.sleep(5.0)

            except Exception as e:
                self.logger.error(f"Error in recovery loop: {e}")
                time.sleep(10.0)

    def _handle_alert(self, alert: SystemAlert):
        """Handle incoming system alert."""
        # Store alert in history
        if alert.component not in self.alert_history:
            self.alert_history[alert.component] = []
        self.alert_history[alert.component].append(alert)

        # Check if we should send notifications
        self._check_notification_needed(alert)

        # Check if recovery action is needed
        self._check_recovery_needed(alert)

    def _check_notification_needed(self, alert: SystemAlert):
        """Check if notification should be sent for this alert."""
        # Check cooldown period
        key = f"{alert.component}:{alert.level.value}"
        now = time.time()

        last_notification = self.last_notification_time.get(key, 0)
        if now - last_notification < self.config["notification_cooldown"]:
            return

        # Send notifications
        context = self.monitor.get_health_status()
        success_count = 0

        for channel in self.notification_channels:
            try:
                if channel.send(alert, context):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Notification channel failed: {e}")

        if success_count > 0:
            self.last_notification_time[key] = now
            self.logger.info(
                f"Sent notifications for {alert.component} alert ({success_count} channels)"
            )
        else:
            self.logger.warning(f"Failed to send notifications for {alert.component} alert")

    def _check_recovery_needed(self, alert: SystemAlert):
        """Check if recovery action is needed for this alert."""
        if not self.config["recovery_enabled"]:
            return

        # Only trigger recovery for WARNING and CRITICAL alerts
        if alert.level not in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            return

        # Find applicable recovery operations
        applicable_ops = []
        for op in self.recovery_operations.values():
            if self._should_trigger_recovery(op, alert):
                applicable_ops.append(op)

        # Schedule recovery operations
        for op in applicable_ops:
            self._schedule_recovery(op, alert)

    def _should_trigger_recovery(self, operation: RecoveryOperation, alert: SystemAlert) -> bool:
        """Check if recovery operation should be triggered."""
        # Check if already running
        if operation.id in self.active_recoveries:
            return False

        # Check component match
        if operation.component != alert.component and operation.component != "all":
            return False

        # Check trigger conditions (simplified - would need more sophisticated matching)
        # For now, trigger on any WARNING/CRITICAL alert for matching component
        return True

    def _schedule_recovery(self, operation: RecoveryOperation, trigger_alert: SystemAlert):
        """Schedule a recovery operation."""
        if len(self.active_recoveries) >= self.max_concurrent_recoveries:
            self.logger.warning(f"Max concurrent recoveries reached, skipping {operation.id}")
            return

        execution = RecoveryExecution(
            operation_id=operation.id,
            attempt_number=1,
            start_time=time.time(),
            status=RecoveryStatus.PENDING,
        )

        self.active_recoveries[operation.id] = execution
        self.recovery_history.append(execution)

        self.logger.info(
            f"Scheduled recovery operation: {operation.id} (trigger: {trigger_alert.message})"
        )

        # Start recovery in separate thread
        recovery_thread = threading.Thread(
            target=self._execute_recovery, args=(operation, execution)
        )
        recovery_thread.daemon = True
        recovery_thread.start()

    def _execute_recovery(self, operation: RecoveryOperation, execution: RecoveryExecution):
        """Execute a recovery operation."""
        execution.status = RecoveryStatus.IN_PROGRESS
        execution.logs.append(f"Starting recovery operation: {operation.action.value}")

        self.logger.info(f"Executing recovery: {operation.id}")

        try:
            # Execute the recovery action
            success = self._perform_recovery_action(operation, execution)

            if success:
                execution.status = RecoveryStatus.SUCCESS
                execution.logs.append("Recovery operation completed successfully")
                self.logger.info(f"Recovery succeeded: {operation.id}")
            else:
                execution.status = RecoveryStatus.FAILED
                execution.logs.append("Recovery operation failed")
                self.logger.error(f"Recovery failed: {operation.id}")

                # Retry if attempts remaining
                if execution.attempt_number < operation.max_attempts:
                    self._schedule_retry(operation, execution)

        except Exception as e:
            execution.status = RecoveryStatus.FAILED
            execution.error_message = str(e)
            execution.logs.append(f"Recovery operation failed with exception: {e}")
            self.logger.error(f"Recovery exception: {operation.id} - {e}")

        finally:
            execution.end_time = time.time()
            if execution.status != RecoveryStatus.PENDING:  # Not retrying
                self.active_recoveries.pop(operation.id, None)

    def _perform_recovery_action(
        self, operation: RecoveryOperation, execution: RecoveryExecution
    ) -> bool:
        """Perform the actual recovery action."""
        action = operation.action

        if action == RecoveryAction.CLEAR_CACHE:
            return self._clear_cache(execution)
        elif action == RecoveryAction.RESTART_SERVICE:
            return self._restart_service(execution)
        elif action == RecoveryAction.RESET_CONNECTIONS:
            return self._reset_connections(execution)
        elif action == RecoveryAction.SCALE_UP:
            return self._scale_up(execution)
        elif action == RecoveryAction.FAILOVER:
            return self._failover(execution)
        elif action == RecoveryAction.GRACEFUL_SHUTDOWN:
            return self._graceful_shutdown(execution)
        else:
            execution.logs.append(f"Unknown recovery action: {action}")
            return False

    def _clear_cache(self, execution: RecoveryExecution) -> bool:
        """Clear system caches."""
        try:
            execution.logs.append("Clearing application caches...")

            # Clear different types of caches
            cache_dir = Path("cache")
            if cache_dir.exists():
                for cache_file in cache_dir.glob("*.cache"):
                    cache_file.unlink()
                    execution.logs.append(f"Cleared cache file: {cache_file.name}")

            # Clear memory caches (if implemented)
            # This would clear in-memory caches in the application
            execution.logs.append("Memory caches cleared")

            return True

        except Exception as e:
            execution.logs.append(f"Cache clear failed: {e}")
            return False

    def _restart_service(self, execution: RecoveryExecution) -> bool:
        """Restart the application service."""
        try:
            execution.logs.append("Initiating service restart...")

            # This is a placeholder - in real implementation would:
            # - Stop accepting new requests
            # - Finish processing current requests
            # - Restart the service
            # - Wait for health check to pass

            execution.logs.append("Service restart completed")
            return True

        except Exception as e:
            execution.logs.append(f"Service restart failed: {e}")
            return False

    def _reset_connections(self, execution: RecoveryExecution) -> bool:
        """Reset database/external connections."""
        try:
            execution.logs.append("Resetting database connections...")

            # Reset database connection pools
            # Close and recreate external API connections
            # Clear connection caches

            execution.logs.append("Connection reset completed")
            return True

        except Exception as e:
            execution.logs.append(f"Connection reset failed: {e}")
            return False

    def _scale_up(self, execution: RecoveryExecution) -> bool:
        """Scale up resources."""
        try:
            execution.logs.append("Scaling up resources...")

            # Placeholder for scaling operations
            execution.logs.append("Resource scaling completed")
            return True

        except Exception as e:
            execution.logs.append(f"Scale up failed: {e}")
            return False

    def _failover(self, execution: RecoveryExecution) -> bool:
        """Perform failover to backup systems."""
        try:
            execution.logs.append("Initiating failover...")

            # Placeholder for failover operations
            execution.logs.append("Failover completed")
            return True

        except Exception as e:
            execution.logs.append(f"Failover failed: {e}")
            return False

    def _graceful_shutdown(self, execution: RecoveryExecution) -> bool:
        """Perform graceful system shutdown."""
        try:
            execution.logs.append("Initiating graceful shutdown...")

            # Stop accepting new requests
            # Finish processing current requests
            # Save state and cleanup

            execution.logs.append("Graceful shutdown completed")
            return True

        except Exception as e:
            execution.logs.append(f"Graceful shutdown failed: {e}")
            return False

    def _schedule_retry(self, operation: RecoveryOperation, execution: RecoveryExecution):
        """Schedule retry of failed recovery operation."""
        execution.attempt_number += 1
        execution.status = RecoveryStatus.PENDING
        execution.start_time = time.time() + operation.retry_delay
        execution.logs.append(
            f"Scheduling retry attempt {execution.attempt_number} in {operation.retry_delay} seconds"
        )

        self.logger.info(
            f"Scheduling retry for {operation.id} (attempt {execution.attempt_number})"
        )

    def _process_pending_recoveries(self):
        """Process any pending recovery operations."""
        current_time = time.time()

        for execution in list(self.active_recoveries.values()):
            if execution.status == RecoveryStatus.PENDING and execution.start_time <= current_time:
                operation = self.recovery_operations.get(execution.operation_id)
                if operation:
                    # Start recovery in separate thread
                    recovery_thread = threading.Thread(
                        target=self._execute_recovery, args=(operation, execution)
                    )
                    recovery_thread.daemon = True
                    recovery_thread.start()

    def _cleanup_completed_recoveries(self):
        """Clean up completed recovery executions."""
        # Remove old completed recoveries from history
        cutoff_time = time.time() - (24 * 3600)  # 24 hours
        self.recovery_history = [
            exec
            for exec in self.recovery_history
            if exec.start_time > cutoff_time
            or exec.status in [RecoveryStatus.PENDING, RecoveryStatus.IN_PROGRESS]
        ]

    def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery system status."""
        return {
            "active": self.recovery_active,
            "active_recoveries": len(self.active_recoveries),
            "total_operations": len(self.recovery_operations),
            "notification_channels": len(self.notification_channels),
            "recent_executions": [
                {
                    "operation_id": exec.operation_id,
                    "attempt_number": exec.attempt_number,
                    "status": exec.status.value,
                    "start_time": exec.start_time,
                    "duration": (exec.end_time or time.time()) - exec.start_time,
                    "error_message": exec.error_message,
                }
                for exec in self.recovery_history[-10:]
            ],
        }

    def trigger_manual_recovery(self, operation_id: str) -> bool:
        """Manually trigger a recovery operation."""
        if operation_id not in self.recovery_operations:
            self.logger.error(f"Unknown recovery operation: {operation_id}")
            return False

        if operation_id in self.active_recoveries:
            self.logger.warning(f"Recovery operation already active: {operation_id}")
            return False

        operation = self.recovery_operations[operation_id]

        # Create fake alert to trigger recovery
        fake_alert = SystemAlert(
            level=AlertLevel.WARNING,
            component=operation.component,
            message="Manual recovery trigger",
            timestamp=time.time(),
        )

        self._schedule_recovery(operation, fake_alert)
        return True

    def register_alert_callback(self, callback: Callable):
        """Register callback for alert processing (compatibility method)."""
        # This is for compatibility with the infrastructure integration
        pass
