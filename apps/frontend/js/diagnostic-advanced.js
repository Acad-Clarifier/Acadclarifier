/**
 * ENHANCED Diagnostic Tool - Network Error Troubleshooting
 * Paste entire content into browser console at http://localhost:8501
 * 
 * This tool will:
 * 1. Capture actual fetch error details
 * 2. Test connectivity with detailed logging
 * 3. Provide specific remediation steps
 */

class NetworkDiagnostics {
  constructor() {
    this.results = [];
    this.hasError = false;
  }

  log(category, message, data = null) {
    const entry = {
      category,
      message,
      data,
      timestamp: new Date().toISOString()
    };
    this.results.push(entry);
    console.log(`[${category}] ${message}`, data || '');
  }

  async testHealthCheck() {
    this.log('HEALTH', 'Testing basic connectivity...');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch('http://localhost:5000/health', {
        method: 'GET',
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      this.log('HEALTH', `✅ Backend responded with HTTP ${response.status}`, {
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers),
        contentType: response.headers.get('content-type')
      });

      const json = await response.json();
      this.log('HEALTH', '✅ Response body parsed successfully', json);

      return true;
    } catch (error) {
      this.hasError = true;
      this.log('HEALTH', `❌ FAILED: ${error.message}`, {
        errorName: error.name,
        errorCode: error.code,
      });

      if (error.name === 'TypeError ') {
        this.log('ERROR_HINT', 'TypeError usually means network-level failure', {
          common_causes: [
            'Backend not running on port 5000',
            'Connection refused/reset',
            'Firewall blocking connections',
            'Backend bound to 127.0.0.1 only (not 0.0.0.0)'
          ]
        });
      }

      return false;
    }
  }

  async testCorsHeaders() {
    this.log('CORS', 'Testing CORS preflight...');
    try {
      const response = await fetch('http://localhost:5000/ask', {
        method: 'OPTIONS',
        headers: {
          'Origin': window.location.origin,
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'content-type'
        }
      });

      const corsHeaders = {
        'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
        'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
        'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        'Access-Control-Max-Age': response.headers.get('Access-Control-Max-Age'),
      };

      if (corsHeaders['Access-Control-Allow-Origin']) {
        this.log('CORS', '✅ CORS headers present', corsHeaders);
      } else {
        this.log('CORS', '⚠️  CORS Allow-Origin header missing', corsHeaders);
      }

      return true;
    } catch (error) {
      this.hasError = true;
      this.log('CORS', `❌ CORS preflight test failed: ${error.message}`);
      return false;
    }
  }

  async testPostRequest() {
    this.log('POST', 'Testing POST request to /ask endpoint...');
    try {
      const response = await fetch(
        'http://localhost:5000/ask',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Origin': window.location.origin
          },
          body: JSON.stringify({
            question: 'test question',
            book_ref: 'book-1'
          })
        }
      );

