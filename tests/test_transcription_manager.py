import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from common.database.postgres_models import Recording, Transcription
from common.services.exceptions import TranscriptionFailedError
from common.services.storage_services import StorageService
from common.services.transcription_services.adapter import AdapterType, TranscriptionAdapter
from common.services.transcription_services.transcription_manager import TranscriptionServiceManager
from common.types import TranscriptionJobMessageData


class MockStorageService(StorageService):
    """Mock storage service for testing."""

    async def download(self, s3_file_key: str, local_file_path: str) -> None:  # noqa: ARG002
        return None

    async def upload(self, local_file_path: str, s3_file_key: str) -> None:  # noqa: ARG002
        return None

    async def delete(self, s3_file_key: str) -> None:  # noqa: ARG002
        return None

    async def check_object_exists(self, s3_file_key: str, expires_in: int = 3600) -> bool:  # noqa: ARG002
        return True


class MockAdapter(TranscriptionAdapter):
    """Mock adapter for testing."""

    def __init__(
        self,
        name: str,
        max_audio_length: int = 1800,
        is_available: bool = True,
        adapter_type: AdapterType = AdapterType.SYNCHRONOUS,
    ):
        self.name = name
        self.max_audio_length = max_audio_length
        self._is_available = is_available
        self.adapter_type = adapter_type

    def is_available(self) -> bool:
        return self._is_available

    async def start(self, audio_file_path_or_recording) -> TranscriptionJobMessageData:  # noqa: ARG002
        return TranscriptionJobMessageData(
            job_name="test_job_name",
            transcript=[{"text": "Test transcript", "speaker": "Speaker1", "start": 0.0, "end": 1.0}],
        )

    async def check(self, message_data: TranscriptionJobMessageData) -> TranscriptionJobMessageData:
        return message_data


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    with patch("common.services.transcription_services.transcription_manager.settings") as mock_settings:
        mock_settings.TRANSCRIPTION_SERVICES = ["MockAdapter1", "MockAdapter2"]
        mock_settings.DATA_S3_BUCKET = "test-bucket"
        mock_settings.AWS_REGION = "us-east-1"
        yield mock_settings


@pytest.fixture
def mock_storage_service():
    with patch(
        "common.services.transcription_services.transcription_manager.storage_service", new_callable=MockStorageService
    ) as mock_storage_service:
        yield mock_storage_service


@pytest.fixture
def mock_adapters():
    """Create mock adapters for testing."""
    adapter1 = MockAdapter(
        "MockAdapter1", max_audio_length=1800, is_available=True, adapter_type=AdapterType.SYNCHRONOUS
    )
    adapter2 = MockAdapter("MockAdapter2", max_audio_length=3600, is_available=True, adapter_type=AdapterType.ASYNC)
    adapter3 = MockAdapter(
        "MockAdapter3", max_audio_length=900, is_available=False, adapter_type=AdapterType.SYNCHRONOUS
    )

    adapters = {
        "MockAdapter1": adapter1,
        "MockAdapter2": adapter2,
        "MockAdapter3": adapter3,
    }

    with patch("common.services.transcription_services.transcription_manager._adapters", adapters):
        yield adapters


@pytest.fixture
def manager(mock_settings, mock_adapters):  # noqa: ARG001
    """Create TranscriptionServiceManager instance for testing."""
    return TranscriptionServiceManager()


@pytest.fixture
def mock_recording():
    """Create mock recording for testing."""
    recording = Mock(spec=Recording)
    recording.s3_file_key = "test_file.mp3"
    return recording


@pytest.fixture
def mock_transcription(mock_recording):
    """Create mock transcription for testing."""
    transcription = Mock(spec=Transcription)
    transcription.recordings = [mock_recording]
    return transcription


@pytest.fixture
def sample_message_data():
    """Create sample TranscriptionJobMessageData for testing."""
    return TranscriptionJobMessageData(
        job_name="test_job",
        transcript=[{"text": "Test transcript", "speaker": "Speaker1", "start_time": 0.0, "end_time": 1.0}],
        transcription_service="MockAdapter1",
    )


