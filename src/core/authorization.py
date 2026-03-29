"""
Authorization module for GMNAP V7
Implements Role-Based Access Control (RBAC)
"""

import logging
from enum import Enum
from functools import wraps
from typing import Dict, List, Set


class Permission(Enum):
    """Available permissions in the system"""

    # Read permissions
    READ_ENTRIES = "read_entries"
    READ_REPORTS = "read_reports"
    READ_METRICS = "read_metrics"

    # Write permissions
    WRITE_ENTRIES = "write_entries"
    WRITE_REPORTS = "write_reports"
    UPDATE_ENTRIES = "update_entries"

    # Delete permissions
    DELETE_ENTRIES = "delete_entries"
    DELETE_REPORTS = "delete_reports"

    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_PERMISSIONS = "manage_permissions"
    SYSTEM_CONFIG = "system_config"

    # Authority permissions
    QUERY_AUTHORITIES = "query_authorities"
    MANAGE_QUOTAS = "manage_quotas"

    # Pipeline permissions
    RUN_PIPELINE = "run_pipeline"
    CONFIGURE_PIPELINE = "configure_pipeline"


class Role(Enum):
    """System roles"""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    API_USER = "api_user"


class AuthorizationManager:
    """Manages role-based access control"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Define role permissions
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.ADMIN: {
                # Admin has all permissions
                Permission.READ_ENTRIES,
                Permission.READ_REPORTS,
                Permission.READ_METRICS,
                Permission.WRITE_ENTRIES,
                Permission.WRITE_REPORTS,
                Permission.UPDATE_ENTRIES,
                Permission.DELETE_ENTRIES,
                Permission.DELETE_REPORTS,
                Permission.MANAGE_USERS,
                Permission.MANAGE_ROLES,
                Permission.MANAGE_PERMISSIONS,
                Permission.SYSTEM_CONFIG,
                Permission.QUERY_AUTHORITIES,
                Permission.MANAGE_QUOTAS,
                Permission.RUN_PIPELINE,
                Permission.CONFIGURE_PIPELINE,
            },
            Role.EDITOR: {
                # Editor can read, write, update
                Permission.READ_ENTRIES,
                Permission.READ_REPORTS,
                Permission.READ_METRICS,
                Permission.WRITE_ENTRIES,
                Permission.WRITE_REPORTS,
                Permission.UPDATE_ENTRIES,
                Permission.QUERY_AUTHORITIES,
                Permission.RUN_PIPELINE,
            },
            Role.RESEARCHER: {
                # Researcher can read and query
                Permission.READ_ENTRIES,
                Permission.READ_REPORTS,
                Permission.READ_METRICS,
                Permission.QUERY_AUTHORITIES,
                Permission.RUN_PIPELINE,
            },
            Role.VIEWER: {
                # Viewer can only read
                Permission.READ_ENTRIES,
                Permission.READ_REPORTS,
                Permission.READ_METRICS,
            },
            Role.API_USER: {
                # API user has limited access
                Permission.READ_ENTRIES,
                Permission.QUERY_AUTHORITIES,
            },
        }

        # Resource-based permissions (optional fine-grained control)
        self.resource_permissions: Dict[str, Dict[str, List[Permission]]] = {}

    def check_permission(self, user_role: str, permission: Permission) -> bool:
        """
        Check if a role has a specific permission

        Args:
            user_role: User's role name
            permission: Permission to check

        Returns:
            True if role has permission
        """
        try:
            role = Role(user_role)
            role_perms = self.role_permissions.get(role, set())
            return permission in role_perms
        except ValueError:
            self.logger.warning(f"Invalid role: {user_role}")
            return False

    def check_multiple_permissions(
        self, user_role: str, permissions: List[Permission], require_all: bool = True
    ) -> bool:
        """
        Check multiple permissions at once

        Args:
            user_role: User's role name
            permissions: List of permissions to check
            require_all: If True, all permissions required. If False, any permission sufficient.

        Returns:
            True if permission check passes
        """
        if require_all:
            return all(self.check_permission(user_role, perm) for perm in permissions)
        else:
            return any(self.check_permission(user_role, perm) for perm in permissions)

    def get_role_permissions(self, user_role: str) -> Set[Permission]:
        """
        Get all permissions for a role

        Args:
            user_role: User's role name

        Returns:
            Set of permissions
        """
        try:
            role = Role(user_role)
            return self.role_permissions.get(role, set())
        except ValueError:
            return set()

    def add_resource_permission(
        self, resource_id: str, user_id: str, permissions: List[Permission]
    ) -> None:
        """
        Grant specific permissions on a resource to a user

        Args:
            resource_id: Resource identifier
            user_id: User identifier
            permissions: List of permissions to grant
        """
        if resource_id not in self.resource_permissions:
            self.resource_permissions[resource_id] = {}

        if user_id not in self.resource_permissions[resource_id]:
            self.resource_permissions[resource_id][user_id] = []

        self.resource_permissions[resource_id][user_id].extend(permissions)

    def check_resource_permission(
        self, resource_id: str, user_id: str, permission: Permission
    ) -> bool:
        """
        Check if user has permission on specific resource

        Args:
            resource_id: Resource identifier
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission on resource
        """
        if resource_id in self.resource_permissions:
            user_perms = self.resource_permissions[resource_id].get(user_id, [])
            return permission in user_perms
        return False

    def remove_resource_permissions(
        self, resource_id: str, user_id: str = None
    ) -> None:
        """
        Remove resource permissions

        Args:
            resource_id: Resource identifier
            user_id: User identifier (if None, remove all permissions for resource)
        """
        if resource_id in self.resource_permissions:
            if user_id:
                self.resource_permissions[resource_id].pop(user_id, None)
            else:
                del self.resource_permissions[resource_id]


def require_permission(permission: Permission):
    """
    Decorator to check permissions before executing a function

    Args:
        permission: Required permission

    Usage:
        @require_permission(Permission.WRITE_ENTRIES)
        async def create_entry(user, entry_data):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from arguments
            # For methods, skip 'self' (args[0]) and get user from args[1] or kwargs
            user = None
            if "user" in kwargs:
                user = kwargs["user"]
            elif len(args) > 0:
                # Check if this is a method (first arg might be self)
                if hasattr(args[0], "__class__") and hasattr(
                    args[0].__class__, func.__name__
                ):
                    # This is a method, user should be second argument
                    user = args[1] if len(args) > 1 else None
                else:
                    # This is a function, user should be first argument
                    user = args[0]

            if not user or not hasattr(user, "role"):
                raise PermissionError("No authenticated user")

            auth_mgr = AuthorizationManager()
            if not auth_mgr.check_permission(user.role, permission):
                raise PermissionError(f"User lacks permission: {permission.value}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator to check if user has any of the specified permissions

    Args:
        permissions: List of permissions (any one required)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from arguments (same logic as require_permission)
            user = None
            if "user" in kwargs:
                user = kwargs["user"]
            elif len(args) > 0:
                # Check if this is a method (first arg might be self)
                if hasattr(args[0], "__class__") and hasattr(
                    args[0].__class__, func.__name__
                ):
                    # This is a method, user should be second argument
                    user = args[1] if len(args) > 1 else None
                else:
                    # This is a function, user should be first argument
                    user = args[0]

            if not user or not hasattr(user, "role"):
                raise PermissionError("No authenticated user")

            auth_mgr = AuthorizationManager()
            if not auth_mgr.check_multiple_permissions(
                user.role, list(permissions), require_all=False
            ):
                perm_names = [p.value for p in permissions]
                raise PermissionError(f"User lacks any of permissions: {perm_names}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class User:
    """Simple user class for authorization"""

    def __init__(self, user_id: str, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a permission"""
        auth_mgr = AuthorizationManager()
        return auth_mgr.check_permission(self.role, permission)

    def get_permissions(self) -> Set[Permission]:
        """Get all user permissions"""
        auth_mgr = AuthorizationManager()
        return auth_mgr.get_role_permissions(self.role)
