import logging
import os
import shutil
import tempfile


from devtoolbox.api_clients.jira_client import JiraClient


logger = logging.getLogger(__name__)

class JiraHandler:
    """
    Handler for JIRA operations, such as creating issues and
    uploading attachments.
    """
    def __init__(self, jira_url, username, password):
        """
        Initialize JiraHandler with connection info and create JiraClient.
        """
        self.jira_url = jira_url
        self.username = username
        self.password = password
        self.client = JiraClient(
            jira_url=jira_url,
            username=username,
            password=password
        )

    def create_issue(
        self,
        project_key,
        summary,
        issue_type,
        description=None,
        assignee=None,
        priority=None,
        labels=None,
        components=None,
        fix_versions=None,
        epic_link=None,
        epic_name=None,
        sprint=None
    ):
        """
        Create a JIRA issue using the provided parameters.
        """
        try:
            issue_key = self.client.create_issue(
                project_key=project_key,
                summary=summary,
                issue_type=issue_type,
                description=description,
                assignee=assignee,
                priority=priority,
                labels=labels,
                components=components,
                fix_versions=fix_versions,
                epic_link=epic_link,
                epic_name=epic_name,
                sprint=sprint
            )
            logger.info(f"Successfully created issue: {issue_key}")
            return issue_key
        except Exception as e:
            logger.error(
                "Failed to create issue: %s",
                str(e),
                exc_info=True
            )
            raise

    def upload_attachment(self, issue_key, file_path, filename=None):
        """
        Upload attachment to JIRA issue.
        """
        try:
            # If filename is provided and different from the actual file name,
            # create a temporary copy with the desired filename
            actual_filename = os.path.basename(file_path)
            if filename and filename != actual_filename:
                # Create temporary file with desired filename
                temp_dir = tempfile.mkdtemp()
                temp_file_path = os.path.join(temp_dir, filename)
                shutil.copy2(file_path, temp_file_path)
                upload_path = temp_file_path
                logger.info(
                    f"Created temporary file {temp_file_path} "
                    f"with filename {filename} for JIRA upload"
                )
            else:
                upload_path = file_path

            attachment_info = self.client.add_attachment(
                issue=issue_key,
                file_path=upload_path
            )
            logger.info(
                f"Successfully uploaded attachment {filename or actual_filename} "
                f"to issue {issue_key}"
            )

            # Clean up temporary file if created
            if filename and filename != actual_filename:
                try:
                    os.remove(temp_file_path)
                    os.rmdir(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to cleanup temporary file {temp_file_path}: "
                        f"{cleanup_error}"
                    )

            return attachment_info
        except Exception as e:
            logger.error(
                "Failed to upload attachment %s to issue %s: %s",
                filename or os.path.basename(file_path),
                issue_key,
                str(e),
                exc_info=True
            )
            raise