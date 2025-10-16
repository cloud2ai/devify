"""
Base LangGraph Node implementation.

This module provides the base class for all LangGraph nodes in the
email processing workflow, ensuring consistent structure, error handling,
and logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from threadline.agents.email_state import (
    EmailState,
    add_node_error,
    has_node_errors,
    get_node_errors_by_name
)

logger = logging.getLogger(__name__)


class BaseLangGraphNode(ABC):
    """
    Base class for all LangGraph nodes in the email processing workflow.

    This class provides a standardized structure for LangGraph nodes with:
    - Three-phase processing: before_processing, execute_processing,
      after_processing
    - Consistent error handling and logging based on node_errors
    - Automatic node entry validation based on error states

    Subclasses can implement:
    - before_processing(): Pre-processing validation and setup
    - execute_processing(): Core business logic (required)
    - after_processing(): Post-processing cleanup and finalization
    """

    def __init__(self, node_name: str):
        """
        Initialize the base node.

        Args:
            node_name (str): Name of the node for logging and identification
        """
        self.node_name = node_name

    def __call__(self, state: EmailState) -> EmailState:
        """
        LangGraph Node standard call interface.

        This is the main entry point for LangGraph nodes. It provides a
        three-phase processing flow with error handling and logging.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated email state
        """
        try:
            logger.info(f"[{self.node_name}] Starting processing")

            if not self.can_enter_node(state):
                logger.warning(
                    f"[{self.node_name}] Cannot enter due to existing errors"
                )
                return state

            state = self.before_processing(state)

            state = self.execute_processing(state)

            state = self.after_processing(state)

            logger.info(f"[{self.node_name}] Processing completed")
            return state

        except Exception as e:
            logger.error(f"[{self.node_name}] Error occurred: {e}")
            return self._handle_error(e, state)

    def can_enter_node(self, state: EmailState) -> bool:
        """
        Check if this node can enter based on error state.

        By default, nodes can enter if there are no errors in the system.
        Subclasses can override this for custom entry logic.

        Args:
            state (EmailState): Current email state

        Returns:
            bool: True if node can enter, False otherwise
        """
        return not has_node_errors(state)

    def before_processing(self, state: EmailState) -> EmailState:
        """
        Pre-processing phase: validation, setup, and preparation.

        This method can be overridden by subclasses for
        custom pre-processing. Default implementation does nothing.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state after pre-processing
        """
        return state

    @abstractmethod
    def execute_processing(self, state: EmailState) -> EmailState:
        """
        Execute the main processing logic for this node.

        This method contains the core business logic for the node.
        Must be implemented by subclasses.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state after processing
        """
        pass

    def after_processing(self, state: EmailState) -> EmailState:
        """
        Post-processing phase: cleanup, finalization, and validation.

        This method can be overridden by subclasses for
        custom post-processing. Default implementation does nothing.

        Args:
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state after post-processing
        """
        return state

    def _handle_error(
        self, error: Exception, state: EmailState
    ) -> EmailState:
        """
        Handle errors that occur during node processing.

        Records the error in the node_errors field for this specific node.

        Args:
            error (Exception): The error that occurred
            state (EmailState): Current email state

        Returns:
            EmailState: Updated state with error information
        """
        error_message = str(error)
        state = add_node_error(state, self.node_name, error_message)

        logger.error(f"[{self.node_name}] Node failed: {error}")
        return state
