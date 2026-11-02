from enum import StrEnum


class Reason(StrEnum):
    EXECUTION_FAILED = "execution_failed"
    OK = "ok"
    INVALID_INPUT = "invalid_input"
    CONFIG_INVALID = "configuration_invalid"
    CONFIG_FILE = "configuration_file_error"
    UNKNOWN_SETTING = "unknown_setting"
    STORE_MISSING = "store_missing"
    STORE_INVALID = "store_unrecognized"
    STORE_REVISION = "store_revision_unsupported"
    UPGRADE_REQUIRED = "upgrade_required"
    MIGRATION_CHAIN = "migration_chain_invalid"
    STORAGE_FAILURE = "storage_failed"
    MIGRATION_FAILED = "migration_failed"
    REFUSED = "permission_refused"
    UNAVAILABLE = "capability_unavailable"
    ROLLED_BACK = "transaction_rolled_back"
    UNCERTAIN = "effects_uncertain"
    INTERNAL = "internal_failure"
    CLEANUP_FAILED = "cleanup_failed"
    CONFLICT = "version_conflict"
    INCOMPLETE = "incomplete_definition"
    NOT_FOUND = "reference_missing"
    REVIEW = "review_inapplicable"
    AUTHENTICATION = "authentication_required"
    PROTECTION = "private_state_unprotected"
    DELIVERY = "credential_delivery_failed"
    LAST_ADMIN = "last_administrator_required"
    AUDIT = "audit_unavailable"
    TLS = "tls_configuration_invalid"
    DRAIN = "drain_deadline_exceeded"


class SafeError(Exception):
    """Only allowlisted codes and known setting names may cross the CLI boundary."""

    def __init__(self, reason: Reason, *, source=None, setting=None):
        super().__init__(reason.value)
        self.reason = reason
        self.source = source
        self.setting = setting
