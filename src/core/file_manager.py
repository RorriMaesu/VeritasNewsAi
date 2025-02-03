import tempfile
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

@contextmanager
def managed_tempfile(prefix: str = "tmp"):
    path = None
    try:
        fd, path = tempfile.mkstemp(prefix=prefix)
        yield Path(path)
    except Exception as e:
        logger.error(f"Temp file error: {str(e)}")
        raise
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to clean {path}: {str(e)}") 