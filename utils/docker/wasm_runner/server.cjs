const WebSocket = require('ws');
const http = require('http');
const puppeteer = require('puppeteer');
const { exec } = require('child_process');
const fs = require('fs');

const coinsPath = '/home/node/.kdf/coins';
const staticCoinsPath = '/home/node/dist/coins.json';

if (fs.existsSync(coinsPath)) {
  console.log(`Found coins file at ${coinsPath}, copying to ${staticCoinsPath}`);
  try {
    // Ensure dist directory exists
    fs.mkdirSync('/home/node/dist', { recursive: true });
    fs.copyFileSync(coinsPath, staticCoinsPath);
  } catch (e) {
    console.error(`Error copying coins file: ${e}`);
  }
} else {
    console.log(`Coins file not found at ${coinsPath}.`);
}

let connectedClient = null;
const requestPromises = new Map();

// 1. Start Vite server as a child process
const viteServer = exec('npx vite preview --host');
viteServer.stdout.on('data', (data) => console.log(`[Vite]: ${data}`));
viteServer.stderr.on('data', (data) => console.error(`[Vite]: ${data}`));

// 2. Start WebSocket server
const wss = new WebSocket.Server({ port: 7777 });
console.log('WebSocket server started on port 7777');

wss.on('connection', (ws) => {
    console.log('Puppeteer page connected to WebSocket');
    connectedClient = ws;

    ws.on('message', (message) => {
        console.log('Received message from WASM client:', message.toString());
        const { id, result, error } = JSON.parse(message.toString());
        if (requestPromises.has(id)) {
            const { resolve, reject } = requestPromises.get(id);
            if (error) {
                reject(error);
            } else {
                resolve(result);
            }
            requestPromises.delete(id);
        }
    });

    ws.on('close', () => {
        console.log('Puppeteer page disconnected');
        connectedClient = null;
    });
});

// 3. Start HTTP RPC server
const rpcServer = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            console.log('--- New RPC Request ---');
            console.log('Received raw request body:', body);

            if (!connectedClient) {
                console.error('Error: WASM client not connected.');
                res.writeHead(503, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'WASM client not connected' }));
                return;
            }

            const id = Math.random().toString(36).substring(2);
            let command;
            try {
                command = JSON.parse(body);
                console.log('Parsed command:', JSON.stringify(command, null, 2));
            } catch (parseError) {
                console.error('Error parsing request body:', parseError);
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid JSON in request body' }));
                return;
            }

            try {
                const result = await new Promise((resolve, reject) => {
                    requestPromises.set(id, { resolve, reject });
                    // The browser-side script (utils/docker/wasm_runner/script.js) expects
                    // each payload to have the shape `{ id, command }`, where `command`
                    // is the parsed RPC request object and `id` is a unique identifier.
                    // Sending the previous `{ message, uuid }` shape caused the script to
                    // treat the payload as `undefined` which in turn resulted in
                    // `mm2_rpc` throwing a `SyntaxError: "[object Object]" is not valid JSON`.
                    // Aligning the structures fixes the contract mismatch.
                    if (command.params && Object.keys(command.params).length === 0) {
                        delete command.params;
                    }
                    const message = JSON.stringify({ id, command });
                    console.log('Sending payload to WASM client:', JSON.stringify(message, null, 2));
                    connectedClient.send(message);
                    setTimeout(() => {
                        if (requestPromises.has(id)) {
                            const error = new Error('Request timed out');
                            console.error('Request timeout for id:', id);
                            reject(error);
                            requestPromises.delete(id);
                        }
                    }, 15000); // 15-second timeout to accommodate heavier requests
                });
                console.log('xx Received raw result from WASM client:', result);
                console.log('xx Received json result from WASM client:', JSON.stringify(result, null, 2));
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
                console.log('--- RPC Request Finished ---');
            } catch (e) {
                console.error('--- Error in RPC Request ---');
                console.error('Caught error object:', e);
                console.error('Caught error object (stringified):', JSON.stringify(e, null, 2));
                res.writeHead(500, { 'Content-Type': 'application/json' });
                const errorMessage = (typeof e === 'object' && e !== null && e.message) ? e.message : (typeof e === 'object' ? JSON.stringify(e) : e.toString());
                console.error('Responding with error message:', errorMessage);
                res.end(JSON.stringify({ error: errorMessage }));
                console.error('--- RPC Request Finished with Error ---');
            }
        });
    } else {
        res.writeHead(404);
        res.end();
    }
});
rpcServer.listen(8780, () => {
    console.log('HTTP RPC server listening on port 8780');
});


// 4. Launch Puppeteer
(async () => {
    console.log('Starting browser');
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        headless: true
    });
    const page = await browser.newPage();
    console.log('Chrome Page created');

    // Pipe browser console logs to Node's console
    page.on('console', msg => console.log(`[Browser]: ${msg.text()}`));
    
    await checkIfWebServerIsRunning(async () => {
      let url = 'http://127.0.0.1:3000';
      await page.goto(url);
      console.log(`KDF Page loaded successfully`);
    });
})();

async function checkIfWebServerIsRunning(cb) {
  const maxRetries = 50;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // Check if the endpoint is active
      await new Promise((resolve, reject) => {
        const req = http.get(`http://127.0.0.1:3000`, (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            reject(new Error(`Web server responded with status code ${res.statusCode}`));
          }
        });

        req.on('error', reject);
        req.end();
      });

      // If the check passes, callback
      await cb();
      break; // Exit the loop if successful
    } catch (error) {
      console.error(`Checking web server status: attempt ${attempt} failed: ${error.message}`);
      if (attempt === maxRetries) {
        console.error("Max retries reached. Web server didn't start.");
        process.exit(1);
      } else {
        console.log(`Retrying in ${retryDelay / 1000} seconds...`);
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
      }
    }
  }
} 