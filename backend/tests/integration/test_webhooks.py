
import pytest

from app.core.events import dispatcher


@pytest.mark.asyncio
async def test_event_dispatcher():
    events_received = []

    async def mock_handler(event_name, payload):
        events_received.append((event_name, payload))

    dispatcher.subscribe("test_event", mock_handler)
    await dispatcher.dispatch("test_event", {"key": "value"})

    assert len(events_received) == 1
    assert events_received[0] == ("test_event", {"key": "value"})
