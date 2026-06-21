import logging
import multiprocessing
import queue
import time
from typing import Any

logger = logging.getLogger("PluginSandbox")

class SandboxExecutionError(Exception):
    pass

class SandboxTimeoutError(SandboxExecutionError):
    pass

class SandboxSecurityError(SandboxExecutionError):
    pass

def _restricted_execution_worker(plugin_code: str, context: dict[str, Any], result_queue: multiprocessing.Queue):
    """
    The actual worker process that runs the untrusted plugin code.
    Runs in a completely separate OS process for memory and fault isolation.
    """
    # Define a highly restricted global environment
    safe_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "type": type,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
        },
        "context": context
    }

    # Safe locals dictionary for the execution
    safe_locals: dict[str, Any] = {}

    try:
        # Pre-execution AST verification could go here
        if "import os" in plugin_code or "import sys" in plugin_code or "__import__" in plugin_code:
            raise SandboxSecurityError("Unauthorized import detected in plugin code.")

        # Execute the code
        exec(plugin_code, safe_globals, safe_locals)

        # Check if the plugin defined a specific entrypoint
        if "run_plugin" in safe_locals and callable(safe_locals["run_plugin"]):
            result = safe_locals["run_plugin"](context)
            result_queue.put({"status": "success", "result": result})
        else:
            # Otherwise return the entire modified local state
            # Filter out functions to only return data
            data_out = {k: v for k, v in safe_locals.items() if not callable(v)}
            result_queue.put({"status": "success", "result": data_out})

    except Exception as e:
        result_queue.put({"status": "error", "message": str(e), "type": type(e).__name__})


class PluginSandbox:
    """
    A secure execution environment for user-provided plugins.
    Uses Process-based isolation to prevent memory leaks, infinite loops, and unauthorized I/O.
    """
    def __init__(self, timeout_seconds: float = 2.0, max_memory_mb: int = 50):
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb

    def execute(self, plugin_code: str, context: dict[str, Any] | None = None) -> Any:
        context = context or {}

        logger.info(f"Starting sandboxed execution (timeout={self.timeout_seconds}s)")

        result_queue: multiprocessing.Queue[Any] = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_restricted_execution_worker,
            args=(plugin_code, context, result_queue)
        )

        start_time = time.time()
        process.start()

        try:
            # Block and wait for result with timeout
            response = result_queue.get(timeout=self.timeout_seconds)

            # Ensure process cleans up
            process.join(timeout=0.1)

            if response["status"] == "success":
                logger.debug(f"Sandbox execution successful in {time.time() - start_time:.3f}s")
                return response["result"]
            else:
                raise SandboxExecutionError(f"{response['type']}: {response['message']}")

        except queue.Empty:
            logger.error("Sandbox execution timed out. Terminating process.")
            process.terminate()
            process.join()
            raise SandboxTimeoutError(f"Plugin execution exceeded maximum allowed time of {self.timeout_seconds}s")

        finally:
            if process.is_alive():
                process.terminate()
                process.join()
