# Frontend-Backend Connectivity Debugging Guide

## Current Status
- ✅ Backend server running on http://localhost:5000  
- ✅ Backend health check responding correctly  
- ⚠️ Frontend cannot connect (Network error reported)
- ❓ Root cause: Unknown - needs browser diagnostics

## Verified Working
```
Backend Health Check:
  Status: 200 OK
  Response: {"status": "ok", "service": "AcadClarifier Backend"}
```

## Diagnostic Steps

### Step 1: Open Browser Developer Tools
1. Open your browser (Chrome, Firefox, Edge, Safari)
2. Press **F12** to open Developer Tools
3. Go to the **Console** tab

### Step 2: Run Diagnostic Tests
In the browser console, paste and run:
```javascript
testBackendConnection()
```

This will test:
- ✓ Backend health endpoint
- ✓ CORS preflight (OPTIONS request)
- ✓ POST request to /ask endpoint
- ✓ API configuration check

### Step 3: Check Network Tab
1. In DevTools, go to **Network** tab
2. Refresh the page (F5)
3. Click on "Book Retrieval" page
4. Select a book
5. Enter a test question and submit
6. Look for the POST request to `/ask`
7. Check:
   - **Status code** (should be 2xx, 4xx, or 5xx - NOT blocked)
   - **Request headers** (especially Host, origin)
   - **Response headers** (look for `Access-Control-Allow-*`)
   - **Response body** (error message details)

### Step 4: Inspect Console Errors
Look for:
- JavaScript errors (red messages)
- CORS policy violations (blocked by CORS)
- Net::ERR_* errors (network level)
- Connection refused messages

---

## Common Issues & Solutions

### Issue: "TypeError: Failed to fetch"
**Cause**: Network-level error, server unreachable  
**Solution**:
```bash
# Verify backend is running
python -c "import requests; print(requests.get('http://localhost:5000/health').json())"
```

### Issue: "Access to XMLHttpRequest blocked by CORS policy"
**Cause**: CORS headers missing or misconfigured  
**Current Config**: `CORS(app)` in server.py should allow all origins  
**Debug**:
```javascript
// In browser console
fetch('http://localhost:5000/health', { method: 'GET' })
  .then(r => {
    console.log('Headers:', Object.fromEntries(r.headers));
    return r.json();
  })
```

### Issue: "Connection refused" or "Net::ERR_CONNECTION_REFUSED"
**Cause**: Backend not listening or listening on wrong interface  
**Solution**:
```bash
# Check if port 5000 is listening
netstat -ano | findstr :5000

# Restart backend ensuring it binds to 0.0.0.0
python -m apps.backend.server
```

### Issue: "POST /ask returns 500 error"
**Cause**: Backend logic error in runtime_orchestrator or dependencies  
**Debug**:
```javascript
// Check response in Network tab for error message
// or run this in console:
fetch('http://localhost:5000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: 'test', book_ref: 'book-1' })
})
  .then(r => r.json())
  .then(data => console.log(JSON.stringify(data, null, 2)))
```

---

## Quick Validation Checklist

- [ ] Backend responds to `http://localhost:5000/health` (via Python!)
- [ ] Browser console has `testBackendConnection` function available
- [ ] Running `testBackendConnection()` completes without "Network error"
- [ ] Network tab shows POST /ask request (not blocked)
- [ ] Response status is not `0` (which means network failed)
- [ ] CORS headers present: `Access-Control-Allow-Origin: *` (or specific origin)

---

## If Still Failing

### Collect These Logs:
1. **Browser Console Output**: Copy entire console output
2. **Network Request Details**: 
   - Screenshot of Network tab showing /ask request
   - Full request headers
   - Full response headers
   - Full response body
3. **Backend Logs**: Check terminal where backend is running for error messages
4. **Environment**: 
   - Python version: `python --version`
   - Flask version: `python -c "import flask; print(flask.__version__)"`
   - OS: Windows/Mac/Linux

### Check These Files:
- [ ] `apps/backend/server.py` - CORS(app) is called
- [ ] `apps/backend/routes.py` - `/ask` endpoint exists
- [ ] `apps/frontend/js/api.js` - API_BASE set correctly
- [ ] `services/retrieval-local/scripts/runtime_orchestrator.py` - File exists
- [ ] `.env` files in both `apps/backend/` and `services/retrieval-local/` - Have GEMINI_API_KEY

---

## Files Modified for Diagnostics

- ✅ `apps/frontend/js/diagnostic.js` - Created with testing functions
- ✅ `apps/frontend/index.html` - Added diagnostic script include

These can be removed later once issue is resolved.
