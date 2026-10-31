from enum import StrEnum


class Reason(StrEnum):
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


class SafeError(Exception):
    """Only allowlisted codes and known setting names may cross the CLI boundary."""

    def __init__(self, reason: Reason, *, source=None, setting=None):
        super().__init__(reason.value)
        self.reason = reason
        self.source = source
        self.setting = setting
