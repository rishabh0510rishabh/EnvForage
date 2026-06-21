import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("ABAC")

class Action(str):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"

@dataclass
class Subject:
    id: str
    roles: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass
class Resource:
    type: str
    id: str
    attributes: dict[str, Any] = field(default_factory=dict)

class PolicyCondition(BaseModel):
    attribute: str
    operator: str # eq, neq, gt, lt, in, contains
    value: Any

class ABACPolicy(BaseModel):
    id: str
    description: str
    effect: str # allow or deny
    subjects: list[str] # role names or '*'
    actions: list[str] # Action strings or '*'
    resources: list[str] # Resource types or '*'
    conditions: list[PolicyCondition] = []

class ABACEvaluator:
    """
    Evaluates Attribute-Based Access Control policies.
    Provides highly granular security checks beyond simple RBAC.
    """
    def __init__(self, policies: list[ABACPolicy]):
        self.policies = policies

    def _evaluate_condition(self, condition: PolicyCondition, subject: Subject, resource: Resource) -> bool:
        # Resolve attribute path (e.g. "subject.department" or "resource.owner_id")
        attr_val = None
        if condition.attribute.startswith("subject."):
            key = condition.attribute.replace("subject.", "")
            attr_val = subject.attributes.get(key)
        elif condition.attribute.startswith("resource."):
            key = condition.attribute.replace("resource.", "")
            attr_val = resource.attributes.get(key)

        if attr_val is None:
            return False

        # Evaluate operator
        op = condition.operator
        val = condition.value

        try:
            if op == "eq": return attr_val == val
            if op == "neq": return attr_val != val
            if op == "gt": return attr_val > val
            if op == "lt": return attr_val < val
            if op == "in": return attr_val in val
            if op == "contains": return val in attr_val
        except TypeError:
            return False

        return False

    def is_allowed(self, subject: Subject, action: str, resource: Resource) -> bool:
        allowed = False

        for policy in self.policies:
            # Check subject match
            subj_match = "*" in policy.subjects or any(r in policy.subjects for r in subject.roles)
            if not subj_match: continue

            # Check action match
            act_match = "*" in policy.actions or action in policy.actions
            if not act_match: continue

            # Check resource match
            res_match = "*" in policy.resources or resource.type in policy.resources
            if not res_match: continue

            # Check conditions
            cond_match = all(self._evaluate_condition(c, subject, resource) for c in policy.conditions)
            if not cond_match: continue

            # Policy matches!
            if policy.effect == "deny":
                logger.warning(f"ABAC Deny: {subject.id} attempted {action} on {resource.type}/{resource.id} (Policy {policy.id})")
                return False # Explicit deny immediately overrides any allows

            if policy.effect == "allow":
                allowed = True

        if allowed:
            logger.debug(f"ABAC Allow: {subject.id} -> {action} -> {resource.type}/{resource.id}")
        else:
            logger.warning(f"ABAC Default Deny: {subject.id} -> {action} -> {resource.type}/{resource.id}")

        return allowed

# Default organizational policy registry
GLOBAL_POLICIES = [
    ABACPolicy(
        id="admin-full-access",
        description="Administrators have full access to everything",
        effect="allow",
        subjects=["admin"],
        actions=["*"],
        resources=["*"]
    ),
    ABACPolicy(
        id="user-read-profiles",
        description="Standard users can read public profiles",
        effect="allow",
        subjects=["user"],
        actions=["read"],
        resources=["profile"],
        conditions=[
            PolicyCondition(attribute="resource.is_public", operator="eq", value=True)
        ]
    ),
    ABACPolicy(
        id="user-own-scripts",
        description="Users can execute and modify their own scripts",
        effect="allow",
        subjects=["user"],
        actions=["read", "write", "execute"],
        resources=["script"],
        conditions=[
            PolicyCondition(attribute="resource.owner_id", operator="eq", value="subject.id")
        ]
    )
]

def get_evaluator() -> ABACEvaluator:
    return ABACEvaluator(GLOBAL_POLICIES)
