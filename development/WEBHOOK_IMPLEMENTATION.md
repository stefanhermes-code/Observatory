# Make.com Webhook Integration - Implementation Guide

## Overview

The PU Observatory platform now includes webhook integration with Make.com (formerly Integromat) to automatically notify external systems when orders are placed.

## Features

- ✅ **Asynchronous HTTP POST** - Non-blocking webhook calls
- ✅ **Fail-Open Design** - Webhook failures don't break order creation
- ✅ **Idempotency** - Unique `request_id` included in every call
- ✅ **Resilience** - 3 retry attempts with exponential backoff
- ✅ **Timeout Protection** - 5-second timeout per attempt
- ✅ **Authentication** - X-Webhook-Secret header support
- ✅ **Comprehensive Logging** - Success/failure tracking with response codes

## Configuration

### Environment Variables

Add these to your `.env` file (local) or Streamlit Cloud secrets:

```toml
# Make.com Webhook Configuration
ORDER_WEBHOOK_URL = "https://hook.integromat.com/your-webhook-url-here"
WEBHOOK_SECRET = "your-shared-secret-here"
SOURCE_APP = "pu_observatory"  # Optional: defaults to "pu_observatory"
```

### Required Variables

- **ORDER_WEBHOOK_URL**: Make.com webhook URL (required for webhooks to work)
- **WEBHOOK_SECRET**: Shared secret for authentication (optional but recommended)
- **SOURCE_APP**: Application identifier (optional, defaults to "pu_observatory")

### Optional Behavior

- If `ORDER_WEBHOOK_URL` is not set, webhooks are silently skipped (no errors)
- If `WEBHOOK_SECRET` is not set, no authentication header is sent
- If `SOURCE_APP` is not set, defaults to `"pu_observatory"`

## Webhook Payload

When an order is successfully created, the following payload is sent to Make.com:

```json
{
  "event_type": "order_submitted",
  "source_app": "pu_observatory",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "submitted_at": "2025-01-15T10:30:00.000Z",
  "status": "pending_review",
  "contact_email": "customer@example.com",
  "company_name": "Example Company Ltd",
  "newsletter_name": "HTC Global Market Intelligence",
  "product_name": "HTC Global Market Intelligence",
  "pricing": {
    "amount": 228.0,
    "currency": "USD",
    "cadence": "monthly",
    "price_per_user_monthly": 19.0,
    "price_per_user_yearly": 228.0,
    "breakdown": {
      "cadence": {
        "type": "monthly",
        "price_per_user_monthly": 19.0,
        "price_per_user_yearly": 228.0,
        "label": "Monthly"
      },
      "users": {
        "count": 1,
        "note": "Pricing is per user"
      },
      "scope": {
        "categories_count": 3,
        "regions_count": 1,
        "tier": "Starter",
        "multiplier": 1.0,
        "base_price_per_user_monthly": 19.0,
        "note": "Scope determines package tier (Starter package, 1.0x multiplier)..."
      },
      "total_monthly": 19.0,
      "total_yearly": 228.0
    }
  }
}
```

### Payload Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Always `"order_submitted"` |
| `source_app` | string | `"pu_observatory"` or `"pu_ondemand_training"` |
| `request_id` | string | Unique UUID (idempotency key) |
| `submitted_at` | string | ISO 8601 timestamp |
| `status` | string | Always `"pending_review"` |
| `contact_email` | string | Customer contact email |
| `company_name` | string | Company name |
| `newsletter_name` | string | Product/newsletter name (Observatory internal) |
| `product_name` | string | Product name (same as newsletter_name; required by Make.com Order Intent / Deal flow) |
| `pricing` | object | Pricing details (see below) |

### Pricing Object

| Field | Type | Description |
|-------|------|-------------|
| `amount` | number | Total annual price (USD) |
| `currency` | string | Currency code (`"USD"`) |
| `cadence` | string | `"daily"`, `"weekly"`, or `"monthly"` |
| `price_per_user_monthly` | number | Price per user per month |
| `price_per_user_yearly` | number | Price per user per year |
| `breakdown` | object | Detailed pricing breakdown |

## HTTP Headers

The webhook includes the following headers:

```
Content-Type: application/json
User-Agent: PU-Observatory-Webhook/1.0
X-Webhook-Secret: <your-webhook-secret>  # Only if WEBHOOK_SECRET is configured
```

## Retry Logic

The webhook implements automatic retry with exponential backoff:

1. **Attempt 1**: Immediate
2. **Attempt 2**: After 1 second delay
3. **Attempt 3**: After 2 seconds delay

**Total maximum time**: ~8 seconds (5s timeout × 3 attempts + delays)

### Retry Behavior

- ✅ **2xx responses**: Success, no retry
- ⚠️ **4xx responses** (except 429): Client error, no retry
- ⚠️ **429 (Rate Limit)**: Retry with backoff
- ⚠️ **5xx responses**: Server error, retry with backoff
- ⚠️ **Timeout**: Retry with backoff
- ⚠️ **Connection errors**: Retry with backoff

## Logging

All webhook attempts are logged with the following information:

- **Success**: Request ID, attempt number, HTTP status code
- **Failure**: Request ID, attempt number, error type, error message

### Log Levels

- **INFO**: Successful webhook calls
- **WARNING**: Retryable failures (timeouts, connection errors)
- **ERROR**: Final failure after all retries, client errors (4xx)

### Example Log Messages

