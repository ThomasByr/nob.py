import logging
from abc import ABC, abstractmethod
from typing import Any

from ...utils.auto_numbered_enum import AutoNumberedEnum

try:
    import posix_ipc  # pyright: ignore[reportMissingImports]
except ImportError:

    class dummy:
        def __getattr__(self, _):
            raise NotImplementedError("The current OS does not provide working POSIX IPC.")

    posix_ipc = dummy()

__all__ = ["Flags", "NamedIPC"]


class Flags(AutoNumberedEnum):
    """Enum for the flags to handle existing IPC objects."""

    RAISE_IF_EXISTS = ()
    RAISE_IF_NOT_EXISTS = ()
    LINK_OR_CREATE = ()
    UNLINK_AND_CREATE = ()


class NamedIPC(ABC):
    """Abstract base class for named IPC objects."""

    def __init__(
        self,
        name: str,
        handle_existence: Flags = Flags.RAISE_IF_NOT_EXISTS,
        unlink_on_delete: bool | None = None,
    ) -> None:
        """Initialize the IPC object and handle existence flags."""
        self.__name = "/" + name.lstrip("/") if isinstance(name, str) else ""
        self.__unlink_on_delete = unlink_on_delete
        self.__linked_existing_object: bool | None = None
        self.__handle = None

        self.logger = logging.getLogger(self.__class__.__name__)

        if not self.__name[1:] or not all(c.isalnum() or c in ("-", "_") for c in self.__name[1:]):
            raise ValueError(
                f"`name` must be a non-empty string with characters '-', '_' or alphanumeric. Got: {name}"
            )
        if not isinstance(handle_existence, Flags):
            raise ValueError("`handle_existence` must be a Flags enum")

        if handle_existence == Flags.UNLINK_AND_CREATE:
            try:
                self._unlink_global()
            except BaseException:
                pass

        if handle_existence == Flags.RAISE_IF_NOT_EXISTS:
            try:
                self.__handle = self._link_existing()
                self.__linked_existing_object = True
            except posix_ipc.ExistentialError as e:
                raise FileNotFoundError(f"{self.__class__.__name__} {self.name} does not exist.") from e
            return

        try:
            try:
                self.__handle = self._create_new()
                self.__linked_existing_object = False
            except posix_ipc.ExistentialError as e:  # Try to link
                self.__handle = self._link_existing()
                self.__linked_existing_object = True
                if handle_existence == Flags.RAISE_IF_EXISTS:
                    raise FileExistsError(f"{self.__class__.__name__} {self.name} already exists.") from e
        except posix_ipc.PermissionsError as e:
            raise PermissionError(f"Permission denied creating {self.__class__.__name__} {self.name}.") from e

    @property
    def name(self) -> str:
        """Get the registered name of the IPC object."""
        return getattr(self, "_NamedIPC__name", "")

    @property
    def linked_existing_object(self) -> bool | None:
        """Whether the handle is linked to an existing IPC object or a new one."""
        return getattr(self, "_NamedIPC__linked_existing_object", None)

    @property
    def unlink_on_delete(self) -> bool:
        """Whether to unlink the IPC object globally when the handle is deleted."""
        u_delete = getattr(self, "_NamedIPC__unlink_on_delete", None)
        if u_delete is not None:
            return u_delete
        linked = getattr(self, "_NamedIPC__linked_existing_object", None)
        return linked is False

    @property
    def handle(self) -> Any:
        """Get the underlying IPC handle object."""
        return getattr(self, "_NamedIPC__handle", None)

    def unlink(self) -> None:
        """Unlink the IPC object globally."""
        try:
            self._unlink_global()
        except posix_ipc.ExistentialError as e:
            raise FileNotFoundError(f"{self.__class__.__name__} {self.name} does not exist.") from e
        except posix_ipc.PermissionsError as e:
            raise PermissionError(
                f"Permission denied unlinking {self.__class__.__name__} {self.name}."
            ) from e

    def close(self) -> None:
        """Close the local IPC handle."""
        if self.handle is not None:
            try:
                self._close_handle()
            except Exception:
                pass
            self.__handle = None

    def __del__(self) -> None:
        """Destructor for the class. Unlinks if it was created by this handle."""
        self.close()
        if (not self.name) or (not self.unlink_on_delete):
            return

        try:
            self.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            self.logger.warning(f"Permission denied unlinking {self.__class__.__name__} during cleanup.")

    @abstractmethod
    def _create_new(self) -> Any:
        pass

    @abstractmethod
    def _link_existing(self) -> Any:
        pass

    @abstractmethod
    def _unlink_global(self) -> None:
        pass

    @abstractmethod
    def _close_handle(self) -> None:
        pass
