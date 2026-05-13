# Deprecated Commands

## init_threadline_settings

**Status**: Deprecated as of 2026-05-09  
**Removal planned**: Future version (TBD)

### Reason for Deprecation

This command was used to initialize threadline settings from YAML configuration files. With the introduction of the Relay module, delivery channel configuration is now managed through:

1. **Relay API** - RESTful API for managing delivery subscriptions
2. **Django Admin** - Web interface for configuration management
3. **Automatic Migration** - Legacy settings are automatically migrated to Relay on startup

### Migration Guide

**Old approach (deprecated):**
```bash
python manage.py init_threadline_settings --user admin
```

**New approach:**

1. **Via Relay API:**
   ```bash
   # Create a delivery subscription
   curl -X POST http://localhost:8000/api/relay/subscriptions/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "name": "My Jira Channel",
       "target_type": "jira",
       "enabled": true,
       "config": {...}
     }'
   ```

2. **Via Django Admin:**
   - Navigate to `/admin/relay/relaysubscription/`
   - Click "Add Relay Subscription"
   - Configure your delivery channel

3. **Automatic Migration:**
   - Existing `issue_config` settings are automatically migrated to Relay subscriptions on Celery worker startup
   - No manual action required for existing users

### What This Command Did

- Loaded YAML configuration from `devify/conf/threadline/issues/`
- Created `Settings` records for:
  - `email_config` - Email collection settings
  - `issue_config` - Issue delivery settings
  - `prompt_config` - AI prompt templates

### Why It's No Longer Needed

- **Relay Module**: Issue delivery is now handled by the dedicated Relay module
- **Better UX**: API and Admin interface provide better user experience than YAML files
- **Separation of Concerns**: Configuration management is separated from initialization
- **Dynamic Updates**: Settings can be updated without restarting services

### For Developers

If you need to maintain backward compatibility in tests:
- The command still works but shows a deprecation warning
- Tests using this command should be updated to use Relay API
- See `relay/tests/` for examples of the new approach