class TestTranscriptionServiceManager:
    """Test class for TranscriptionServiceManager."""

    def test_init_with_available_adapters(self, manager):
        """Test initialization with available adapters."""
        # Should only include available adapters that are in settings
        assert len(manager._available_adapters) == 2  # noqa: SLF001
        assert "MockAdapter1" in manager._available_adapters  # noqa: SLF001
        assert "MockAdapter2" in manager._available_adapters  # noqa: SLF001
        assert "MockAdapter3" not in manager._available_adapters  # noqa: SLF001

    def test_init_with_no_available_adapters(self, mock_adapters):  # noqa: ARG002
        """Test initialization when no adapters are available."""
        with patch("common.services.transcription_services.transcription_manager.settings") as mock_settings:
            mock_settings.TRANSCRIPTION_SERVICES = ["NonExistentAdapter"]

            manager = TranscriptionServiceManager()
            assert len(manager._available_adapters) == 0  # noqa: SLF001

    def test_get_available_services(self, manager):
        """Test get_available_services method."""
        available_services = manager.get_available_services()

        assert len(available_services) == 2
        assert "MockAdapter1" in available_services
        assert "MockAdapter2" in available_services

    def test_get_available_services_with_unavailable_adapter(self, mock_adapters):  # noqa: ARG002
        """Test get_available_services when adapter is unavailable."""
        with patch("common.services.transcription_services.transcription_manager.settings") as mock_settings:
            mock_settings.TRANSCRIPTION_SERVICES = ["MockAdapter3"]  # This one is not available

            manager = TranscriptionServiceManager()
            available_services = manager.get_available_services()

            assert len(available_services) == 0

    @pytest.mark.parametrize(
        "duration,expected_adapter",  # noqa: PT006
        [
            (1500, "MockAdapter1"),  # Should select MockAdapter1 (1800s max) for 1500s duration
            (2000, "MockAdapter2"),  # Should select MockAdapter2 (3600s max) for 2000s duration
        ],
    )
    def test_select_adaptor_success(self, manager, duration, expected_adapter):
        """Test successful adapter selection based on duration."""
        adapter = manager.select_adaptor(duration)
        assert adapter.name == expected_adapter

    def test_select_adaptor_no_suitable_adapter(self, manager):
        """Test adapter selection when no adapter can handle the duration."""
        with pytest.raises(RuntimeError, match="No transcription services are available"):
            manager.select_adaptor(5000)  # Exceeds all adapters' max length

    @pytest.mark.asyncio
    @patch("common.services.transcription_services.transcription_manager.convert_american_to_british_spelling")
    async def test_check_transcription_success(self, mock_convert_spelling, manager, sample_message_data):
        """Test successful transcription check."""
        mock_convert_spelling.return_value = "Test transcript (British)"

        result = await manager.check_transcription("MockAdapter1", sample_message_data)

        assert result.job_name == "test_job"
        mock_convert_spelling.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_transcription_adapter_not_available(self, manager):
        """Test transcription check with unavailable adapter."""
        message_data = TranscriptionJobMessageData(
            job_name="test_job", transcript=None, transcription_service="NonExistentAdapter"
        )

        with pytest.raises(TranscriptionFailedError, match="Transcription service NonExistentAdapter is not available"):
            await manager.check_transcription("NonExistentAdapter", message_data)

    @pytest.mark.asyncio
    async def test_check_transcription_no_transcript(self, manager):
        """Test transcription check when transcript is None."""
        message_data = TranscriptionJobMessageData(
            job_name="test_job", transcript=None, transcription_service="MockAdapter1"
        )

        result = await manager.check_transcription("MockAdapter1", message_data)
        assert result.transcript is None

    @pytest.mark.asyncio
    async def test_perform_transcription_steps_synchronous(
        self,
        mock_storage_service,  # noqa: ARG002
        manager,
        mock_recording,
        mock_transcription,
    ):
        """Test perform_transcription_steps with synchronous adapter."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch.object(manager, "get_recording_to_process") as mock_get_recording,
        ):
            # Setup mocks
            mock_duration = 1500.0
            mock_get_recording.return_value = (mock_recording, Path(temp_file.name), mock_duration)
            mock_adapter = manager.select_adaptor(int(mock_duration))

            with patch.object(mock_adapter, "start") as mock_start:
                mock_start.return_value = TranscriptionJobMessageData(
                    job_name="test_job",
                    transcript=[{"text": "Test transcript", "speaker": "Speaker1", "start_time": 0.0, "end_time": 1.0}],
                    transcription_service=mock_adapter.name,
                )

                result = await manager.perform_transcription_steps(mock_transcription)

                assert result.job_name == "test_job"
                assert result.transcript is not None
                mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_transcription_steps_asynchronous(
        self,
        mock_storage_service,  # noqa: ARG002
        manager,
        mock_recording,
        mock_transcription,
    ):
        """Test perform_transcription_steps with asynchronous adapter."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch.object(manager, "get_recording_to_process") as mock_get_recording,
            patch.object(manager, "check_transcription") as mock_check_transcription,
        ):
            # Setup mocks
            mock_duration = 3500.0  # Should trigger async adapter
            mock_get_recording.return_value = (mock_recording, Path(temp_file.name), mock_duration)
            mock_adapter = manager.select_adaptor(int(mock_duration))
            assert mock_adapter.adapter_type == AdapterType.ASYNC

            with patch.object(mock_adapter, "start") as mock_start:
                # Return transcription job without transcript to trigger check_transcription
                mock_start.return_value = TranscriptionJobMessageData(
                    job_name="test_job", transcription_service=mock_adapter.name
                )
                mock_check_transcription.return_value = TranscriptionJobMessageData(
                    job_name="test_job",
                    transcript=[{"text": "Test transcript", "speaker": "Speaker1", "start_time": 0.0, "end_time": 1.0}],
                    transcription_service=mock_adapter.name,
                )

                result = await manager.perform_transcription_steps(mock_transcription)

                assert result.job_name == "test_job"
                assert result.transcript is not None
                mock_start.assert_called_once_with(audio_file_path_or_recording=mock_recording)
                mock_check_transcription.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_transcription_steps_unknown_adapter_type(
        self,
        mock_storage_service,  # noqa: ARG002
        manager,
        mock_recording,
        mock_transcription,
    ):
        """Test perform_transcription_steps with unknown adapter type."""
        with (
            tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file,
            patch.object(manager, "get_recording_to_process") as mock_get_recording,
            patch.object(manager, "select_adaptor") as mock_select_adaptor,
        ):
            # Setup mocks
            mock_get_recording.return_value = (mock_recording, Path(temp_file.name), 1500)

            # Create adapter with unknown type
            mock_adapter = Mock()
            mock_adapter.adapter_type = "UNKNOWN_TYPE"
            mock_select_adaptor.return_value = mock_adapter

            with pytest.raises(RuntimeError, match="adapter not recognised"):
                await manager.perform_transcription_steps(mock_transcription)
