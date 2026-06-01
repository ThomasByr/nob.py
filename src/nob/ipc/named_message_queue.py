import logging
from collections.abc import Callable
from typing import Any

from typing_extensions import override

from .features import Flags, NamedIPC, posix_ipc

__all__ = ["NamedMessageQueue"]


class NamedMessageQueue(NamedIPC):
    """Class to handle a POSIX-IPC named message queue."""

    def __init__(
        self,
        name: str,
        max_messages: int | None = None,
        max_message_size: int | None = None,
        read: bool = True,
        write: bool = True,
        handle_existence: Flags = Flags.RAISE_IF_NOT_EXISTS,
        unlink_on_delete: bool | None = None,
    ) -> None:
        """Create a POSIX IPC named message queue.

        The `handle_existence` parameter controls the behavior regarding the existence of the message queue:
        - `RAISE_IF_EXISTS`: Creates a new message queue, raises an error if it already exists.
        - `LINK_OR_CREATE`: Links to the existing message queue if it exists.
        - `RAISE_IF_NOT_EXISTS`: Links to the existing message queue if it exists, raises an error otherwise.
        - `UNLINK_AND_CREATE`: Deletes the existing message queue and creates a new one.

        The message queue is automatically unlinked when the object is deleted if it was
        created by this handle. Else, the message queue is only closed.

        Args:
            name (str): The name of the message queue.
            max_messages (int | None, optional): The maximum number of messages the queue can hold.
                Defaults to None, which uses `QUEUE_MESSAGES_MAX_DEFAULT`.
            max_message_size (int | None, optional): The maximum size (in bytes) of a message.
                Defaults to None, which uses `QUEUE_MESSAGE_SIZE_MAX_DEFAULT`.
            read (bool, optional): If True, the message queue can be read from. Defaults to True.
            write (bool, optional): If True, the message queue can be written to. Defaults to True.
            handle_existence (NamedMessageQueue.Flags, optional): Behavior regarding existence of the message queue.
                Defaults to `RAISE_IF_NOT_EXISTS`.
            unlink_on_delete (bool | None): If True, the message queue will be unlinked when the
                object is deleted or garbage collected. If False, the message queue will only be closed.
                Defaults to None, which evaluates to True if the message queue was created by this handle.

        Raises:
            ValueError: If the input parameters are invalid.
            PermissionError: If the message queue cannot be created (or deleted with
                `UNLINK_AND_CREATE`) due to permissions.
            FileExistsError: If the message queue already exists and could not be removed after
                setting `handle_existence` to `RAISE_IF_EXISTS`.
            FileNotFoundError: If the message queue could not be found after setting
                `handle_existence` to `RAISE_IF_NOT_EXISTS`.

        Example:
            >>> mq = NamedMessageQueue("/test_queue", handle_existence=Flags.UNLINK_AND_CREATE)
            >>> mq.send("Hello, World!")
            True
            >>> message, priority = mq.receive()
            >>> print(message.decode(), priority)
            Hello, World! 0
        """

        self.__max_messages = (
            getattr(posix_ipc, "QUEUE_MESSAGES_MAX_DEFAULT", 10) if max_messages is None else max_messages
        )
        self.__max_message_size = (
            getattr(posix_ipc, "QUEUE_MESSAGE_SIZE_MAX_DEFAULT", 8192)
            if max_message_size is None
            else max_message_size
        )

        if not (isinstance(self.__max_messages, int) and self.__max_messages > 0):
            raise ValueError("`max_messages` must be a positive integer")
        if not (isinstance(self.__max_message_size, int) and self.__max_message_size > 0):
            raise ValueError("`max_message_size` must be a positive integer")
        if not isinstance(read, bool):
            raise ValueError("`read` must be a boolean")
        if not isinstance(write, bool):
            raise ValueError("`write` must be a boolean")

        self.__read = read
        self.__write = write
        super().__init__(name, handle_existence, unlink_on_delete)
        self.logger = logging.getLogger("mq")

    @override
    def _create_new(self) -> Any:
        return posix_ipc.MessageQueue(
            self.name,
            posix_ipc.O_CREX,
            max_messages=self.__max_messages,
            max_message_size=self.__max_message_size,
            read=self.__read,
            write=self.__write,
        )

    @override
    def _link_existing(self) -> Any:
        return posix_ipc.MessageQueue(
            self.name,
            0,
            max_messages=self.__max_messages,
            max_message_size=self.__max_message_size,
            read=self.__read,
            write=self.__write,
        )

    @override
    def _unlink_global(self) -> None:
        posix_ipc.unlink_message_queue(self.name)

    @override
    def _close_handle(self) -> None:
        self.handle.close()

    @property
    def mdq(self) -> int:
        return self.handle.mqd

    @property
    def block(self) -> bool:
        return self.handle.block

    @block.setter
    def block(self, value: bool) -> None:
        self.handle.block = value

    @property
    def current_messages(self) -> int:
        return self.handle.current_messages

    @property
    def max_message_size(self) -> int:
        return self.handle.max_message_size

    @property
    def max_messages(self) -> int:
        return self.handle.max_messages

    def send(self, message: bytes | str, timeout: float | None = None, priority: int = 0) -> bool:
        """Send a message to the queue, optionally with a timeout and priority.

        Args:
            message (bytes | str): The message to send. If a string is provided, it will be encoded as UTF-8.
            timeout (float | None, optional): The timeout for the send operation.
                `None` means to wait indefinitely until the message is sent. `0` means to not wait at all. Defaults to None.
            priority (int, optional): The priority of the message. Defaults to 0.

        Raises:
            ValueError: If the input parameters are invalid.

        Returns:
            bool: True if the message was sent, False if the queue was full and the message could not be sent within the timeout.
        """
        if not isinstance(timeout, (float, int)) and timeout is not None:
            raise ValueError("`timeout` must be a float or None")
        if timeout is not None and timeout < 0:
            raise ValueError("If provided, `timeout` must be a positive float")

        kwargs: dict[str, Any] = {"priority": priority}
        if timeout is not None:
            kwargs["timeout"] = timeout

        try:
            self.handle.send(message, **kwargs)
            return True
        except posix_ipc.BusyError:
            return False

    def receive(self, timeout: float | None = None) -> tuple[bytes, int] | None:
        """Receive a message from the queue, optionally with a timeout.

        Args:
            timeout (float | None, optional): The timeout for the receive operation.
                `None` means to wait indefinitely until a message is received. `0` means to not wait at all. Defaults to None.

        Raises:
            ValueError: If the input parameters are invalid.

        Returns:
            tuple[bytes, int] | None: The received message and its priority, or None if the timeout was reached.
        """
        if not isinstance(timeout, (float, int)) and timeout is not None:
            raise ValueError("`timeout` must be a float or None")
        if timeout is not None and timeout < 0:
            raise ValueError("If provided, `timeout` must be a positive float")

        kwargs: dict[str, Any] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout

        try:
            return self.handle.receive(**kwargs)
        except posix_ipc.BusyError:
            return None

    def request_notification(self, notification: int | tuple[Callable, Any] | None = None) -> bool:
        """Request a notification when a message is sent to the queue.

        Args:
            notification (int | tuple[Callable, Any] | None, optional): Requests or cancels notification from the operating system when the queue changes from empty to non-empty. Defaults to None.
                - When *notification* is not provided or `None`, any existing notification request is cancelled.
                - When *notification* is an integer, notification will be sent as a signal of this value that can be caught using a signal handler installed with `signal.signal()`.
                - When *notification* is a tuple of `(function, param)`, notification will be sent by invoking *`function(param)`* in a new thread.
        Returns:
            bool: _description_
        """
        try:
            self.handle.request_notification(notification)
            return True
        except posix_ipc.BusyError:
            return False
