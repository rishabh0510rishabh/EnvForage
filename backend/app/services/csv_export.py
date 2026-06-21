
# --- Generic CSV Stream Exporter ---
import csv
import io
import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("CSVExporter")

class CSVExportService:
    """
    A highly optimized CSV export service designed for Massive Data.
    Instead of loading 100k records into memory, it uses SQLAlchemy
    `yield_per` and FastAPI `StreamingResponse` to generate CSV chunks on the fly.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_csv_chunks(
        self,
        model: type[Any],
        columns: list[str],
        chunk_size: int = 1000
    ) -> AsyncGenerator[str, None]:
        """
        Yields CSV strings chunk by chunk.
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)

        # Write Header
        writer.writeheader()
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Build streaming query
        stmt = select(model).execution_options(yield_per=chunk_size)

        try:
            # stream() executes the query asynchronously and yields chunks
            result = await self.db.stream(stmt)

            async for row in result.scalars():
                row_dict = {}
                for col in columns:
                    val = getattr(row, col, "")
                    # Format datetime, None, etc.
                    if val is None:
                        val = ""
                    row_dict[col] = str(val)

                writer.writerow(row_dict)

                # We yield row by row (or we could buffer and yield chunk by chunk)
                # Here we yield every row to keep memory absolutely minimal
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        except Exception as e:
            logger.error(f"CSV Streaming failed midway: {e}")
            yield f"\n\nERROR: Export failed midway due to server error: {e}"

    def get_streaming_response(self, model: type[Any], columns: list[str], filename: str = "export.csv"):
        """
        Returns a FastAPI StreamingResponse configured for file download.
        """
        from fastapi.responses import StreamingResponse

        generator = self._generate_csv_chunks(model, columns)

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8"
        }

        return StreamingResponse(generator, headers=headers, media_type="text/csv")
