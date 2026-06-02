import os
import re
from typing import List, Optional

import bashlex

from app.core.config import settings

class SecurityAlertError(Exception):
    """Custom exception jab koi malicious pattern detect ho"""
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}

class ASTSafetyFilter:
    def __init__(self):
        self.blocked_commands: set[str] = {"rm", "mkfs", "dd", "chmod", "chown"}
        self.dangerous_flags: set[str] = {"-rf", "-r", "-f"}

    def _normalize_word(self, node) -> str:
        """Quotes aur Backslashes ko remove karke command normalise karta hai"""
        if not hasattr(node, 'word'):
            return ""
        raw_word = node.word
        return raw_word.replace("'", "").replace('"', "").replace("\\", "")

    def _check_command_node(self, node):
        """Individual command node ko validate karta hai"""
        cmd_parts = []
        for part in node.parts:
            if part.kind == 'word':
                cmd_parts.append(self._normalize_word(part))
        
        if not cmd_parts:
            return

        root_cmd = cmd_parts[0]
        args = cmd_parts[1:]

        # Check blocked binaries
        if root_cmd in self.blocked_commands:
            if root_cmd == "rm":
                has_danger_flag = any(flag in args for flag in self.dangerous_flags)
                has_root_target = any("/" in arg for arg in args)
                
                if has_danger_flag or has_root_target:
                    raise SecurityAlertError(
                        message=f"Critical Security Violation: Blocked command root '{root_cmd}' with dangerous arguments.",
                        payload={"command": root_cmd, "args": args, "status": "blocked"}
                    )

    def _traverse_nodes(self, node):
        """Recursive traversal jo tree ke har kone se nodes nikalta hai"""
        if node.kind == 'command':
            self._check_command_node(node)

        if hasattr(node, 'parts'):
            for child in node.parts:
                self._traverse_nodes(child)

    def analyze_script(self, script_content: str) -> bool:
        """
        Main function jise baki services call karengi.
        Returns True agar safe hai, raise SecurityAlertException agar dangerous hai.
        """
        try:
            trees = bashlex.parse(script_content)
        except Exception as e:
            raise SecurityAlertError(
                message="Unparseable or heavily obfuscated script structure detected.",
                payload={"error": str(e), "status": "blocked"}
            )

        for tree in trees:
            self._traverse_nodes(tree)
            
        return True
