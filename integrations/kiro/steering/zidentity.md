# ZIdentity Steering

## Overview

ZIdentity is Zscaler's centralized identity management platform. It provides user and group management across all Zscaler services, and is the source of truth for identity data used in ZPA access policies, ZIA user-based rules, and ZDX user correlation.

## Key Concepts

- **Users**: Identity records for individuals. Includes profile data, email, status, and group memberships.
- **Groups**: Logical groupings of users for policy assignment across ZPA and ZIA.
- **User-Group Relationships**: Users belong to groups; groups are referenced in access policies and filtering rules.

## Common Workflows

### User Lookup
```
1. zidentity_search_users      → Search for a user by name, email, or other attributes
2. zidentity_get_user           → Get full user profile by ID
3. zidentity_get_user_groups    → Get groups the user belongs to (by user ID)
4. zidentity_get_user_groups_by_name → Get groups for a user by username
```

### Group Management
```
1. zidentity_list_groups        → List all groups
2. zidentity_search_groups      → Search groups by name or attribute
3. zidentity_get_group          → Get group details by ID
4. zidentity_get_group_users    → List users in a group (by group ID)
5. zidentity_get_group_users_by_name → List users in a group (by group name)
```

### User Inventory
```
1. zidentity_list_users         → List all users (paginated)
2. For each user of interest:
   a. zidentity_get_user        → Get full profile
   b. zidentity_get_user_groups → Get group memberships
```

### Cross-Service Identity Correlation
```
1. zidentity_search_users  → Find the user
2. zidentity_get_user_groups → Get their groups
3. Then correlate with:
   - ZPA: zpa_list_access_policy_rules → Which policies match this user/group?
   - ZIA: zia_list_url_filtering_rules → Which URL rules apply to this user/group?
   - ZDX: zdx_list_devices → Find the user's device for experience data
```

## Available Tools

| Tool | Description |
|------|-------------|
| `zidentity_list_users` | List all users (paginated) |
| `zidentity_get_user` | Get specific user by ID |
| `zidentity_search_users` | Search users by name, email, or attributes |
| `zidentity_get_user_groups` | Get groups for a user (by user ID) |
| `zidentity_get_user_groups_by_name` | Get groups for a user (by username) |
| `zidentity_list_groups` | List all groups (paginated) |
| `zidentity_get_group` | Get specific group by ID |
| `zidentity_search_groups` | Search groups by name or attributes |
| `zidentity_get_group_users` | List users in a group (by group ID) |
| `zidentity_get_group_users_by_name` | List users in a group (by group name) |

All ZIdentity tools are **read-only**.

## Best Practices

1. **Use search for large directories** — `zidentity_search_users` and `zidentity_search_groups` are more efficient than listing all records
2. **Verify group membership for access issues** — When a user can't access an app, check their group memberships against ZPA access policy conditions
3. **Correlate across services** — ZIdentity users/groups are referenced in ZPA policies and ZIA rules. Use identity data to trace why a user has or lacks access.
4. **Check both directions** — Use `zidentity_get_user_groups` to see a user's groups, and `zidentity_get_group_users` to see who's in a specific group
