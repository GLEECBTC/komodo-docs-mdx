"""Common helper utilities for KDF RPC integration tests.

This module centralises logic for:
* Starting/stopping the docker-compose KDF container.
* Performing health-checks (version + get_enabled_coins).
* Capturing the node context before tests and writing it to a JSON report.

All individual test scripts should import and use ``KDFTestHelper`` instead
of duplicating this logic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# ------------------------------------------------------------------
# Ensure workspace root in sys.path so that `import utils.*` works when
# tests are executed from nested directories.
# ------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import requests

# Now that path is set, import project modules
from lib.api_client.kdf_api_processor import ApiRequestProcessor
from constants.config import get_config
from lib.utils.logging_utils import set_config_provider, get_logger

# Ensure logger uses config provider
set_config_provider(get_config)

__all__ = ["KDFTestHelper"]


class KDFTestHelper:
    """Utility wrapper around KDF docker-compose and RPC calls."""

    DEFAULT_RPC_PORT = "8778"
    DEFAULT_RPC_PASSWORD = "RPC_UserP@SSW0RD"
    RPC_URL_TEMPLATE = "http://127.0.0.1:{port}"

    def __init__(
        self,
        *,
        rpc_port: str | int | None = None,
        rpc_password: str | None = None,
        compose_dir: Path | None = None,
    ) -> None:
        self.rpc_port: str = str(rpc_port or os.getenv("RPC_PORT", self.DEFAULT_RPC_PORT))
        self.rpc_password: str = rpc_password or os.getenv("RPC_PASSWORD", self.DEFAULT_RPC_PASSWORD)
        self.rpc_url: str = self.RPC_URL_TEMPLATE.format(port=self.rpc_port)

        # utils/docker is three levels up from this file: tests -> py -> utils
        self.compose_dir: Path = compose_dir or Path(__file__).resolve().parents[3] / "utils" / "docker"

        self._env: Dict[str, str] = {
            **os.environ,
            "RPC_PORT": self.rpc_port,
            "RPC_PASSWORD": self.rpc_password,
        }

        # Initialize ApiRequestProcessor for unified request handling
        self.logger = get_logger("tests")
        try:
            self.api_processor = ApiRequestProcessor(config=get_config(), logger=self.logger)
            # Load method sets from processor to decide version
            self.v1_methods = self.api_processor.v1_methods
            self.v2_methods = self.api_processor.v2_methods
        except Exception as exc:
            # Fallback: create empty sets if initialization fails (e.g., missing deps)
            print("Warning: ApiRequestProcessor initialization failed:", exc)
            self.api_processor = None
            self.v1_methods = set()
            self.v2_methods = set()

    # ---------------------------------------------------------------------
    # Docker helpers
    # ---------------------------------------------------------------------

    def docker_compose(self, args: List[str]) -> None:
        """Run ``docker compose <args>`` inside *compose_dir* with env vars set."""
        cmd = ["docker", "compose", *args]
        subprocess.run(cmd, cwd=self.compose_dir, check=True, env=self._env)

    # ---------------------------------------------------------------------
    # RPC helpers
    # ---------------------------------------------------------------------

    def _rpc_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        if self.api_processor:
            return self.api_processor._make_request(body)
        resp = requests.post(self.rpc_url, json=body, timeout=10)
        try:
            return resp.json()
        except ValueError:
            resp.raise_for_status()
            raise

    def call_v2(self, method: str, params: Dict[str, Any] | None = None, *, id: int = 0) -> Dict[str, Any]:
        """Call a *v2* RPC method."""
        body = {
            "mmrpc": "2.0",
            "userpass": self.rpc_password,
            "method": method,
            "id": id,
        }
        if params:
            body["params"] = params
        return self._rpc_request(body)

    def call_version(self) -> Dict[str, Any]:
        """Call the legacy ``version`` RPC (v1)."""
        body = {
            "method": "version",
            "userpass": self.rpc_password,
            # legacy call does not use ``mmrpc`` or ``params``
        }
        return self._rpc_request(body)

    # ------------------------------------------------------------------
    # Unified method caller that determines version
    # ------------------------------------------------------------------

    def send_method(self, method: str, params: Dict[str, Any] | None = None, *, id: int = 0) -> Dict[str, Any]:
        """Determine appropriate RPC protocol version and send the request."""
        # prefer v2 if available
        if method in self.v2_methods or (method not in self.v1_methods):
            return self.call_v2(method, params, id=id)
        else:
            # legacy v1 – merge params into root as per classic API
            body = {
                "method": method,
                "userpass": self.rpc_password,
                **({"id": id} if id is not None else {}),
            }
            if params:
                body.update(params)
            return self._rpc_request(body)

    # ---------------------------------------------------------------------
    # Health-check & context capture
    # ---------------------------------------------------------------------

    def ensure_container(self, retries: int = 3, wait_seconds: int = 5) -> None:
        """Ensure docker container is up and RPC responds.

        Tries *retries* times, (re)starting the compose stack when needed.
        Raises ``SystemExit`` on repeated failure.
        """
        for _ in range(retries):
            try:
                # Simply verifying we get any JSON response without connection error.
                _ = self.call_v2("get_enabled_coins")
                return  # If call didn't raise, node is reachable
            except Exception as exc:
                print("Health-check exception:", exc)

            print("Container not responding – starting…")
            self.docker_compose(["up", "-d"])
            time.sleep(wait_seconds)

        # After retries, fetch logs and abort
        try:
            logs = subprocess.run(
                ["docker", "logs", "docker-kdf-1", "--tail", "50"],
                capture_output=True,
                text=True,
            )
            print("Last container log lines:\n", logs.stdout)
        except Exception as exc:
            print("Could not fetch docker logs:", exc)
        raise SystemExit("Container failed to start or respond after retries")

    def capture_context(self, report_path: Path | None = None) -> Dict[str, Any]:
        """Capture node *version* (v1) and *enabled coins* (v2) and optionally write to *report_path*."""
        version_info = self.call_version().get("result", {})
        coins_info = self.call_v2("get_enabled_coins").get("result", {})

        context = {
            "version": version_info,
            "enabled_coins": coins_info,
        }

        if report_path is None:
            report_path = Path(__file__).resolve().parents[3] / "reports" / "dev" / "test_node_context.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(context, indent=2))
        print(f"Saved node context to {report_path}")
        return context

    # ---------------------------------------------------------------------
    # Convenience helpers for tests
    # ---------------------------------------------------------------------

    def ensure_node_ready(self) -> None:
        """Ensure container is running and node context captured.

        Most integration tests require the node to be up before executing RPCs.
        This helper wraps ``ensure_container`` and ``capture_context`` so tests
        can prepare the environment with a single call.
        """
        # Proactively start the stack; if it's already running `docker compose up` is a no-op.
        try:
            self.docker_compose(["up", "-d"])
        except Exception as exc:
            print("docker compose up failed (it may already be running):", exc)

        # Wait until RPC responds.
        self.ensure_container(retries=6, wait_seconds=5)
        # Store context for debugging/reporting; ignore return value.
        self.capture_context() 