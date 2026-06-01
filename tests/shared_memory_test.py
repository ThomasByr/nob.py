# ty:ignore[invalid-argument-type, unresolved-attribute, unused-ignore-comment]  # ty:ignore[unused-ignore-comment]
# unresolved-attribute for os.setegid and os.seteuid are both resolved on UNIX
# Those ignores are unused on UNIX, which is why I need the first unused-ignore-comment,
# but I need the second unused-ignore-comment on Windows to ignore the first one that is indeed unused.
import os

posix_ipc_defined = True
try:
    import posix_ipc  # pyright: ignore[reportMissingImports]
except ImportError:
    posix_ipc_defined = False


if posix_ipc_defined:
    import mmap
    import multiprocessing as mp
    import random
    import signal
    import time
    from contextlib import contextmanager

    import pytest

    from nob.ipc import Flags, NamedSharedMemory

    @contextmanager
    def dropping_root_privileges():
        # Drop privileges to whatever UID and GID are provided in the environment
        uid = int(os.environ.get("UID", 1000))
        gid = int(os.environ.get("GID", 1000))
        os.setegid(gid)
        os.seteuid(uid)

        yield

        # Restore root privileges
        os.seteuid(0)
        os.setegid(0)

    @pytest.fixture
    def require_root():
        if os.getuid() != 0:
            pytest.skip(
                "Test requires root privileges. Re-run tests, prepending your command with `sudo -E env PATH=$PATH`"
            )

    @pytest.fixture
    def shm_name():
        # It is better if each unit test has a unique shared memory name, for isolation purposes
        return "test_shm_" + str(random.randint(0, 2**24))

    def create_shm_task(shm_name, event):
        # We need a size greater than 0
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.RAISE_IF_EXISTS)
        event.set()
        while shm:
            time.sleep(1)

    @pytest.fixture(autouse=True)
    def cleanup_shm(shm_name):
        # Cleanup before test
        try:
            posix_ipc.unlink_shared_memory(f"/{shm_name}")
        except posix_ipc.ExistentialError:
            pass

        yield

        # Cleanup after test
        try:
            posix_ipc.unlink_shared_memory(f"/{shm_name}")
        except posix_ipc.ExistentialError:
            pass

    def test_init_basic(shm_name):
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm.name == f"/{shm_name}"
        assert shm.linked_existing_object is False
        assert shm.size == 1024

    def test_init_invalid_name():
        with pytest.raises(ValueError):
            NamedSharedMemory("")
        with pytest.raises(ValueError):
            NamedSharedMemory("test@shm")

    def test_init_invalid_size(shm_name):
        with pytest.raises(ValueError):
            NamedSharedMemory(shm_name, size=-1)
        with pytest.raises(ValueError):
            NamedSharedMemory(shm_name, size="1024")  # type: ignore

    def test_init_invalid_read_only(shm_name):
        with pytest.raises(ValueError):
            NamedSharedMemory(shm_name, read_only="True")  # type: ignore

    def test_init_invalid_handle_existence(shm_name):
        with pytest.raises(ValueError):
            NamedSharedMemory(shm_name, handle_existence=100)  # type: ignore
        with pytest.raises(ValueError):
            NamedSharedMemory(shm_name, handle_existence="RAISE_IF_EXISTS")  # type: ignore

    def test_raise_if_exists(shm_name):
        # First creation should succeed
        shm1 = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.RAISE_IF_EXISTS)
        assert shm1.linked_existing_object is False

        # Second creation should fail
        with pytest.raises(FileExistsError):
            NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.RAISE_IF_EXISTS)

    def test_raise_if_not_exists_when_not_exists(shm_name):
        # Should fail when shared memory doesn't exist
        with pytest.raises(FileNotFoundError):
            NamedSharedMemory(shm_name, handle_existence=Flags.RAISE_IF_NOT_EXISTS)

    def test_raise_if_not_exists_when_exists(shm_name):
        # Create first shared memory
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm.linked_existing_object is False

        # Successful to existing shared memory
        shm_link = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.RAISE_IF_NOT_EXISTS)
        assert shm_link.linked_existing_object is True

    def test_link_or_create(shm_name):
        # First creation
        shm1 = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm1.linked_existing_object is False

        # Second should link
        shm2 = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm2.linked_existing_object is True

    def test_unlink_and_create(shm_name):
        # Create first shared memory
        NamedSharedMemory(
            shm_name,
            size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,  # Don't unlink the shared memory on garbage collection
        )

        # Delete and create new one
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.UNLINK_AND_CREATE)
        assert shm.linked_existing_object is False

    def test_unlink_and_create_no_fail_if_not_exists(shm_name):
        # Delete and create new one
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.UNLINK_AND_CREATE)
        assert shm.linked_existing_object is False

    def test_link_bad_permissions(shm_name, require_root):
        # Create shared memory with default permissions
        NamedSharedMemory(
            shm_name,
            size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,
        )

        # Should fail to link to shared memory
        with dropping_root_privileges():
            with pytest.raises(PermissionError):
                NamedSharedMemory(
                    shm_name,
                    size=1024,
                    handle_existence=Flags.LINK_OR_CREATE,
                    unlink_on_delete=False,
                )

    def test_size_and_fd(shm_name):
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm.size == 1024
        assert isinstance(shm.fd, int)
        assert shm.fd >= 0

    def test_shm_mmap(shm_name):
        shm = NamedSharedMemory(shm_name, size=100, handle_existence=Flags.UNLINK_AND_CREATE)

        # Mmap and write
        memory = mmap.mmap(shm.fd, shm.size)
        memory.write(b"Hello from POSIX IPC")
        memory.seek(0)
        assert memory.read(20) == b"Hello from POSIX IPC"
        memory.close()

    def test_unlink(shm_name):
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        shm.unlink()

        # Should raise when trying to link to non-existent shared memory
        with pytest.raises(FileNotFoundError):
            NamedSharedMemory(shm_name, handle_existence=Flags.RAISE_IF_NOT_EXISTS)

    def test_unlink_bad_permissions(shm_name, require_root):
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)

        with dropping_root_privileges():
            # Should fail to unlink shared memory
            with pytest.raises(PermissionError):
                shm.unlink()
            # Fails with warning, but should not raise
            shm.__del__()

    def test_unlink_on_delete_auto_mode(shm_name):
        shm = NamedSharedMemory(shm_name, size=1024, handle_existence=Flags.LINK_OR_CREATE)
        assert shm.unlink_on_delete is True
        shm.__del__()
        with pytest.raises(posix_ipc.ExistentialError):
            posix_ipc.unlink_shared_memory(f"/{shm_name}")

    def test_unlink_on_delete_explicit_mode_to_false(shm_name):
        shm = NamedSharedMemory(
            shm_name,
            size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,
        )
        assert shm.unlink_on_delete is False
        shm.__del__()
        posix_ipc.unlink_shared_memory(f"/{shm_name}")

    def test_unlink_on_sigint(shm_name):
        create_event = mp.Event()
        process = mp.Process(target=create_shm_task, args=(shm_name, create_event), daemon=True)
        process.start()
        create_event.wait()
        os.kill(process.pid, signal.SIGINT)
        process.join()

        # Should result in non-zero exit code after KeyboardInterrupt is raised
        assert process.exitcode == 1

        # As SIGINT is handled with normal exit flow, shared memory should be unlinked during cleanup
        with pytest.raises(posix_ipc.ExistentialError):
            posix_ipc.unlink_shared_memory(f"/{shm_name}")

    def test_unlink_on_signal_unhandled_signal(shm_name):
        create_event = mp.Event()
        process = mp.Process(target=create_shm_task, args=(shm_name, create_event), daemon=True)
        process.start()
        create_event.wait()
        os.kill(process.pid, signal.SIGTERM)
        process.join()
        assert process.exitcode != 0

        # Shared memory should not be unlinked as SIGTERM is not handled
        posix_ipc.unlink_shared_memory(f"/{shm_name}")
