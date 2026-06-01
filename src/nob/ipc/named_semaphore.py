import logging
from typing import Any

from typing_extensions import override

from .features import Flags, NamedIPC, posix_ipc

__all__ = ["NamedSemaphore"]


class NamedSemaphore(NamedIPC):
    """Class to handle a POSIX-IPC named semaphore."""

    def __init__(
        self,
        name: str,
        initial_value: int = 1,
        handle_existence: Flags = Flags.RAISE_IF_NOT_EXISTS,
        unlink_on_delete: bool | None = None,
    ) -> None:
        """Create a POSIX IPC named semaphore.

        The `handle_existence` parameter controls the behavior regarding the existence of the semaphore:
        - `RAISE_IF_EXISTS`: Creates a new semaphore, raises an error if it already exists.
        - `LINK_OR_CREATE`: Links to the existing semaphore if it exists.
        - `RAISE_IF_NOT_EXISTS`: Links to the existing semaphore if it exists, raises an error otherwise.
        - `UNLINK_AND_CREATE`: Deletes the existing semaphore and creates a new one.

        The semaphore is automatically unlinked when the object is deleted if it was
        created by this handle. Else, the semaphore is only closed.

        Args:
            name (str): The name of the semaphore.
            initial_value (int, optional): The initial value of the semaphore. Defaults to 1.
            handle_existence (NamedSemaphore.Flags, optional): Behavior regarding existence of the semaphore.
                Defaults to `RAISE_IF_NOT_EXISTS`.
            unlink_on_delete (bool | None): If True, the semaphore will be unlinked when the
                object is deleted or garbage collected. If False, the semaphore will only be closed.
                Defaults to None, which evaluates to True if the semaphore was created by this handle.

        Raises:
            ValueError: If the input parameters are invalid.
            PermissionError: If the semaphore cannot be created (or deleted with
                `UNLINK_AND_CREATE`) due to permissions.
            FileExistsError: If the semaphore already exists and could not be removed after
                setting `handle_existence` to `RAISE_IF_EXISTS`.
            FileNotFoundError: If the semaphore could not be found after setting
                `handle_existence` to `RAISE_IF_NOT_EXISTS`.

        Example:
            >>> sem = NamedSemaphore("/test_semaphore", handle_existence=Flags.UNLINK_AND_CREATE)
            >>> with sem:  # Acquire the semaphore
            ...     # Critical section
            ...     pass  # Semaphore will be automatically released after the block
        """
        if not (
            isinstance(initial_value, int)
            and 0 <= initial_value <= getattr(posix_ipc, "SEMAPHORE_VALUE_MAX", 32767)
        ):
            raise ValueError(
                f"`initial_value` must be a non-negative integer less than {getattr(posix_ipc, 'SEMAPHORE_VALUE_MAX', 32767)}"
            )
        self.__initial_value = initial_value
        super().__init__(name, handle_existence, unlink_on_delete)
        self.logger = logging.getLogger("sem")

    @override
    def _create_new(self) -> Any:
        return posix_ipc.Semaphore(self.name, posix_ipc.O_CREX, initial_value=self.__initial_value)

    @override
    def _link_existing(self) -> Any:
        return posix_ipc.Semaphore(self.name, 0)

    @override
    def _unlink_global(self) -> None:
        posix_ipc.unlink_semaphore(self.name)

    @override
    def _close_handle(self) -> None:
        self.handle.close()

    @property
    def linked_existing_semaphore(self):
        return self.linked_existing_object

    @property
    def value(self) -> int:
        """Get the current value of the semaphore."""
        if getattr(posix_ipc, "SEMAPHORE_VALUE_SUPPORTED", False) is False:
            raise NotImplementedError("Operation is not supported on this platform")
        return self.handle.value

    def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        """Acquire the semaphore, decrementing its value by one. If the value is zero, block until it becomes possible to acquire.

        Args:
            blocking (bool, optional): If True, block until the semaphore can be acquired. Defaults to True.
            timeout (float | None, optional): The maximum time to wait for the semaphore when blocking. Defaults to None.

        Raises:
            ValueError: If the input parameters are invalid.
            NotImplementedError: If the operation is not supported on the current platform.

        Returns:
            bool: True if the semaphore was acquired, False otherwise.
        """
        if not isinstance(blocking, bool):
            raise ValueError("`blocking` must be a boolean")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout < 0):
            raise ValueError("If provided, `timeout` must be a positive float")

        acquire_kwargs = {}
        if not blocking:
            acquire_kwargs["timeout"] = 0
            if timeout is not None:
                raise ValueError("Cannot specify a timeout if blocking is False")
        elif timeout is not None:
            acquire_kwargs["timeout"] = timeout
            if getattr(posix_ipc, "SEMAPHORE_TIMEOUT_SUPPORTED", False) is False:
                raise NotImplementedError("Timeouts are not supported on this platform")

        try:
            self.handle.acquire(**acquire_kwargs)
            return True
        except posix_ipc.BusyError:
            return False

    def release(self, n: int = 1) -> None:
        """Release the semaphore, incrementing its value by `n` and waking up to `n` waiting acquirers.

        Args:
            n (int, optional): The number of times to release the semaphore. Defaults to 1.

        Raises:
            ValueError: If `n` is not a positive integer.
        """
        if not (isinstance(n, int) and n >= 1):
            raise ValueError("`n` must be a positive integer")
        for _ in range(n):
            self.handle.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.release()
