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


if posix_ipc_defined and getattr(posix_ipc, "MESSAGE_QUEUES_SUPPORTED", True):
    import multiprocessing as mp
    import random
    import signal
    import time
    from contextlib import contextmanager

    import pytest

    from nob.ipc import Flags, NamedMessageQueue

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
    def mq_name():
        # It is better if each unit test has a unique message queue name, for isolation purposes
        return "test_mq_" + str(random.randint(0, 2**24))

    def create_mq_task(mq_name, event):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.RAISE_IF_EXISTS
        )
        event.set()
        while mq:
            time.sleep(1)

    @pytest.fixture(autouse=True)
    def cleanup_mq(mq_name):
        # Cleanup before test
        try:
            posix_ipc.unlink_message_queue(f"/{mq_name}")
        except posix_ipc.ExistentialError:
            pass

        yield

        # Cleanup after test
        try:
            posix_ipc.unlink_message_queue(f"/{mq_name}")
        except posix_ipc.ExistentialError:
            pass

    def test_init_basic(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.name == f"/{mq_name}"
        assert mq.linked_existing_object is False
        assert mq.max_messages == 10
        assert mq.max_message_size == 1024

    def test_init_invalid_name():
        with pytest.raises(ValueError):
            NamedMessageQueue("")
        with pytest.raises(ValueError):
            NamedMessageQueue("test@mq")

    def test_init_invalid_max_messages(mq_name):
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_messages=-1)
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_messages=0)
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_messages="10")  # type: ignore

    def test_init_invalid_max_message_size(mq_name):
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_message_size=-1)
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_message_size=0)
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, max_message_size="1024")  # type: ignore

    def test_init_invalid_read_write(mq_name):
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, read="True")  # type: ignore
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, write="True")  # type: ignore

    def test_init_invalid_handle_existence(mq_name):
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, handle_existence=100)  # type: ignore
        with pytest.raises(ValueError):
            NamedMessageQueue(mq_name, handle_existence="RAISE_IF_EXISTS")  # type: ignore

    def test_raise_if_exists(mq_name):
        # First creation should succeed
        mq1 = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.RAISE_IF_EXISTS
        )
        assert mq1.linked_existing_object is False

        # Second creation should fail
        with pytest.raises(FileExistsError):
            NamedMessageQueue(
                mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.RAISE_IF_EXISTS
            )

    def test_raise_if_not_exists_when_not_exists(mq_name):
        # Should fail when message queue doesn't exist
        with pytest.raises(FileNotFoundError):
            NamedMessageQueue(mq_name, handle_existence=Flags.RAISE_IF_NOT_EXISTS)

    def test_raise_if_not_exists_when_exists(mq_name):
        # Create first message queue
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.linked_existing_object is False

        # Successful to existing message queue
        mq_link = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.RAISE_IF_NOT_EXISTS
        )
        assert mq_link.linked_existing_object is True

    def test_link_or_create(mq_name):
        # First creation
        mq1 = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq1.linked_existing_object is False

        # Second should link
        mq2 = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq2.linked_existing_object is True

    def test_unlink_and_create(mq_name):
        # Create first message queue
        NamedMessageQueue(
            mq_name,
            max_messages=10,
            max_message_size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,  # Don't unlink the message queue on garbage collection
        )

        # Delete and create new one
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.UNLINK_AND_CREATE
        )
        assert mq.linked_existing_object is False

    def test_unlink_and_create_no_fail_if_not_exists(mq_name):
        # Delete and create new one
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.UNLINK_AND_CREATE
        )
        assert mq.linked_existing_object is False

    def test_link_bad_permissions(mq_name, require_root):
        # Create message queue with default permissions
        NamedMessageQueue(
            mq_name,
            max_messages=10,
            max_message_size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,
        )

        # Should fail to link to message queue
        with dropping_root_privileges():
            with pytest.raises(PermissionError):
                NamedMessageQueue(
                    mq_name,
                    max_messages=10,
                    max_message_size=1024,
                    handle_existence=Flags.LINK_OR_CREATE,
                    unlink_on_delete=False,
                )

    def test_properties(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert isinstance(mq.mdq, int)
        assert mq.mdq >= 0
        assert mq.block is True
        mq.block = False
        assert mq.block is False

    def test_send_receive_basic(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.current_messages == 0

        assert mq.send(b"hello") is True
        assert mq.current_messages == 1

        msg = mq.receive()
        assert msg == (b"hello", 0)
        assert mq.current_messages == 0

    def test_send_invalid_timeout(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        with pytest.raises(ValueError):
            mq.send(b"test", timeout=-1)
        with pytest.raises(ValueError):
            mq.send(b"test", timeout="1")  # type: ignore

    def test_receive_invalid_timeout(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        with pytest.raises(ValueError):
            mq.receive(timeout=-1)
        with pytest.raises(ValueError):
            mq.receive(timeout="1")  # type: ignore

    def test_send_timeout_when_full(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=1, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.send(b"first") is True

        # Second send should timeout
        assert mq.send(b"second", timeout=0.1) is False

    def test_send_non_blocking_when_full(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=1, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        mq.block = False
        assert mq.send(b"first") is True
        # Second send should immediately fail (return False)
        assert mq.send(b"second") is False

    def test_receive_timeout_when_empty(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.receive(timeout=0.1) is None

    def test_receive_non_blocking_when_empty(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        mq.block = False
        assert mq.receive() is None

    def test_send_receive_priority(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.send(b"low", priority=1) is True
        assert mq.send(b"high", priority=10) is True
        assert mq.send(b"medium", priority=5) is True

        # Higher priority first
        assert mq.receive() == (b"high", 10)
        assert mq.receive() == (b"medium", 5)
        assert mq.receive() == (b"low", 1)

    def test_request_notification(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=5, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        # Basic notification request to cancel notification (passing None) should succeed
        assert mq.request_notification(None) is True

    def test_unlink(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        mq.unlink()

        # Should raise when trying to link to non-existent message queue
        with pytest.raises(FileNotFoundError):
            NamedMessageQueue(mq_name, handle_existence=Flags.RAISE_IF_NOT_EXISTS)

    def test_unlink_bad_permissions(mq_name, require_root):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )

        with dropping_root_privileges():
            # Should fail to unlink message queue
            with pytest.raises(PermissionError):
                mq.unlink()
            # Fails with warning, but should not raise
            mq.__del__()

    def test_unlink_on_delete_auto_mode(mq_name):
        mq = NamedMessageQueue(
            mq_name, max_messages=10, max_message_size=1024, handle_existence=Flags.LINK_OR_CREATE
        )
        assert mq.unlink_on_delete is True
        mq.__del__()
        with pytest.raises(posix_ipc.ExistentialError):
            posix_ipc.unlink_message_queue(f"/{mq_name}")

    def test_unlink_on_delete_explicit_mode_to_false(mq_name):
        mq = NamedMessageQueue(
            mq_name,
            max_messages=10,
            max_message_size=1024,
            handle_existence=Flags.LINK_OR_CREATE,
            unlink_on_delete=False,
        )
        assert mq.unlink_on_delete is False
        mq.__del__()
        posix_ipc.unlink_message_queue(f"/{mq_name}")

    def test_unlink_on_sigint(mq_name):
        create_event = mp.Event()
        process = mp.Process(target=create_mq_task, args=(mq_name, create_event), daemon=True)
        process.start()
        create_event.wait()
        os.kill(process.pid, signal.SIGINT)
        process.join()

        # Should result in non-zero exit code after KeyboardInterrupt is raised
        assert process.exitcode == 1

        # As SIGINT is handled with normal exit flow, message queue should be unlinked during cleanup
        with pytest.raises(posix_ipc.ExistentialError):
            posix_ipc.unlink_message_queue(f"/{mq_name}")

    def test_unlink_on_signal_unhandled_signal(mq_name):
        create_event = mp.Event()
        process = mp.Process(target=create_mq_task, args=(mq_name, create_event), daemon=True)
        process.start()
        create_event.wait()
        os.kill(process.pid, signal.SIGTERM)
        process.join()
        assert process.exitcode != 0

        # Message queue should not be unlinked as SIGTERM is not handled
        posix_ipc.unlink_message_queue(f"/{mq_name}")
