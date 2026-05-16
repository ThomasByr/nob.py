import logging

try:
    import posix_ipc  # pyright: ignore[reportMissingImports]

except ImportError:

    class dummy:
        def __getattr__(self, _):
            raise NotImplementedError("The current OS does not provide working POSIX IPC.")

    posix_ipc = dummy()

from ..utils.auto_numbered_enum import AutoNumberedEnum

__all__ = ["NamedSemaphore"]


class NamedSemaphore:
    """Class to handle a POSIX-IPC named semaphore.

    This class provides a Pythonic interface to POSIX named semaphores. It supports multi-process
    environments and relies on the underlying thread-safe POSIX IPC implementation. After creation,
    the semaphore handle is primarily read-only, ensuring thread safety for typical usage.

    This semaphores are supported on Linux, macOS and Windows + Cygwin ≥ 1.7. Note that some features
    such as timeouts are not supported on all platforms (e.g. macOS).

    To create a new semaphore ensuring that it did not exist before, you can set the `handle_existence`
    parameter to `RAISE_IF_EXISTS`. This will raise an error if the semaphore already exists:

    ```
    # Raises an error if the semaphore already exists
    my_sem = NamedSemaphore("max_api_calls", handle_existence=NamedSemaphore.Flags.RAISE_IF_EXISTS)
    ```

    To create or link a semaphore ignoring the existence of a previous semaphore with the same name,
    you can use the `LINK_OR_CREATE` parameter:

    ```
    my_sem = NamedSemaphore("max_api_calls", handle_existence=NamedSemaphore.Flags.LINK_OR_CREATE)
    ```

    To create a new semaphore deleting the previous one if it exists, you can set the `handle_existence`
    parameter to `UNLINK_AND_CREATE`. This will delete the existing semaphore and create
    a new one:

    ```
    my_sem = NamedSemaphore("max_api_calls", handle_existence=NamedSemaphore.Flags.UNLINK_AND_CREATE)
    ```

    The class provides a context manager interface, which acquires the semaphore on entry and
    releases it on exit. This is the recommended way to use the semaphore if it is assumed that the
    semaphore was already created. In this case, the RAISE_IF_NOT_EXISTS flag can be used to raise
    an error if the semaphore does not previously exist, ensuring that the semaphore is created
    beforehand:

    ```
    # Raises an error if the semaphore does not yet exist
    with NamedSemaphore("max_api_calls", handle_existence=NamedSemaphore.Flags.RAISE_IF_NOT_EXISTS):
        # Critical section
        ...
    ```

    Unlinking of the semaphore:
    - By default, the semaphore is unlinked by the garbage collector when the object is deleted if
      it was created by this handle. Else, only the descriptor is closed. This behavior can be
      overridden by setting the `unlink_on_delete` parameter in the constructor.
    - The semaphore can also be unlinked manually by calling the `unlink` method. This removes the
      semaphore globally, making it inaccessible by its name.
    """

    class Flags(AutoNumberedEnum):
        """Enum for the flags to handle existing semaphores."""

        RAISE_IF_EXISTS = ()
        RAISE_IF_NOT_EXISTS = ()
        LINK_OR_CREATE = ()
        UNLINK_AND_CREATE = ()

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
        """
        # Save the input parameters
        self.__name = "/" + name.removeprefix("/") if isinstance(name, str) else ""
        self.__unlink_on_delete = unlink_on_delete
        self.__linked_existing_semaphore: bool | None = None
        self.logger = logging.getLogger("sem")

        # Check the input parameters
        if not self.name[1:] or not all(c.isalnum() or c in ("-", "_") for c in self.name[1:]):
            raise ValueError(
                f"`name` must be a non-empty string with characters '-', '_' or alphanumeric. Got: {name}"
            )
        if not (isinstance(initial_value, int) and 0 <= initial_value <= posix_ipc.SEMAPHORE_VALUE_MAX):
            raise ValueError(
                f"`initial_value` must be a non-negative integer less than {posix_ipc.SEMAPHORE_VALUE_MAX}"
            )
        if not (isinstance(handle_existence, NamedSemaphore.Flags)):
            raise ValueError("`handle_existence` must be a NamedSemaphore.Flags enum")

        # Check if the semaphore already exists and remove it if flag is set
        if handle_existence == NamedSemaphore.Flags.UNLINK_AND_CREATE:
            try:
                self.unlink()
            except FileNotFoundError:
                pass

        if handle_existence == NamedSemaphore.Flags.RAISE_IF_NOT_EXISTS:
            # Force link to an existing semaphore if flag is set
            try:
                self.__semaphore_handle = posix_ipc.Semaphore(self.name)
                self.__linked_existing_semaphore = True
            except posix_ipc.ExistentialError as e:
                raise FileNotFoundError(f"Semaphore {self.name} does not exist.") from e
            return

        # Create the semaphore or link to an existing one based on the flag
        try:
            try:
                # O_CREX flag will fail with ExistentialError if the semaphore already exists
                self.__semaphore_handle = posix_ipc.Semaphore(
                    self.name, posix_ipc.O_CREX, initial_value=initial_value
                )
                self.__linked_existing_semaphore = False
            except posix_ipc.ExistentialError as e:  # Try to link
                # Link to an existing semaphore
                self.__semaphore_handle = posix_ipc.Semaphore(
                    self.name, posix_ipc.O_CREAT, initial_value=initial_value
                )
                self.__linked_existing_semaphore = True
                if handle_existence == NamedSemaphore.Flags.RAISE_IF_EXISTS:
                    raise FileExistsError(f"Semaphore {self.name} already exists.") from e
        except posix_ipc.PermissionsError as e:
            raise PermissionError(f"Permission denied creating semaphore {self.name}.") from e

    @property
    def name(self) -> str:
        """Return the name of the semaphore.

        Returns:
            str: The name of the semaphore.
        """
        return self.__name

    @property
    def linked_existing_semaphore(self):
        """Return whether the semaphore was linked to an existing semaphore on handle creation.

        Returns:
            bool | None: True if verifies condition, False otherwise. None if not yet verified.
        """
        return self.__linked_existing_semaphore

    @property
    def unlink_on_delete(self) -> bool:
        """Return whether the semaphore will be unlinked when the object is deleted.
        The default behavior is to unlink the semaphore if it was created by this handle.
        But can be manually overridden by setting the `unlink_on_delete` parameter in the constructor.

        Returns:
            bool: True if the semaphore will be unlinked when the object is deleted, False otherwise.
        """
        if self.__unlink_on_delete is not None:
            return self.__unlink_on_delete
        return self.__linked_existing_semaphore is False

    @property
    def value(self) -> int:
        """Return the current value of the semaphore. Not possible on macOS.

        Returns:
            bool: The current value of the semaphore.
        """
        if not posix_ipc.SEMAPHORE_VALUE_SUPPORTED:
            raise NotImplementedError("Operation is not supported on this platform")
        return self.__semaphore_handle.value

    def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        """Acquire the semaphore.

        Args:
            blocking (bool): If True, the method will block until the semaphore is acquired. If False,
                the method will return immediately, regardless of whether the semaphore was acquired.
            timeout (float | None, optional): If provided, the method will block for at most `timeout` seconds. If the
                semaphore is not acquired within this time, the method will return False. If not provided,
                the method will block indefinitely if `blocking` is True. Not supported on macOS. Defaults to None.

        Raises:
            ValueError: If the input parameters are invalid.
            NotImplementedError: If the platform does not support timeout and a timeout is provided.

        Returns:
            bool: True if the semaphore was acquired, False otherwise.
        """
        # Check the input parameters
        if not isinstance(blocking, bool):
            raise ValueError("`blocking` must be a boolean")
        if timeout is not None and (not isinstance(timeout, float) or timeout < 0):
            raise ValueError("If provided, `timeout` must be a positive float")

        acquire_kwargs = {}  # Setting for the default blocking acquire
        # Non-blocking acquire
        if not blocking:
            acquire_kwargs["timeout"] = 0
            if timeout is not None:
                raise ValueError("Cannot specify a timeout if blocking is False")
        # Blocking acquire with timeout
        elif timeout is not None:
            acquire_kwargs["timeout"] = timeout
            if not posix_ipc.SEMAPHORE_TIMEOUT_SUPPORTED:
                raise NotImplementedError("Timeouts are not supported on this platform")

        # Blocking acquire with timeout
        try:
            self.__semaphore_handle.acquire(**acquire_kwargs)
            return True
        except posix_ipc.BusyError:
            return False

    def release(self, n: int = 1) -> None:
        """Release the semaphore.

        Args:
            n (int, optional): The number of times to release the semaphore. Defaults to 1.

        Raises:
            ValueError: If `n` is invalid.
        """
        # Check the input parameters
        if not (isinstance(n, int) and n >= 1):
            raise ValueError("`n` must be a positive integer")

        # Release the semaphore
        for _ in range(n):
            self.__semaphore_handle.release()

    def unlink(self) -> None:
        """Unlink the semaphore.

        This method removes the semaphore globally, making it inaccessible by its name.
        Any other processes linked to this semaphore will lose access to it. Use this method
        cautiously in shared environments.

        Raises:
            FileNotFoundError: If the semaphore cannot be unlinked due to not existing.
            PermissionError: If the semaphore cannot be unlinked due to permissions.
        """
        try:
            posix_ipc.unlink_semaphore(self.name)
        except posix_ipc.ExistentialError as e:
            raise FileNotFoundError(f"Semaphore {self.name} does not exist.") from e
        except posix_ipc.PermissionsError as e:
            raise PermissionError(f"Permission denied unlinking semaphore {self.name}.") from e

    def __enter__(self):
        """Enter the semaphore context. Acquires the semaphore.

        Returns:
            self: The created object.
        """
        self.acquire()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        """Exit the semaphore context. Releases the semaphore."""
        # Try to release the semaphore
        self.release()

    def __del__(self):
        """Destructor for the class. Unlinks the semaphore if it was created by this handle."""
        # Close the semaphore handle
        if getattr(self, "__semaphore_handle", None) is not None:
            try:
                self.__semaphore_handle.close()
            except posix_ipc.ExistentialError:
                pass

        # Unlink the semaphore if it was created by this handle
        if not self.unlink_on_delete:
            return
        try:
            # Unlink the semaphore
            self.unlink()
        except FileNotFoundError:  # Ignore if the semaphore does not exist
            pass
        except PermissionError:
            self.logger.warning("Permission denied unlinking semaphore during cleanup.")
