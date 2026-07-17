import logging
import os
import sys

import structlog

def configure_logging(level: str | None = None, json_ouput: bool | None = None) -> None:
    """Idempotent global logger configuration.
    
    Resolution for each setting: explicit arg > env var > default.
    
    LOG_LEVEL   - stdlib level name (debug/info/warning/...). Default: info.
    LOG_JSON    - force JSON output. Default: JSON if stderr is non-TTY (CI/prod)
    """
    log_level_name = (level or os.environ.get("LOG_LEVEL", "info")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO) # value or the log level name

    if json_ouput is None:
        json_ouput = (
            os.environ.get("LOG_JSON", "").lower() in {"1", "yes", "true"}
            or not sys.stderr.isatty()
        )
    
    renderer = (
        structlog.processors.JSONRenderer() if json_ouput else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"), # 2026-07-17 13:36:29,
            renderer
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True
    )
    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stderr)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # the environment variables are loaded into the runtime exec.
    
    # Console Rendering (json_output=False)
    configure_logging()
    log = structlog.get_logger()
    log.info(
        "ticket_classifed",
        ticket_id="TKT-10001",
        priority="urgent",
        category="billing",
        confidence=0.94,
    )
    log.warning(
        "enrichment_slow",
        ticket_id="TKT-10001",
        duration_ms=3420,
    )

    # JSON rendering (json_output)
    # configure_logging(level="info", json_ouput=True)
    # log = structlog.get_logger()
    # log.info(
    #     "ticket_classifed",
    #     ticket_id="TKT-10001",
    #     priority="urgent",
    #     category="billing",
    #     confidence=0.94,
    # )