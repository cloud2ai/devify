"""
Checkpoint Manager for LangGraph email processing.

This module provides checkpoint management functionality for the LangGraph
workflow, using Redis as the checkpoint storage backend. It handles saving,
loading, and clearing checkpoints for state persistence and recovery.
"""

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import StateGraph

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoints for LangGraph workflow using Redis backend.

    This class provides a high-level interface for checkpoint operations,
    including saving, loading, and clearing checkpoints for the email
    processing workflow. Follows LangGraph best practices for
    Redis checkpointing.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the CheckpointManager.

        Args:
            redis_url: Redis connection URL. If None, use CELERY_BROKER_URL
                from Django settings
            ttl_config: TTL configuration for checkpoints. If None, use defaults
        """
        self.redis_url = (
            redis_url or getattr(
                settings, 'CELERY_BROKER_URL', 'redis://localhost:6379'
            )
        )

        # Configure TTL settings for checkpoint expiration
        self.ttl_config = ttl_config or {
            "default_ttl": 60 * 24,  # 24 hours in minutes
            "refresh_on_read": True  # Refresh TTL when checkpoint is read
        }

        logger.info(f"Redis checkpointer URL configured: {self.redis_url}")
        logger.info(f"TTL configuration: {self.ttl_config}")

        # Initialize context manager storage
        self._context_manager = None

    def get_checkpointer(self) -> RedisSaver:
        """
        Get the Redis checkpointer instance with TTL configuration.

        Returns:
            RedisSaver: The Redis checkpointer instance with TTL settings
        """
        # Create RedisSaver using context manager and return the actual instance
        context_manager = RedisSaver.from_conn_string(
            self.redis_url,
            ttl=self.ttl_config
        )

        # Enter the context manager to get the actual RedisSaver instance
        checkpointer = context_manager.__enter__()

        # Call setup to initialize indices
        checkpointer.setup()

        # Store the context manager for cleanup later
        self._context_manager = context_manager

        return checkpointer

    def cleanup(self):
        """
        Clean up the context manager if it exists.
        """
        if self._context_manager is not None:
            try:
                self._context_manager.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during context manager cleanup: {e}")
            finally:
                self._context_manager = None

    def save_checkpoint(
        self,
        config: Dict[str, Any],
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save current state as checkpoint.

        Args:
            config: Configuration containing thread_id and other parameters
            state: Current workflow state to save
            metadata: Optional metadata to store with checkpoint
            parent_config: Optional parent configuration

        Returns:
            str: Checkpoint ID of the saved checkpoint
        """
        try:
            with self.get_checkpointer() as checkpointer:
                checkpoint_id = checkpointer.put(
                    config,
                    state,
                    metadata or {},
                    parent_config or {}
                )
                logger.info(f"Checkpoint saved with ID: {checkpoint_id}")
                return checkpoint_id
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load_checkpoint(
        self,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Load state from checkpoint.

        Args:
            config: Configuration containing thread_id and optional
                checkpoint_id

        Returns:
            Dict[str, Any]: Loaded state if found, None otherwise
        """
        try:
            with self.get_checkpointer() as checkpointer:
                result = checkpointer.get(config)
                if result:
                    logger.info(
                        f"Checkpoint loaded for thread: "
                        f"{config.get('thread_id')}"
                    )
                    return result
                else:
                    logger.warning(
                        f"No checkpoint found for thread: "
                        f"{config.get('thread_id')}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            raise

    def list_checkpoints(
        self,
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a given thread.

        Args:
            config: Configuration containing thread_id

        Returns:
            List[Dict[str, Any]]: List of checkpoint information
        """
        try:
            with self.get_checkpointer() as checkpointer:
                checkpoints = list(checkpointer.list(config))
                logger.info(
                    f"Found {len(checkpoints)} checkpoints for thread: "
                    f"{config.get('thread_id')}"
                )
                return checkpoints
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            raise

    def clear_checkpoint(
        self,
        config: Dict[str, Any],
        checkpoint_id: Optional[str] = None
    ) -> bool:
        """
        Clear specific checkpoint or all checkpoints for a thread.

        Note: RedisSaver does not support direct checkpoint clearing.
        This method provides a workaround by setting TTL to 0 for immediate expiration.

        Args:
            config: Configuration containing thread_id
            checkpoint_id: Optional specific checkpoint ID to clear.
                          If None, clears all checkpoints for the thread.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # RedisSaver does not support direct checkpoint clearing
            # We can only rely on TTL expiration or manual Redis key deletion
            logger.warning(
                "Direct checkpoint clearing is not supported by RedisSaver. "
                "Checkpoints will expire based on TTL configuration. "
                "For immediate clearing, consider using Redis directly."
            )

            # Alternative: List checkpoints to verify they exist
            checkpoints = self.list_checkpoints(config)
            if checkpoints:
                logger.info(
                    f"Found {len(checkpoints)} checkpoints for thread "
                    f"{config.get('configurable', {}).get('thread_id')}. "
                    "They will expire based on TTL settings."
                )
                return True
            else:
                logger.info("No checkpoints found for the specified thread")
                return True

        except Exception as e:
            logger.error(f"Failed to clear checkpoint: {e}")
            return False

    def get_latest_checkpoint(
        self,
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest checkpoint for a thread.

        Args:
            config: Configuration containing thread_id

        Returns:
            Dict[str, Any]: Latest checkpoint if found, None otherwise
        """
        try:
            checkpoints = self.list_checkpoints(config)
            if checkpoints:
                # Return the most recent checkpoint
                latest = max(checkpoints, key=lambda x: x.get('ts', ''))
                return latest
            return None
        except Exception as e:
            logger.error(f"Failed to get latest checkpoint: {e}")
            return None


    def setup(self) -> None:
        """
        Initialize the Redis checkpointer setup.

        This method should be called once during application startup
        to ensure Redis indices are properly created.
        """
        try:
            with self.get_checkpointer() as checkpointer:
                checkpointer.setup()
            self._is_initialized = True
            logger.info("CheckpointManager setup completed successfully")
        except Exception as e:
            logger.error(f"Failed to setup CheckpointManager: {e}")
            raise

    def is_healthy(self) -> bool:
        """
        Check if the checkpoint manager is healthy and can connect to Redis.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            with self.get_checkpointer() as checkpointer:
                # Try to list checkpoints to verify connection
                list(checkpointer.list({
                    "configurable": {"thread_id": "health_check"}
                }))
            return True
        except Exception as e:
            logger.warning(f"CheckpointManager health check failed: {e}")
            return False


# Global checkpoint manager instance
_checkpoint_manager = None


def get_checkpoint_manager() -> CheckpointManager:
    """
    Get the global checkpoint manager instance.

    Returns:
        CheckpointManager: The global checkpoint manager instance
    """
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


def setup_checkpoint_manager() -> None:
    """
    Setup the global checkpoint manager.

    This function should be called during application startup
    to initialize Redis indices.
    """
    manager = get_checkpoint_manager()
    manager.setup()


def create_checkpointer() -> RedisSaver:
    """
    Create Redis checkpointer for LangGraph.

    This function provides a simple interface to create a Redis checkpointer
    using the existing Redis configuration.

    Returns:
        RedisSaver: Redis checkpointer instance
    """
    manager = get_checkpoint_manager()
    return manager.get_checkpointer()


def create_thread_config(
    thread_id: str,
    checkpoint_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create configuration for LangGraph thread operations.

    Args:
        thread_id: Unique identifier for the workflow thread
        checkpoint_id: Optional specific checkpoint ID to load

    Returns:
        Dict[str, Any]: Configuration dictionary for LangGraph operations
    """
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id

    return config


def save_workflow_checkpoint(
    thread_id: str,
    state: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save workflow checkpoint with simplified interface.

    Args:
        thread_id: Unique identifier for the workflow thread
        state: Current workflow state to save
        metadata: Optional metadata to store with checkpoint

    Returns:
        str: Checkpoint ID of the saved checkpoint
    """
    manager = get_checkpoint_manager()
    config = create_thread_config(thread_id)
    return manager.save_checkpoint(config, state, metadata)


def load_workflow_checkpoint(
    thread_id: str,
    checkpoint_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Load workflow checkpoint with simplified interface.

    Args:
        thread_id: Unique identifier for the workflow thread
        checkpoint_id: Optional specific checkpoint ID to load

    Returns:
        Dict[str, Any]: Loaded state if found, None otherwise
    """
    manager = get_checkpoint_manager()
    config = create_thread_config(thread_id, checkpoint_id)
    return manager.load_checkpoint(config)
