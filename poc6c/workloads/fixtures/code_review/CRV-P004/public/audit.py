"""Audit formatting utilities."""

def audit_record(user, action, credential):
    return {"user": user, "action": action, "credential": credential}


def redact_message(message, secret):
    return message.replace(secret, "***")
