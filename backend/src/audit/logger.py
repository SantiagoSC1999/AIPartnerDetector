"""Audit logging service."""

from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid


class AuditLogger:
    """Service for logging all duplicate detection decisions."""

    def __init__(self):
        """Initialize audit logger."""
        self.logs = []

    async def log_upload(self, file_id: str, filename: str, total_records: int) -> None:
        """Log file upload event."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "upload",
            "file_id": file_id,
            "filename": filename,
            "total_records": total_records,
        }
        self.logs.append(log_entry)

    async def log_duplicate_detection(
        self,
        file_id: str,
        row_id: str,
        uploaded_institution: Dict[str, Any],
        matched_clarisa_id: int,
        similarity_score: float,
        status: str,
        reason: str,
    ) -> None:
        """Log duplicate detection decision."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "duplicate_detection",
            "file_id": file_id,
            "row_id": row_id,
            "uploaded_institution": uploaded_institution,
            "matched_clarisa_id": matched_clarisa_id,
            "similarity_score": similarity_score,
            "status": status,
            "reason": reason,
        }
        self.logs.append(log_entry)

    async def log_error(self, file_id: str, row_id: str, error: str) -> None:
        """Log processing error."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "file_id": file_id,
            "row_id": row_id,
            "error": error,
        }
        self.logs.append(log_entry)

    async def log_audit_action(
        self, action: str, entity_type: str, entity_id: str = None, details: Dict[str, Any] = None
    ) -> None:
        """Log a generic audit action."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "audit_action",
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
        }
        self.logs.append(log_entry)

    async def export_logs(self) -> str:
        """Export all logs as JSON string."""
        return json.dumps(self.logs, indent=2)

    async def get_logs(self) -> list:
        """Get all logs."""
        return self.logs.copy()


# Global instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
