from unittest.mock import patch

import pytest

from nob.ipc import NamedSemaphore


def test_ipc_objects_require_the_ipc_extra():
    with patch("nob.ipc.features.posix_ipc", None):
        with pytest.raises(ImportError, match="ipc.*extra"):
            NamedSemaphore("foo")


def test_ipc_objects_unsupported_on_windows():
    with patch("nob.ipc.features.posix_ipc", None), patch("sys.platform", "win32"):
        with pytest.raises(NotImplementedError, match="Windows"):
            NamedSemaphore("foo")
