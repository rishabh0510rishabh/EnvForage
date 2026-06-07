import io

from app.api.v1.scripts import _stream_zip


def test_stream_zip_closes_buffer():
    buffer = io.BytesIO(b"test-data")

    chunks = list(_stream_zip(buffer))

    assert chunks == [b"test-data"]
    assert buffer.closed