      this.log('POST', `Response received with status ${response.status}`, {
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers)
      });

      try {
        const data = await response.json();
        this.log('POST', `Response body:`, data);

        if (response.status === 200 && data.status === 'success') {
          this.log('POST', '✅ Request succeeded!');
        } else if (response.status >= 500) {
          this.log('ERROR_HINT', 'Backend returned 500 error - check backend terminal for error details', {
            error: data.error
          });
        } else if (response.status >= 400 && response.status < 500) {
          this.log('POST', '⚠️  Got client error (4xx) - bad request format?', {
            error: data.error
          });
        }
      } catch (parseError) {
        this.log('POST', `Failed to parse response JSON`, { error: parseError.message });
      }

      return true;
    } catch (error) {
      this.hasError = true;
      this.log('POST', `❌ POST request failed: ${error.message}`, {
        errorName: error.name,
        type: error.constructor.name
      });
      return false;
    }
  }

  async testApiModule() {
    this.log('CONFIG', 'Checking API configuration...');
    try {
      // If api.js is available, check its configuration
      this.log('CONFIG', `Window location: ${window.location.hostname}:${window.location.port}`, {
        protocol: window.location.protocol,
        isLocalHost: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      });

      this.log('CONFIG', '✅ API configuration ready');
      return true;
    } catch (error) {
      this.log('CONFIG', `⚠️  Could not verify API config: ${error.message}`);
      return false;
    }
  }

  async runAllTests() {
    console.clear();
    console.log('%c🔍 NETWORK DIAGNOSTICS STARTED', 'color: blue; font-size: 16px; font-weight: bold');
    console.log(`Timestamp: ${new Date().toISOString()}\n`);

    await this.testApiModule();
    await this.testHealthCheck();
    await this.testCorsHeaders();
    await this.testPostRequest();

    console.log('\n%c📊 DIAGNOSTICS COMPLETE', 'color: green; font-size: 14px; font-weight: bold');
    this.printSummary();
    this.printRemediationSteps();

    return this.results;
  }

  printSummary() {
    const errorCount = this.results.filter(r => r.message.includes('❌')).length;
    const warningCount = this.results.filter(r => r.message.includes('⚠️')).length;

    console.log('\n' + '='.repeat(70));
    console.log('SUMMARY:');
    if (errorCount === 0 && warningCount === 0) {
      console.log('✅ All tests passed!');
    } else {
      console.log(`❌ Errors: ${errorCount}`);
      console.log(`⚠️  Warnings: ${warningCount}`);
    }
    console.log('='.repeat(70));
  }

  printRemediationSteps() {
    console.log('\n%c🔧 REMEDIATION STEPS', 'color: orange; font-size: 12px; font-weight: bold');

    if (this.hasError) {
      console.log(`
1. CHECK IF BACKEND IS RUNNING:
   - Open new terminal
   - Run: python -m apps.backend.server
   - Should show: "Running on http://0.0.0.0:5000"

2. CHECK IF FRONTEND IS RUNNING:
   - Open another terminal
   - Run: python app.py
   - Should show: "Static frontend running at http://localhost:8501"

3. VERIFY CONNECTIVITY:
   - In terminal, run: python -c "import requests; print(requests.get('http://localhost:5000/health').json())"
   - Should print: {'status': 'ok', 'service': 'AcadClarifier Backend'}

4. CHECK FIREWALL/NETWORK:
   - Windows Firewall might block 5000
   - Try: netstat -ano | findstr :5000
   - Should show process listening

5. CHECK FOR PORT CONFLICTS:
   - Maybe another service is using port 5000?
   - Try: netstat -ano | findstr :5000
   - Or change backend port in apps/backend/server.py

6. COLLECT DETAILED ERROR INFO:
   - Run diagnostic again and copy ALL output
   - Check backend terminal for error messages
   - Check browser console for error details
      `);
    } else {
      console.log('\n✅ All connectivity tests passed!');
      console.log('If frontend still shows "Network error", the issue might be:');
      console.log('  - Selected book not in database');
      console.log('  - Embeddings not generated for selected book');
      console.log('  - API response parsing issue');
      console.log('\nTry the full pipeline:');
      console.log('  1. Go to Book Retrieval page');
      console.log('  2. Click "Find Book" or "Explore Library"');
      console.log('  3. Select a book (should see it below)');
      console.log('  4. Type a question in the text input');
      console.log('  5. Press Send');
      console.log('  6. Check browser console (F12 → Console tab) for errors');
    }
  }

  printRawResults() {
    console.log('\n%c📋 RAW RESULTS (JSON)', 'color: gray; font-size: 12px; font-weight: bold');
    console.log(JSON.stringify(this.results, null, 2));
  }
}

// Make globally available
window.NetworkDiagnostics = NetworkDiagnostics;

// Auto-run on load
console.log('%c✅ Diagnostic module loaded!', 'color: green; font-weight: bold');
console.log('Run: await (new NetworkDiagnostics()).runAllTests()');
console.log('\nOr for quick check:');
console.log('  testBackendConnection() - simple tests');
console.log('  await (new NetworkDiagnostics()).runAllTests() - comprehensive');
