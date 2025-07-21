from celery import shared_task
from datetime import datetime
import logging

from .models import Post

logger = logging.getLogger(__name__)


@shared_task()
def async_task(post_id):
    """
    Asynchronous task to handle operations related to a specific post.

    This task is intended to be called via an API to perform background processing
    for a given post identified by `post_id`. The task will print the details of
    the specified post.

    Args:
        post_id (int): The unique identifier of the post to process.

    Returns:
        None
    """
    try:
        post = Post.objects.get(id=post_id)
        logger.info(f"Post details: {post}")
    except Post.DoesNotExist:
        logger.error(f"Post with id {post_id} does not exist")
    pass


@shared_task()
def heartbeat():
    """
    Simulates querying the Post model and logs the count of posts found.

    This is a demonstration function intended to be used as an asynchronous
    task. It logs the start of the heartbeat process, queries the Post model
    to count the number of posts, and logs the count of posts found.

    Returns:
        bool: Always returns True.
    """
    posts_count = Post.objects.count()
    logger.info(f"Do Heartbeat for posts, found {posts_count} posts")
    return True


@shared_task()
def show_current_time():
    """
    Outputs the current time to demonstrate dynamic scheduling of tasks.

    This function is intended to be called as a scheduled task to log the
    current time whenever it is executed.

    Returns:
        None
    """
    current_time = datetime.now()
    logger.info(f"Current time: {current_time}")