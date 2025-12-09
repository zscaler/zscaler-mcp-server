# ZIdentity Steering

## Overview

ZIdentity is Zscaler's identity management platform that provides centralized user and group management across Zscaler services.

## Key Concepts

- **Users**: Identity records for individuals accessing Zscaler services
- **Groups**: Logical groupings of users for policy assignment
- **API Clients**: OAuth credentials for programmatic access

## Common Workflows

### User Discovery
```
1. zidentity_get_users - List all users
2. zidentity_search - Search for specific users
```

### Group Management
```
1. zidentity_get_groups - List all groups
2. zidentity_search - Search for specific groups
```

## Available Tools

| Tool | Description | Type |
|------|-------------|------|
| `zidentity_get_users` | Get user information | Read |
| `zidentity_get_groups` | Get group information | Read |
| `zidentity_search` | Search across Zidentity resources | Read |

## Best Practices

1. **Use search for large directories** - More efficient than listing all users
2. **Correlate with ZPA policies** - Users/groups are referenced in access policies
3. **Verify group membership** - Important for understanding access rights