```
INFO: Webhook thread started for request_id: 550e8400-e29b-41d4-a716-446655440000
INFO: Webhook attempt 1/3 for request_id: 550e8400-e29b-41d4-a716-446655440000
INFO: Webhook success for request_id: 550e8400-e29b-41d4-a716-446655440000 (attempt 1/3, status: 200)
```

## Error Handling

### Fail-Open Design

**Critical Principle**: Webhook failures **never** break order creation.

- Order is saved to database **before** webhook is called
- Webhook runs in background thread (non-blocking)
- All webhook errors are caught and logged
- User sees success message even if webhook fails

### Error Scenarios

1. **Webhook URL not configured**: Silently skipped, no error
2. **Network timeout**: Retried 3 times, then logged as error
3. **Connection error**: Retried 3 times, then logged as error
4. **HTTP 4xx error**: Logged as error, not retried (except 429)
5. **HTTP 5xx error**: Retried 3 times, then logged as error
6. **Pricing calculation failure**: Uses default pricing (0 USD)

## Make.com Integration

### Connection to Dashboard HTC Global / Deal Creation Flow

The webhook is designed to connect to the **Order Intent Webhook Flow** in Make.com, which feeds the **Dashboard HTC Global** approval queue and the **Deal Creation (eWay)** flow:

1. **Observatory** → On order submission, `create_specification_request()` in `core/database.py` calls `send_order_webhook_async()` with a payload that includes `product_name` (same as `newsletter_name`), `company_name`, `contact_email`, and `pricing`.
2. **Make.com Order Intent Webhook Flow** – Trigger: Custom Webhook. It expects `product_name`, `pricing` (stored as `pricing_json` in Supabase), `company_name`, `contact_email`, etc. The payload sent by Observatory matches this; `product_name` is included so the flow can map to Supabase and downstream Deal creation.
3. **Dashboard HTC Global** – Reads from Supabase `order_intent_events` (or equivalent) for the approval queue.
4. **Deal Creation (Doc 7)** – After approval, Make.com creates deals in eWay using `company_name`, `product_name`, `contact_email`, `pricing_json.amount`, `pricing_json.currency`.

**To enable the connection:** Set `ORDER_WEBHOOK_URL` in the Observatory deployment (Streamlit Cloud secrets or `.env`) to your Make.com Order Intent webhook URL (e.g. `https://hook.eu2.make.com/...`). Set `WEBHOOK_SECRET` if your Make.com scenario validates the `X-Webhook-Secret` header.

### Expected Make.com Workflow

1. **Receive Webhook** - Make.com receives POST request
2. **Validate Secret** - Check X-Webhook-Secret header (if configured)
3. **Write to Supabase** - Store event in Supabase table (e.g. `order_intent_events`)
4. **Deal Control Logic** - Trigger business logic based on rules
5. **eWay Deal Creation** - Create deal in eWay system (uses `product_name`, `company_name`, `contact_email`, `pricing`)

### Idempotency Handling

Make.com should deduplicate events based on `request_id`:

- `request_id` is a UUID and is unique per order
- If Make.com receives duplicate `request_id`, it should skip processing
- This prevents duplicate deals/records if webhook is retried

## Testing

### Local Testing

1. Set `ORDER_WEBHOOK_URL` in `.env` file
2. Use a test webhook URL (e.g., https://webhook.site)
3. Submit an order via Configurator app
4. Check webhook.site for received payload
5. Verify logs for webhook attempts

### Production Testing

1. Configure webhook URL in Streamlit Cloud secrets
2. Submit a test order
3. Check Make.com execution logs
4. Verify event appears in Supabase
5. Confirm deal creation in eWay

## Troubleshooting

### Webhook Not Firing

1. Check `ORDER_WEBHOOK_URL` is set in secrets
2. Verify webhook URL is correct (no typos)
3. Check application logs for webhook errors
4. Verify `requests` library is installed (`pip install requests`)

### Webhook Failing

1. Check Make.com webhook URL is active
2. Verify `WEBHOOK_SECRET` matches Make.com configuration
3. Check network connectivity from Streamlit Cloud
4. Review logs for specific error messages
5. Test webhook URL manually with curl/Postman

### Duplicate Events

1. Verify Make.com deduplicates on `request_id`
2. Check if webhook is being called multiple times (shouldn't happen)
3. Review retry logic - should only retry on failure

## Code Structure

### Files Modified

- `core/webhook.py` - New webhook module
- `core/database.py` - Integrated webhook call
- `requirements.txt` - Added `requests` dependency
- `streamlit_secrets_template.toml` - Added webhook config

### Key Functions

- `send_order_webhook_async()` - Entry point (non-blocking)
- `_send_webhook_sync()` - Synchronous sender with retry logic
- `build_order_webhook_payload()` - Payload builder
- `get_webhook_config()` - Configuration loader

## Security Considerations

1. **Secret Authentication**: Use `WEBHOOK_SECRET` for authentication
2. **HTTPS Only**: Webhook URL should use HTTPS
3. **Idempotency**: `request_id` prevents duplicate processing
4. **Fail-Open**: Errors don't expose sensitive data
5. **Logging**: No sensitive data in logs (only request_id and status)

## Future Enhancements

Potential improvements:

- Webhook status tracking in database
- Admin UI for webhook status monitoring
- Webhook retry queue for failed calls
- Multiple webhook endpoints support
- Webhook payload customization per endpoint

---

**Implementation Date**: 2025-01-XX  
**Version**: 1.0  
**Status**: Production Ready

