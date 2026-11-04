"""Exercise native process interruption and restart with the installed interpreter.

On Windows, a hidden console controller broadcasts real console events to the
unmodified application and ignores those events itself. No production stop fixtures.
"""

import argparse
import json
import os
import platform
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path


def exercise(api=False, target_python=None):
    target_python = target_python or sys.executable
    environment = {k: v for k, v in os.environ.items() if not k.startswith("MOBIRAEON_")}
    checks = []
    with tempfile.TemporaryDirectory(prefix="mobiraeon-interruption-") as temporary:
        database = Path(temporary) / "native.db"
        base = [target_python, "-m", "mobiraeon", "--database", str(database)]
        if api:
            import socket

            from tls_fixture import certificate

            from mobiraeon.private_state import PrivateState

            outside = Path(temporary)
            private = outside / "private"
            database = private / "native.db"
            PrivateState(private, database).provision()
            cert, key = certificate(outside)
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            config = outside / "api.toml"
            config.write_text(f"""[database]
path = {json.dumps(str(database))}
[access]
private_dir = {json.dumps(str(private))}
[api]
enabled = true
port = {port}
cert_file = {json.dumps(str(cert))}
key_file = {json.dumps(str(key))}
""")
            base = [target_python, "-m", "mobiraeon", "--config", str(config)]
        initialized = subprocess.run(
            [*base, "initialize"],
            cwd=temporary,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert initialized.returncode == 0, initialized.stderr
        signals = (
            (signal.SIGINT, signal.SIGBREAK)
            if os.name == "nt"
            else (signal.SIGINT, signal.SIGTERM)
        )
        if os.name == "nt":
            # The controller shares the console, but only the application's own
            # signal handlers should stop its host. No handler is patched there.
            for signum in signals:
                signal.signal(signum, lambda *args: None)
        for signum in signals:
            process = subprocess.Popen(
                [*base, "start"],
                cwd=temporary,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                ready_queue = queue.Queue()
                threading.Thread(
                    target=lambda inbox=ready_queue, child=process: inbox.put(
                        child.stdout.readline()
                    ),
                    daemon=True,
                ).start()
                first_line = ready_queue.get(timeout=15)
                ready = json.loads(first_line)
                assert ready["phase"] == "ready" and ready["foundation_ready"]
                # Readiness is emitted immediately before the host installs handlers.
                time.sleep(0.2)
                if os.name == "nt":
                    import ctypes

                    event = 0 if signum == signal.SIGINT else 1
                    assert ctypes.windll.kernel32.GenerateConsoleCtrlEvent(event, 0)
                else:
                    process.send_signal(signum)
                try:
                    stdout, stderr = process.communicate(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=10)
                    checks.append(
                        {
                            "signal": signum.name,
                            "result": "shutdown_timeout",
                            "stdout": first_line + stdout,
                            "stderr": stderr,
                        }
                    )
                    return {"result": "failed", "checks": checks}
                terminal = json.loads(stdout)
                assert process.returncode == 0
                assert terminal["phase"] == "terminal" and terminal["outcome"] == "success"
                assert not terminal["foundation_ready"]
                assert terminal["invocation_id"] == ready["invocation_id"]
                assert [json.loads(line)["event"] for line in stderr.splitlines()] == [
                    "foundation_ready",
                    "stopped",
                ]
                restarted = subprocess.run(
                    [*base, "check"],
                    cwd=temporary,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                assert restarted.returncode == 0
                checks.append(
                    {
                        "signal": signum.name,
                        "command": [*base, "start"],
                        "exit_code": process.returncode,
                        "stdout": first_line + stdout,
                        "stderr": stderr,
                        "subsequent_check_exit_code": restarted.returncode,
                    }
                )
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
    return {"result": "passed", "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--api", action="store_true")
    parser.add_argument("--target-python", default=sys.executable)
    options = parser.parse_args()
    if os.name == "nt" and not options.controller:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        controller = {
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "parse_status": "not_attempted",
            "timeout_seconds": 90,
            "stdout_truncated": False,
            "stderr_truncated": False,
        }
        controller["command"] = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--controller",
            "--target-python",
            options.target_python,
            *(("--api",) if options.api else ()),
        ]

        def bounded(value, maximum=262144):
            if isinstance(value, bytes):
                value = value.decode(errors="replace")
            return (value or "")[:maximum]

        try:
            process = subprocess.run(
                controller["command"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=startup,
                capture_output=True,
                text=True,
                timeout=90,
            )
            controller.update(
                exit_code=process.returncode,
                stdout=bounded(process.stdout),
                stderr=bounded(process.stderr),
                stdout_truncated=len(process.stdout) > 262144,
                stderr_truncated=len(process.stderr) > 262144,
            )
            try:
                if controller["stdout_truncated"]:
                    raise ValueError
                parsed = json.loads(process.stdout)
            except ValueError:
                controller["parse_status"] = "invalid_or_oversized_json"
                report = {"result": "failed"}
            else:
                controller["parse_status"] = "parsed"
                controller["child_report"] = parsed
                valid = (
                    isinstance(parsed, dict)
                    and parsed.get("result") == "passed"
                    and isinstance(parsed.get("checks"), list)
                    and bool(parsed["checks"])
                    and all(isinstance(check, dict) for check in parsed["checks"])
                )
                controller["validation_status"] = (
                    "passing_report" if valid else "not_a_passing_report"
                )
                report = (
                    dict(parsed) if valid and process.returncode == 0 else {"result": "failed"}
                )
        except subprocess.TimeoutExpired as error:
            controller.update(
                timed_out=True,
                parse_status="timeout",
                stdout=bounded(error.stdout),
                stderr=bounded(error.stderr),
                stdout_truncated=len(bounded(error.stdout, 262145)) > 262144,
                stderr_truncated=len(bounded(error.stderr, 262145)) > 262144,
            )
            report = {"result": "failed"}
        except OSError as error:
            controller.update(
                parse_status="process_unavailable", failure_type=type(error).__name__
            )
            report = {"result": "failed"}
        report["controller"] = controller
    else:
        try:
            report = exercise(options.api, options.target_python)
        except Exception as error:
            report = {"result": "failed", "error_type": type(error).__name__}
    report.update(
        {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "host": "direct_tls_api" if options.api else "foundation",
        }
    )
    if options.output:
        options.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
