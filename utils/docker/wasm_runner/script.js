import init, * as kdflib from '/kdf/kdflib.js';

async function main() {
    console.log("Initializing WASM...");
    await init('/kdf/kdflib_bg.wasm');
    console.log("WASM Initialized.");

    const ws = new WebSocket('ws://127.0.0.1:7777');

    ws.onopen = () => {
        console.log('Connected to WebSocket server');
    };

    ws.onmessage = async (event) => {
        const { id, command } = JSON.parse(event.data);
        console.log(`[${id}] Received command:`, command);

        try {
            console.log(`[${id}] Calling kdflib.mm2_rpc...`);
            const rawResult = await kdflib.mm2_rpc(command);
            console.log(`[${id}] Received raw result (type: ${typeof rawResult}):`, rawResult);

            let parsedResult;
            if (typeof rawResult === 'string') {
                try {
                    parsedResult = JSON.parse(rawResult);
                } catch (e) {
                    console.warn(`[${id}] Could not JSON.parse raw result, forwarding as-is.`);
                    parsedResult = rawResult;
                }
            } else {
                parsedResult = rawResult; // already an object
            }

            ws.send(JSON.stringify({ id, result: parsedResult }));
            console.log(`[${id}] Sent parsed result back to server.`);
        } catch (e) {
            console.error(`[${id}] Caught error from kdflib.mm2_rpc:`, e);
            const errorMessage = e.toString();
            ws.send(JSON.stringify({ id, error: errorMessage }));
            console.log(`[${id}] Sent error back to server.`);
        }
    };

    ws.onclose = () => {
        console.log('Disconnected from WebSocket server');
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    // By default, KDF will look for a coins file.
    // The "coins" array in the config can override this.
    let mm2_config = {
        "gui": "kdf_mdx_docs",
        "rpcip": "0.0.0.0",
        "rpc_local_only": false,
        "enable_hd": true,
        "netid": 8762,
        "rpcport": 8780,
        "seednodes": ["seed01.kmdefi.net", "seed02.kmdefi.net"],
        "passphrase": "movie near museum glare gossip clerk adapt chair inch child erupt verify",
        "userpass": "RPC_UserP@SSW0RD",
        "rpc_password": "RPC_UserP@SSW0RD"
    };

    // Allow overriding the config via URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const mm2ConfParam = urlParams.get('mm2_conf');
    if (mm2ConfParam) {
        try {
            mm2_config = JSON.parse(atob(mm2ConfParam));
            console.log("Loaded MM2 config from URL parameter.");
        } catch (e) {
            console.error("Error parsing mm2_conf from URL:", e);
        }
    }

    try {
        console.log("Fetching coins file...");
        const response = await fetch('/coins.json');
        if (response.ok) {
            const coins = await response.json();
            mm2_config.coins = coins;
            console.log("Successfully loaded and merged coins file.");
        } else {
            console.log(`Could not load coins.json (status: ${response.status}), proceeding without it.`);
        }
    } catch (e) {
        console.error("Error fetching or parsing coins.json:", e);
    }

    function log_handler(level, line) {
        console.log(`[${level}] ${line}`);
    }

    try {
        const params = {
            conf: mm2_config,
            log_level: kdflib.LogLevel.Info,
        };
        kdflib.mm2_main(params, log_handler);
        console.log("mm2_main started");
    } catch (e) {
        console.error("Error starting mm2_main:", e);
    }
}

main().catch(console.error); 