"""AST-based safety filter for shell script validation."""

import os

import bashlex


class SecurityAlertError(Exception):
    """Raised when a malicious pattern is detected in a script."""

    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.payload = payload or {}


class ASTSafetyFilter:
    def __init__(self) -> None:
        self.blocked_commands: set[str] = {"rm", "mkfs", "dd", "chmod", "chown"}
        self.dangerous_flags: set[str] = {"-rf", "-r", "-f"}

    def _normalize_word(self, node) -> str:
        """Strip quotes and backslashes to normalise the command word."""
        if not hasattr(node, "word"):
            return ""
        return node.word.replace("'", "").replace('"', "").replace("\\", "")

    def _check_command_node(self, node) -> None:
        """Validate an individual command node."""
        cmd_parts = [
            self._normalize_word(part) for part in node.parts if part.kind == "word"
        ]

        if not cmd_parts:
            return

        root_cmd = cmd_parts[0]
        args = cmd_parts[1:]

        is_blocked_cmd = root_cmd in self.blocked_commands or any(
            root_cmd.startswith(cmd + ".") for cmd in self.blocked_commands
        )

        if not is_blocked_cmd:
            return

        has_danger_flag = False
        has_root_target = False

        for arg in args:
            if arg.startswith("-"):
                if arg in self.dangerous_flags:
                    has_danger_flag = True
                elif not arg.startswith("--"):
                    for char in arg[1:]:
                        if f"-{char}" in self.dangerous_flags:
                            has_danger_flag = True
            elif arg == "/" or os.path.normpath(arg) == "/":
                has_root_target = True

        if has_danger_flag or has_root_target:
            raise SecurityAlertError(
                message=f"Critical Security Violation: Blocked command '{root_cmd}' with dangerous arguments.",
                payload={"command": root_cmd, "args": args, "status": "blocked"},
            )

    def _traverse_nodes(self, node) -> None:
        """Recursively traverse all nodes in the parse tree."""
        if node.kind == "command":
            self._check_command_node(node)
        if hasattr(node, "parts"):
            for child in node.parts:
                self._traverse_nodes(child)

    def analyze_script(self, script_content: str) -> bool:
        """
        Analyze a shell script for dangerous patterns.

        Returns True if safe. Raises SecurityAlertError if dangerous.
        """
        try:
            trees = bashlex.parse(script_content)
        except Exception as exc:
            raise SecurityAlertError(
                message="Unparseable or heavily obfuscated script structure detected.",
                payload={"error": str(exc), "status": "blocked"},
            ) from exc

        for tree in trees:
            self._traverse_nodes(tree)

        return True
