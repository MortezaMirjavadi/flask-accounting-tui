"""Wallet activity logging utilities."""

import json


def log_wallet_activity(cursor, wallet_id, user_id, action, entity_type=None, entity_id=None, details=None):
    """Insert a record into wallet_activity_log for audit trail.

    Args:
        cursor: Database cursor
        wallet_id: ID of the wallet
        user_id: ID of the user performing the action
        action: Action string (e.g. 'transaction_created', 'member_added')
        entity_type: Optional entity type (e.g. 'transaction', 'transfer', 'account')
        entity_id: Optional entity ID
        details: Optional dict with additional context
    """
    details_json = json.dumps(details) if details else None

    cursor.execute(
        """
        INSERT INTO wallet_activity_log (wallet_id, user_id, action, entity_type, entity_id, details)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """,
        (wallet_id, user_id, action, entity_type, entity_id, details_json)
    )


# Common action constants
ACTION_TRANSACTION_CREATED = 'transaction_created'
ACTION_TRANSACTION_EDITED = 'transaction_edited'
ACTION_TRANSACTION_DELETED = 'transaction_deleted'
ACTION_TRANSFER_CREATED = 'transfer_created'
ACTION_MEMBER_ADDED = 'member_added'
ACTION_MEMBER_REMOVED = 'member_removed'
ACTION_MEMBER_ROLE_CHANGED = 'member_role_changed'
ACTION_SETTINGS_CHANGED = 'settings_changed'
ACTION_INVITATION_SENT = 'invitation_sent'
ACTION_INVITATION_ACCEPTED = 'invitation_accepted'
ACTION_INVITATION_REJECTED = 'invitation_rejected'

# Account action constants
ACTION_ACCOUNT_CREATED = 'account_created'
ACTION_ACCOUNT_UPDATED = 'account_updated'
ACTION_ACCOUNT_DELETED = 'account_deleted'
ACTION_ACCOUNT_TRANSFER = 'account_transfer'
