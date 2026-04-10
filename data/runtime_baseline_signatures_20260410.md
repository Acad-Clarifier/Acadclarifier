# Runtime Baseline Signatures (2026-04-10)

## Baseline before fixes

### /ask (failing)

- HTTP status: 400
- API error payload signature:
  - status=error
  - error=retrieval failed
- Server log signature:
  - Error retrieving documents: Collection expecting embedding with dimension of 768, got 384

### /journal/recommend (observed behavior)

- HTTP status: 200
- Payload signature:
  - status=no_results
  - message=No journals found matching your query.
- Note: this endpoint did not fail in this local baseline run.

### /recommend (control)

- HTTP status: 200
- Payload signature:
  - status=ok
  - message=Recommendations fetched successfully (fallback mode)

## Verification after fixes

### /health repeated probes

- 5/5 requests returned HTTP 200.

### /ask repeated requests

- Endpoint no longer throws worker-level exception.
- Returns clean structured API error with mapped status:
  - HTTP 422
  - error=Collection expecting embedding with dimension of 768, got 384
  - error_code=chroma_embedding_dimension_mismatch
  - error_summary=embedding dimension mismatch

### /journal/recommend repeated requests

- 3/3 requests returned HTTP 200.
- Endpoint remained stable; no worker crash.

### /recommend control

- Still HTTP 200 with successful fallback-mode recommendations.

### sqlite/chromadb signature check

- No "unsupported version of sqlite3" signature observed in backend logs during verification.
