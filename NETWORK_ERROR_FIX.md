# Network Error Debugging - Complete Guide

## Your Error
```
Network error while contacting backend
```

This means the frontend **cannot reach** the backend on `http://localhost:5000`. This is a **connectivity issue**, not an application logic error.

---

## Quick Diagnosis (2 minutes)

### Step 1: Backend Running?
Open **PowerShell** and run:
```powershell
python -c "import requests; r = requests.get('http://localhost:5000/health'); print(f'Status: {r.status_code}'); print(f'Response: {r.text}')"
```

**Expected output:**
```
Status: 200
Response: {
  "service": "AcadClarifier Backend",
  "status": "ok"
}
```

**If you get connection error:**
- Backend is NOT running
- Go to next step

### Step 2: Start Backend
Open a terminal and run:
```bash
cd d:\BE Project\Acadclarifier
python -m apps.backend.server
```

**You should see:**
```
 * Running on http://0.0.0.0:5000
```

**Keep this terminal open!**

### Step 3: Start Frontend  
Open **another** terminal and run:
```bash
cd d:\BE Project\Acadclarifier
python app.py
```

**You should see:**
```
Static frontend running at http://localhost:8501
```

**Keep this terminal open too!**

### Step 4: Test in Browser
1. Open http://localhost:8501 in your browser
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Paste and run:
```javascript
await (new NetworkDiagnostics()).runAllTests()
```

This will tell you exactly what's wrong.

---

## Detailed Troubleshooting

### Problem 1: Backend Won't Start

**Error:** `Address already in use` or `Port 5000 already in use`

**Solution:**
```powershell
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or use a different port
# Edit apps/backend/server.py, change:
# app.run(host="0.0.0.0", port=5001, ...)
# Then start with: python -m apps.backend.server
```

---

### Problem 2: Health Check Works, But Frontend Still Fails

**Symptom:** 
- `python ... requests.get(...).json()` works fine
- But frontend shows "Network error"

**Likely causes:**

#### 2a: CORS Issue
The browser might be blocking the request due to CORS policy.

**Debug in browser console:**
```javascript
fetch('http://localhost:5000/health')
  .then(r => r.json())
  .then(d => console.log(d))
  .catch(e => console.error('CORS ERROR:', e.message))
```

**If you see:** `CORS policy blocked`

**Solution:** Already handled! `CORS(app)` is in server.py. Try:
- Hard refresh: **Ctrl+Shift+R**
- Clear browser cache: **Ctrl+Shift+Delete**
- Try incognito window: **Ctrl+Shift+N**

#### 2b: Wrong API URL
Frontend might be using wrong backend URL.

**Check in browser console:**
```javascript
// These should print:
console.log('Frontend location:', window.location.hostname, window.location.port)
console.log('Should contact:', 'http://localhost:5000')
```

**If frontend is running on different port (not localhost:8501):**
- Edit `apps/frontend/js/api.js`
- Change `LOCAL_API_BASE = 'http://localhost:5000'` to your actual backend URL

#### 2c: Browser Timeout
Request might be timing out.

**Check:**
```javascript
// This tests with timeout
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000);

fetch('http://localhost:5000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: 'test', book_ref: 'book-1' }),
  signal: controller.signal
})
  .then(r => r.json())
  .then(d => console.log('Success:', d))
  .catch(e => console.error('Error:', e.message))
  .finally(() => clearTimeout(timeoutId))
```

---

### Problem 3: Backend Returns 500 Error

**Symptom:** Network tab shows `POST /ask` returns HTTP 500

**This means:**
- Backend received the request
- Backend encountered an error processing it

**To debug:**
1. Check backend terminal for error message
2. Look for full traceback/stack trace

**Common 500 causes:**
- Book embeddings not generated: `python services/retrieval-local/scripts/chunks_to_vectors.py`
- GEMINI_API_KEY invalid: Check `.env` file has valid key
- Query parsing issue: Check browser console for request body

**Solution:**
```bash
# Verify embeddings exist for all books
ls d:\BE Project\Acadclarifier\services\retrieval-local\outputs\embeddings_output\

# Should show: book-1, book-2, ..., book-10

# If missing, regenerate:
cd d:\BE Project\Acadclarifier\services\retrieval-local\scripts
python chunks_to_vectors.py
```

---

### Problem 4: Book Not Found / Selection Issues

**Symptom:** Can select books BUT getting errors about book not found

**Debug:**
```javascript
// In browser console, after selecting a book:
console.log('Selected book:', document.getElementById('local-question')?.dataset.bookRef)

// Or check state:
// (if app exports state)
```

**Solution:**
1. Go to "Explore Library" 
2. Select a book from the list
3. Book name should appear below the search box
4. Then try asking a question

---

## Complete Diagnostic Checklist

- [ ] Backend starts with `python -m apps.backend.server`
- [ ] Backend confirms: `Running on http://0.0.0.0:5000`
- [ ] Terminal test works: `python -c "import requests..."`
- [ ] Status 200 returned from health check
- [ ] Frontend starts with `python app.py`
- [ ] Frontend loads at `http://localhost:8501`
- [ ] Browser console has `testBackendConnection` function
- [ ] Running `testBackendConnection()` shows all ✅
- [ ] Network tab in DevTools shows requests to localhost:5000
- [ ] Requests are not blocked (not red X)
- [ ] Response status is 2xx, 4xx, or 5xx (not 0)
- [ ] Book is selected before asking question
- [ ] Question is filled in (not empty)
- [ ] Book embeddings exist (`book-1` through `book-10` folders)
- [ ] `.env` file has `GEMINI_API_KEY`

---

## Data Verification

Verify all necessary data exists:

```powershell
# Check embeddings
Get-ChildItem "D:\BE Project\Acadclarifier\services\retrieval-local\outputs\embeddings_output" -Directory

# Check query outputs (from manual tests)
Get-ChildItem "D:\BE Project\Acadclarifier\services\retrieval-local\outputs\query_output" -Directory

# Check final outputs (simplified results)
Get-ChildItem "D:\BE Project\Acadclarifier\services\retrieval-local\outputs\final_output" -Directory
```

All should show files/folders for each book.

---

## If Still Failing

### Collect This Information:

1. **Backend Terminal Output** (Copy entire terminal content)
2. **Frontend Terminal Output** (Copy entire terminal content)
3. **Browser Console Output** (F12 → Console → Right-click copy)
4. **Network Tab Details** (F12 → Network → POST /ask request)
5. **Environment Check**:
   ```powershell
   python --version
   pip list | findstr -E "flask|cors|chromadb|sentence|google"
   ```

### Escalation Path:

If diagnostics don't reveal the issue:
1. Check `apps/backend/config.py` for database config
2. Check `.env` files for all required keys
3. Run: `python test_backend_ready.py` to verify structure
4. Run browser diagnostic: `await (new NetworkDiagnostics()).runAllTests()`

---

## Files for Diagnostics

These files were created to help debug:
- `test_backend_ready.py` - Quick backend structure check
- `test_pipeline.py` - Full pipeline import test
- `apps/frontend/js/diagnostic.js` - Simple browser diagnostics
- `apps/frontend/js/diagnostic-advanced.js` - Advanced browser diagnostics

All can be removed once issue is fixed.

---

## Success Indicators

Once working, you should:
1. ✅ See book name displayed after selection
2. ✅ Book retrieval page unlocks (no longer grayed out)
3. ✅ Questions can be typed into the input
4. ✅ Response appears after submission
5. ✅ Network tab shows HTTP 200 for POST /ask
