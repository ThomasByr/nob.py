import logging
from typing import Any

from typing_extensions import override

from .features import Flags, NamedIPC, posix_ipc

__all__ = ["NamedSharedMemory"]


class NamedSharedMemory(NamedIPC):
    """Class to handle a POSIX-IPC named shared memory."""

    def __init__(
        self,
        name: str,
        size: int = 0,
        read_only: bool = False,
        handle_existence: Flags = Flags.RAISE_IF_NOT_EXISTS,
        unlink_on_delete: bool | None = None,
    ) -> None:
        """Create a POSIX IPC named shared memory segment.

        The `handle_existence` parameter controls the behavior regarding the existence of the shared memory:
        - `RAISE_IF_EXISTS`: Creates a new shared memory segment, raises an error if it already exists.
        - `LINK_OR_CREATE`: Links to the existing shared memory segment if it exists.
        - `RAISE_IF_NOT_EXISTS`: Links to the existing shared memory segment if it exists, raises an error otherwise.
        - `UNLINK_AND_CREATE`: Deletes the existing shared memory segment and creates a new one.

        The shared memory is automatically unlinked when the object is deleted if it was
        created by this handle. Else, the shared memory is only closed.

        Args:
            name (str): The name of the shared memory segment.
            size (int, optional): The size (in bytes) of the shared memory segment. Defaults to 0.
            read_only (bool, optional): If True, the shared memory segment is opened read-only. Defaults to False.
            handle_existence (NamedSharedMemory.Flags, optional): Behavior regarding existence of the shared memory segment.
                Defaults to `RAISE_IF_NOT_EXISTS`.
            unlink_on_delete (bool | None): If True, the shared memory will be unlinked when the
                object is deleted or garbage collected. If False, the shared memory will only be closed.
                Defaults to None, which evaluates to True if the shared memory was created by this handle.

        Raises:
            ValueError: If the input parameters are invalid.
            PermissionError: If the shared memory cannot be created (or deleted with
                `UNLINK_AND_CREATE`) due to permissions.
            FileExistsError: If the shared memory already exists and could not be removed after
                setting `handle_existence` to `RAISE_IF_EXISTS`.
            FileNotFoundError: If the shared memory could not be found after setting
                `handle_existence` to `RAISE_IF_NOT_EXISTS`.

        Example:
            >>> import mmap
            >>> shm = NamedSharedMemory("/test_shm", size=1024, handle_existence=Flags.UNLINK_AND_CREATE)
            >>> memory = mmap.mmap(shm.fd, shm.size)
            >>> memory.write(b"Hello from POSIX IPC")
            >>> memory.seek(0)
            >>> assert memory.read(20) == b"Hello from POSIX IPC"
            >>> memory.close()
        """
        if not (isinstance(size, int) and size >= 0):
            raise ValueError("`size` must be a non-negative integer")
        if not isinstance(read_only, bool):
            raise ValueError("`read_only` must be a boolean")

        self.__size = size
        self.__read_only = read_only
        super().__init__(name, handle_existence, unlink_on_delete)
        self.logger = logging.getLogger("shm")

    @override
    def _create_new(self) -> Any:
        return posix_ipc.SharedMemory(
            self.name, posix_ipc.O_CREX, size=self.__size, read_only=self.__read_only
        )

    @override
    def _link_existing(self) -> Any:
        return posix_ipc.SharedMemory(self.name, 0, size=self.__size, read_only=self.__read_only)

    @override
    def _unlink_global(self) -> None:
        posix_ipc.unlink_shared_memory(self.name)

    @override
    def _close_handle(self) -> None:
        self.handle.close_fd()

    @property
    def size(self) -> int:
        """Get the size of the shared memory segment."""
        return self.handle.size

    @property
    def fd(self) -> int:
        """Get the file descriptor of the shared memory segment."""
        return self.handle.fd

    def __enter__(self) -> "NamedSharedMemory":
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.close()
