# Gemini AI Bridge (Consultant-Only)

This module provides a read-only interface to the Gemini API.

## Policy: Consultant-Only
- Gemini acts strictly as a cognitive consultant.
- It generates candidates and packets for review.
- No operational execution or state mutation is allowed from this module.
- Every request is wrapped with authority boundaries.

## Schema
Responses always include:
- `authority`: `candidate_only`
- `mutation_allowed`: `false`