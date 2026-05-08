# Quick Reference: Network Error Fix

## TL;DR - The Issue

Frontend shows "Network error while contacting backend" when trying to use local book retrieval.

## TL;DR - The Fix

### 1. Ensure Both Servers Running

**Terminal 1** (Backend):
```bash
cd d:\BE Project\Acadclarifier
python -m apps.backend.server
```
Wait for: `Running on http://0.0.0.0:5000`

**Terminal 2** (Frontend):
```bash
cd d:\BE Project\Acadclarifier
python app.py
```
Wait for: `Static frontend running at http://localhost:8501`

### 2. Test in Browser

1. Open http://localhost:8501
2. Press **F12** (Developer Tools)
3. Go to **Console** tab
4. Paste and run BOTH:
```javascript
testBackendConnection()
```

5. If that works, run:
```javascript
await (new NetworkDiagnostics()).runAllTests()
```

### 3. Look for Errors

The tests will show you **exactly** what's wrong:
- ❌ Backend not running
- ❌ CORS blocked
- ❌ Connection refused
- ❌ Port already in use
- ✅ All tests pass → issue is elsewhere

## Verification Checklist

- [ ] Backend started: `python -m apps.backend.server`
- [ ] See: `Running on http://0.0.0.0:5000`
- [ ] Frontend started: `python app.py`
- [ ] See: `Static frontend running at http://localhost:8501`
- [ ] Browser can access http://localhost:8501
- [ ] Browser console runs `testBackendConnection()`
- [ ] All tests show ✅
- [ ] Book is selected
- [ ] Question is typed
- [ ] No "Network error"

## Fast Diagnostics Commands

```powershell
# Check if backend responds
python -c "import requests; print(requests.get('http://localhost:5000/health').json())"

# Check what's using port 5000
netstat -ano | findstr :5000

# Restart everything
# Terminal 1:
python -m apps.backend.server

# Terminal 2:
python app.py
```

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "Network error" | Backend not running | Start: `python -m apps.backend.server` |
| Connection refused | Wrong port/bind | Check port 5000 free: `netstat -ano \| findstr :5000` |
| CORS error | Browser blocking | Hard refresh: Ctrl+Shift+R |
| Timeout error | Slow response | Normal on first request, wait longer |
| 500 error | Backend crashes | Check terminal output for traceback |
| Book not in list | Embeddings missing | Run: `python services/retrieval-local/scripts/chunks_to_vectors.py` |

## Diagnostic Tools Available

In browser console:

**Simple test:**
```javascript
testBackendConnection()  // ✅ Basic connectivity
```

**Detailed test:**
```javascript
await (new NetworkDiagnostics()).runAllTests()  // ✅ Complete diagnosis
```

## Still Not Working?

1. Collect detailed error info:
   - Backend terminal entire output
   - Frontend terminal entire output
   - Browser console (F12 → Console tab)
   - Network tab (F12 → Network tab, show POST /ask request)

2. Check documentation:
   - `NETWORK_ERROR_FIX.md` - Full troubleshooting
   - `CONNECTIVITY_DEBUGGING.md` - Step-by-step guide
   - `INVESTIGATION_SUMMARY.md` - What was verified

3. Verify data exists:
   ```powershell
   Get-ChildItem "D:\BE Project\Acadclarifier\services\retrieval-local\outputs\embeddings_output"
   # Should show: book-1, book-2, ..., book-10
   ```

4. Run verification script:
   ```bash
   python test_backend_ready.py  # Backend structure check
   ```

---

## File Locations Reference

| File | Purpose |
|------|---------|
| `apps/backend/server.py` | Backend Flask app |
| `apps/frontend/app.py` | Frontend server |
| `apps/backend/routes.py` | API endpoints |
| `apps/frontend/js/api.js` | Frontend API client |
| `apps/frontend/js/diagnostic.js` | Simple browser test |
| `apps/frontend/js/diagnostic-advanced.js` | Advanced browser test |
| `.env` | API keys config |
| `test_backend_ready.py` | Backend verification |
| `NETWORK_ERROR_FIX.md` | Complete fix guide |

---

## Success = You Should See

After fix applied:
1. ✅ Select book → book name appears
2. ✅ Type question → input unlocked
3. ✅ Click Send → loading indicator appears
4. ✅ Response → formatted answer with sources
5. ✅ Network tab → POST /ask returns HTTP 200

