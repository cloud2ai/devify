# Configuration Migration Guide

## Issue Delivery Configuration Changes (2026-05-10)

### What Changed?

**Before:** Issue delivery channels (JIRA, Feishu Bitable) were configured via YAML files in `conf/threadline/issues/`

**After:** Issue delivery channels are now configured via **Relay API** or **Django Admin**

### Why the Change?

1. **Better User Experience**: Web UI and API are more user-friendly than editing YAML files
2. **Dynamic Updates**: Configuration changes take effect immediately without restarting services
3. **Multi-Channel Support**: Users can configure multiple delivery channels (e.g., multiple JIRA projects)
4. **Separation of Concerns**: Delivery logic is now in the dedicated Relay module
5. **Better Validation**: API validates configuration before saving

### Migration Path

#### Automatic Migration

**No action required for existing users!**

- Legacy configurations in the `Settings` table are automatically migrated to Relay subscriptions
- Migration happens on first Celery worker startup
- Your existing JIRA/Feishu configurations will continue to work

#### For New Configurations

**Option 1: Django Admin (Recommended for most users)**

1. Navigate to: `http://localhost:8000/admin/relay/relaysubscription/`
2. Click "Add Relay Subscription"
3. Fill in the form:
   - **Name**: Descriptive name (e.g., "Production JIRA")
   - **Target Type**: Select `jira` or `feishu_bitable`
   - **Enabled**: Check to activate
   - **Config**: JSON configuration (see examples below)
   - **Strategies**: Configure merge strategies
   - **Field Mappings**: Map workflow fields to target system fields

**Option 2: Relay API (For automation/scripts)**

```bash
curl -X POST http://localhost:8000/api/relay/subscriptions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @jira_subscription.json
```

### Configuration Examples

#### JIRA Subscription (JSON format)

```json
{
  "name": "Production JIRA",
  "target_type": "jira",
  "enabled": true,
  "config": {
    "issue_engine": "jira",
    "enable": true,
    "language": "Chinese",
    "jira": {
      "url": "https://jira.example.com/",
      "username": "your-username",
      "api_token": "your-api-token"
    },
    "fields": {
      "project_key_config": {
        "jira_field": "project",
        "default": "REQ"
      },
      "issue_type_config": {
        "jira_field": "issuetype",
        "default": "New Feature"
      },
      "priority_config": {
        "jira_field": "priority",
        "default": "High"
      },
      "summary_config": {
        "prefix": "[AI]",
        "add_timestamp": true
      },
      "description_config": {
        "jira_field": "description"
      },
      "assignee_config": {
        "use_llm": true,
        "jira_field": "assignee",
        "default": "default-user",
        "allow_values": ["user1", "user2", "user3"],
        "prompt": "Match assignee based on content"
      }
    }
  },
  "strategies": {
    "auto_merge_strategy": "new",
    "manual_merge_strategy": "linked",
    "retry_issue_strategy": "update"
  },
  "field_mappings": {}
}
```

#### Feishu Bitable Subscription (JSON format)

```json
{
  "name": "Product Requirements Bitable",
  "target_type": "feishu_bitable",
  "enabled": true,
  "config": {
    "issue_engine": "feishu_bitable",
    "enable": true,
    "language": "Chinese",
    "feishu_bitable": {
      "app_id": "your-app-id",
      "app_secret": "your-app-secret",
      "app_token": "your-app-token",
      "app_token_type": "wiki",
      "table_name": "Issue Collection",
      "attachment_field_name": "Attachments"
    }
  },
  "strategies": {
    "auto_merge_strategy": "new",
    "manual_merge_strategy": "linked",
    "retry_issue_strategy": "update"
  },
  "field_mappings": {
    "Issue Summary": "title",
    "Requirement Collection": "summary_content",
    "Notes": "llm_content",
    "Priority": "feishu_priority",
    "Status": "feishu_status",
    "Source ID": "email_id_str"
  }
}
```

### Deprecated Files and Commands

#### Removed Files
- `conf/threadline/issues/issue_config.yaml` ❌
- `conf/threadline/issues/jira_config.yaml` ❌
- `conf/threadline/issues/feishu_bitable_config.yaml` ❌

#### Deprecated Commands
- `python manage.py init_threadline_settings` - Still works but shows deprecation warning

### Frequently Asked Questions

**Q: Will my existing configuration stop working?**
A: No. Existing configurations are automatically migrated and will continue to work.

**Q: Can I still use the old YAML files?**
A: No. The YAML files have been removed. Use Relay API or Django Admin instead.

**Q: How do I configure multiple JIRA projects?**
A: Create multiple Relay subscriptions, one for each JIRA project.

**Q: What happens to my `init_threadline_settings` scripts?**
A: The command still works but is deprecated. Update your scripts to use the Relay API.

**Q: Where can I find my migrated configuration?**
A: Check Django Admin at `/admin/relay/relaysubscription/` or use the API at `/api/relay/subscriptions/`

### Need Help?

- **Documentation**: See README.md sections on "JIRA Configuration" and "Feishu Bitable Configuration"
- **API Reference**: Visit `/api/schema/swagger-ui/` for interactive API documentation
- **Legacy Command Documentation**: See `devify/threadline/management/commands/DEPRECATED.md`

### Timeline

- **2026-05-10**: YAML files removed, Relay API is the standard method
- **Future**: `init_threadline_settings` command will be removed entirely
