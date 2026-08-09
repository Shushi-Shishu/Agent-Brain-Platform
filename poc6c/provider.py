"""
Anthropic provider adapter for POC 6c.

Implements the ProviderAdapter protocol from controller.py using the Anthropic
Messages API directly.  Auditable telemetry is recorded for every response.

Security rules
--------------
- ANTHROPIC_API_KEY is read once at construction; never logged, hashed,
  committed, or written to any manifest.
- provider_cost_usd is computed only from observed billable tokens and the
  locked pricing record.  Missing token fields are never estimated.
- Batch API, prompt caching, fast/priority tiers, and geographic pricing
  modifiers are disabled for the first confirmation run so cost accounting
  is unambiguous.

Model identity
--------------
- Agent and evaluator model IDs are read from configuration.
- GET /v1/models is called at preflight; the adapter fails closed if either
  configured ID is absent from the response.
- Every response.model field is checked against the locked ID; a mismatch
  raises ResponseModelMismatch.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import anthropic


# ---------------------------------------------------------------------------
# Pricing lock
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
PRICING_LOCK_PATH = HERE / "pricing_lock.json"


def load_pricing_lock() -> dict[str, Any]:
    """Load and return the versioned pricing lock record."""
    return json.loads(PRICING_LOCK_PATH.read_text(encoding="utf-8"))


def validate_pricing_lock(lock: dict[str, Any] | None = None) -> None:
    """
    Validate the pricing lock for production use.

    Raises PricingLockExpiredError if:
    - source_sha256 is NOT_FETCHED_OFFLINE (not replaced with an auditable digest).
    - verification_required is True (pricing must be re-verified before use).
    - applicable_rate_expires date has passed (introductory rate expired).
    - Any required key is missing.
    """
    import datetime
    if lock is None:
        lock = load_pricing_lock()

    if lock.get("source_sha256", "") in ("NOT_FETCHED_OFFLINE", "", None):
        raise PricingLockExpiredError(
            "pricing_lock.json source_sha256 is 'NOT_FETCHED_OFFLINE'. "
            "Fetch the Anthropic pricing page, compute its SHA-256, and replace "
            "this sentinel before any confirmation run."
        )
    if lock.get("verification_required", False):
        raise PricingLockExpiredError(
            "pricing_lock.json has verification_required=true. "
            "Re-verify the pricing source and clear this flag before confirmation."
        )
    expires = lock.get("applicable_rate_expires", "")
    if expires:
        try:
            expiry_date = datetime.date.fromisoformat(expires)
            today = datetime.date.today()
            if today > expiry_date:
                raise PricingLockExpiredError(
                    f"pricing_lock.json applicable_rate expired on {expires} "
                    f"(today is {today}). Re-lock the applicable rate before confirmation."
                )
        except ValueError:
            raise PricingLockExpiredError(
                f"pricing_lock.json applicable_rate_expires '{expires}' "
                "is not a valid ISO date."
            )


def pricing_record_for_model(model_id: str) -> dict[str, Any]:
    """Return the pricing entry for the given model ID.  Raises KeyError if absent."""
    lock = load_pricing_lock()
    for entry in lock["models"]:
        if entry["model_id"] == model_id:
            return entry
    raise KeyError(f"model_id '{model_id}' not found in pricing_lock.json")


def pricing_lock_sha256() -> str:
    """Stable hex digest of the pricing lock file contents."""
    return hashlib.sha256(
        PRICING_LOCK_PATH.read_bytes()
    ).hexdigest().upper()


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

def compute_provider_cost_usd(
    pricing: dict[str, Any],
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """
    Compute provider_cost_usd from observed token counts and the locked pricing
    record.  Returns None if either token count is missing — never estimates.

    Only standard input/output rates are applied (Batch API, caching, and
    geographic modifiers are disabled for the first confirmation run).
    """
    if input_tokens is None or output_tokens is None:
        return None
    rate_in  = pricing["input_usd_per_million_tokens"]
    rate_out = pricing["output_usd_per_million_tokens"]
    return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000


# ---------------------------------------------------------------------------
# Telemetry record
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ResponseTelemetry:
    """Auditable telemetry captured from a single API response."""

    model_id_requested: str
    model_id_returned: str
    message_id: str | None
    request_id: str | None           # HTTP request-id header — required for confirmation
    input_tokens: int | None
    output_tokens: int | None
    cache_creation_input_tokens: int | None
    cache_read_input_tokens: int | None
    stop_reason: str | None
    http_request_id: str | None      # alias for request_id (same value)
    latency_ms: float
    pricing_lock_sha256: str
    provider_cost_usd: float | None
    retry_count: int                  # number of retries attempted (0 = no retry)
    retry_exhausted: bool             # True if all retries were consumed

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ProviderAdapterError(RuntimeError):
    """Base class for provider adapter errors."""


class MissingApiKey(ProviderAdapterError):
    """ANTHROPIC_API_KEY is absent or empty."""


class ModelNotAvailable(ProviderAdapterError):
    """A configured model ID was not returned by GET /v1/models."""


class ResponseModelMismatch(ProviderAdapterError):
    """response.model differs from the locked model ID."""


class MissingUsage(ProviderAdapterError):
    """Required token-usage or identity fields are absent from the response."""


class CacheUsageViolation(ProviderAdapterError):
    """Cache tokens were present when caching is disabled in the pricing lock."""


class PricingLockExpiredError(ProviderAdapterError):
    """The pricing lock applicable rate has expired or digest validation fails."""


class RetryTelemetryError(ProviderAdapterError):
    """Retry telemetry fields are missing or malformed."""


# ---------------------------------------------------------------------------
# Provider adapter
# ---------------------------------------------------------------------------

class AnthropicProviderAdapter:
    """
    Anthropic Messages API adapter for POC 6c.

    Parameters
    ----------
    agent_model_id : str
        Model ID for the configured-agent arm (Sonnet-tier).
    evaluator_model_id : str
        Model ID for the blinded evaluator (Opus-tier).
    max_tokens : int
        Hard output token cap per call.
    use_synthetic_fixtures : bool
        When True, bypass the live API and return deterministic synthetic
        responses.  Required for unit tests; must not be used during a
        confirmation run.
    """

    def __init__(
        self,
        agent_model_id: str,
        evaluator_model_id: str,
        max_tokens: int = 4096,
        use_synthetic_fixtures: bool = False,
    ) -> None:
        self.agent_model_id     = agent_model_id
        self.evaluator_model_id = evaluator_model_id
        self.max_tokens         = max_tokens
        self.use_synthetic_fixtures = use_synthetic_fixtures
        self._pricing_lock      = load_pricing_lock()
        self._pricing_lock_sha  = pricing_lock_sha256()

        if not use_synthetic_fixtures:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                raise MissingApiKey(
                    "ANTHROPIC_API_KEY is not set or is empty. "
                    "The adapter requires a valid API key to call the Anthropic API. "
                    "Never set this key in source code or commit it to version control."
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        else:
            self._client = None

    # ------------------------------------------------------------------
    # Preflight: model availability check
    # ------------------------------------------------------------------

    def verify_models_available(self) -> dict[str, bool]:
        """
        Call GET /v1/models and confirm both configured model IDs are present.

        Returns a dict of {model_id: True} for each available model.
        Raises ModelNotAvailable if either ID is absent.

        When use_synthetic_fixtures is True, returns success without calling
        the live API (for test use only).
        """
        if self.use_synthetic_fixtures:
            return {
                self.agent_model_id: True,
                self.evaluator_model_id: True,
            }

        available_ids: set[str] = set()
        for model in self._client.models.list():
            available_ids.add(model.id)

        result: dict[str, bool] = {}
        missing: list[str] = []
        for mid in (self.agent_model_id, self.evaluator_model_id):
            if mid in available_ids:
                result[mid] = True
            else:
                missing.append(mid)
                result[mid] = False

        if missing:
            raise ModelNotAvailable(
                f"Configured model(s) not found in GET /v1/models: {missing}. "
                f"Preflight fails closed — do not proceed to confirmation."
            )
        return result

    # ------------------------------------------------------------------
    # Core call
    # ------------------------------------------------------------------

    def call(
        self,
        model_id: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
    ) -> tuple[str, ResponseTelemetry]:
        """
        Call the Anthropic Messages API with the given messages and return
        (response_text, telemetry).

        The locked model ID is verified against response.model; a mismatch
        raises ResponseModelMismatch.  Missing usage fields are logged in
        telemetry with None values; they are never estimated.
        """
        if self.use_synthetic_fixtures:
            return self._synthetic_response(model_id)

        pricing = pricing_record_for_model(model_id)
        kwargs: dict[str, Any] = {
            "model":      model_id,
            "max_tokens": self.max_tokens,
            "messages":   messages,
        }
        if system:
            kwargs["system"] = system

        t0 = time.monotonic()
        with self._client.messages.with_raw_response.create(**kwargs) as raw:
            response    = raw.parse()
            latency_ms  = (time.monotonic() - t0) * 1000.0
            request_id  = raw.headers.get("request-id") or raw.headers.get("x-request-id")

        # Reject if response model differs from the locked model
        if response.model != model_id:
            raise ResponseModelMismatch(
                f"response.model='{response.model}' != locked model='{model_id}'. "
                f"This call cannot be used for confirmation."
            )

        usage = response.usage
        input_tokens  = getattr(usage, "input_tokens",  None)
        output_tokens = getattr(usage, "output_tokens", None)
        cache_create  = getattr(usage, "cache_creation_input_tokens", None)
        cache_read    = getattr(usage, "cache_read_input_tokens",     None)

        # Fail closed on missing required telemetry
        if input_tokens is None or output_tokens is None:
            raise MissingUsage(
                f"response.usage is missing input_tokens or output_tokens "
                f"for model '{model_id}'. "
                "Missing token counts cannot be estimated; this call cannot "
                "be used for confirmation cost accounting."
            )
        if not response.id:
            raise MissingUsage(
                f"response.id (message_id) is absent for model '{model_id}'. "
                "Provider-supplied message identity is required for confirmation."
            )
        if not request_id:
            raise MissingUsage(
                f"HTTP request-id header is absent for model '{model_id}'. "
                "Provider-supplied request identity is required for confirmation."
            )

        # Reject cache usage when caching is disabled
        lock = self._pricing_lock
        constraints = lock.get("confirmation_constraints", {})
        if constraints.get("prompt_caching_disabled", False):
            if (cache_create and cache_create > 0) or (cache_read and cache_read > 0):
                raise CacheUsageViolation(
                    f"Cache tokens present (creation={cache_create}, read={cache_read}) "
                    f"but prompt_caching_disabled=true in pricing_lock.json. "
                    "Disable caching before running a confirmation or update the "
                    "pricing lock to apply cache pricing."
                )

        cost = compute_provider_cost_usd(pricing, input_tokens, output_tokens)

        telemetry = ResponseTelemetry(
            model_id_requested              = model_id,
            model_id_returned               = response.model,
            message_id                      = response.id,
            request_id                      = request_id,
            input_tokens                    = input_tokens,
            output_tokens                   = output_tokens,
            cache_creation_input_tokens     = cache_create,
            cache_read_input_tokens         = cache_read,
            stop_reason                     = str(response.stop_reason) if response.stop_reason else None,
            http_request_id                 = request_id,
            latency_ms                      = latency_ms,
            pricing_lock_sha256             = self._pricing_lock_sha,
            provider_cost_usd               = cost,
            retry_count                     = 0,
            retry_exhausted                 = False,
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        return "\n".join(text_blocks), telemetry

    # ------------------------------------------------------------------
    # Synthetic fixtures (tests only)
    # ------------------------------------------------------------------

    def _synthetic_response(
        self, model_id: str
    ) -> tuple[str, ResponseTelemetry]:
        """
        Return a deterministic synthetic response for unit tests.
        The model_id_returned field matches the requested ID, simulating a
        correctly identified API response.  Never call the live API.
        """
        pricing = pricing_record_for_model(model_id)
        cost = compute_provider_cost_usd(pricing, 100, 50)
        telemetry = ResponseTelemetry(
            model_id_requested              = model_id,
            model_id_returned               = model_id,
            message_id                      = "msg_synthetic_fixture",
            request_id                      = "req_synthetic_fixture",
            input_tokens                    = 100,
            output_tokens                   = 50,
            cache_creation_input_tokens     = None,
            cache_read_input_tokens         = None,
            stop_reason                     = "end_turn",
            http_request_id                 = "req_synthetic_fixture",
            latency_ms                      = 0.0,
            pricing_lock_sha256             = self._pricing_lock_sha,
            provider_cost_usd               = cost,
            retry_count                     = 0,
            retry_exhausted                 = False,
        )
        return "Synthetic response for unit tests.", telemetry

    # ------------------------------------------------------------------
    # Log redaction helper
    # ------------------------------------------------------------------

    @staticmethod
    def redact_key(text: str) -> str:
        """Replace any API key-shaped token (sk-ant-...) in text with [REDACTED]."""
        import re
        return re.sub(r"sk-ant-[A-Za-z0-9\-_]+", "[REDACTED]", text)
