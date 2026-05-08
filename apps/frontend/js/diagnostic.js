/**
 * Diagnostic tool to test frontend-backend connectivity
 * Run in browser console and check results
 */

async function testBackendConnection() {
  console.log('🔍 Starting backend connectivity diagnostics...\n');

  // Test 1: Health check
  console.log('Test 1: Backend health check');
  try {
    const response = await fetch('http://localhost:5000/health', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    console.log(`  ✓ Request sent successfully`);
    console.log(`  Status: ${response.status} ${response.statusText}`);
    console.log(`  Headers:`, Object.fromEntries(response.headers));
    const data = await response.json();
    console.log(`  Response body:`, data);
    console.log('✅ Health check successful\n');
  } catch (error) {
    console.error('❌ Health check failed:');
    console.error(`  Error: ${error.message}`);
    console.error(`  Error name: ${error.name}`);
    console.error(`  Error stack:`, error.stack);
    console.error('');
  }

  // Test 2: CORS preflight simulation
  console.log('Test 2: CORS preflight (OPTIONS request)');
  try {
    const response = await fetch('http://localhost:5000/ask', {
      method: 'OPTIONS',
      headers: {
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
      },
    });
    console.log(`  ✓ OPTIONS request successful`);
    console.log(`  Status: ${response.status}`);
    console.log(`  CORS Headers:`, {
      'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
      'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
      'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
    });
    console.log('✅ CORS preflight successful\n');
  } catch (error) {
    console.error('❌ CORS preflight failed:');
    console.error(`  Error: ${error.message}\n`);
  }

  // Test 3: Simple POST request
  console.log('Test 3: Sample POST request to /ask endpoint');
  try {
    const response = await fetch('http://localhost:5000/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: 'Test question',
        book_ref: 'book-1',
      }),
    });
    console.log(`  ✓ POST request sent successfully`);
    console.log(`  Status: ${response.status} ${response.statusText}`);
    const data = await response.json();
    console.log(`  Response:`, data);
    console.log('✅ POST request successful\n');
  } catch (error) {
    console.error('❌ POST request failed:');
    console.error(`  Error: ${error.message}`);
    console.error(`  Error name: ${error.name}\n`);
  }

  // Test 4: Check API_BASE from actual module
  console.log('Test 4: Check API configuration');
  try {
    const apiModule = await import('./api.js');
    console.log(`  Window location:`, window.location.hostname, window.location.port);
    console.log(`  Expected API Base: http://localhost:5000`);
    console.log('✅ API configuration check complete\n');
  } catch (error) {
    console.error('❌ Could not load API module:', error.message);
  }

  console.log('📊 Diagnostics complete!');
  console.log('\nIf you see "CORS header missing" or "Network error", the issue is one of:');
  console.log('  1. Backend not actually running on port 5000');
  console.log('  2. Firewall blocking localhost:5000');
  console.log('  3. Backend listening on wrong interface (127.0.0.1 vs 0.0.0.0)');
  console.log('  4. Browser security policy (rare on localhost)');
}

// Export for browser console
window.testBackendConnection = testBackendConnection;
console.log('✅ Diagnostic tools loaded. Run: testBackendConnection()');
