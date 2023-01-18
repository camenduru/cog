import logging
import signal
import sys
from argparse import ArgumentParser
from typing import Any

import structlog
import uvicorn

from ..logging import setup_logging
from .http import create_app
from .redis import RedisConsumer
from .queue_worker import QueueWorker

log = structlog.get_logger("cog.director")


def _die(signum: Any, frame: Any) -> None:
    log.warning("caught early SIGTERM: exiting immediately!")
    sys.exit(1)


# We are probably running as PID 1 so need to explicitly register a handler
# to die on SIGTERM. This will be overwritten once we start uvicorn.
signal.signal(signal.SIGTERM, _die)

parser = ArgumentParser()

parser.add_argument("--redis-url", required=True)
parser.add_argument("--redis-input-queue", required=True)
parser.add_argument("--redis-consumer-id", required=True)
parser.add_argument("--predict-timeout", type=int, default=1800)
parser.add_argument(
    "--max-failure-count",
    type=int,
    default=5,
    help="Maximum number of consecutive failures before the worker should exit",
)

setup_logging(log_level=logging.INFO)

args = parser.parse_args()

redis_consumer = RedisConsumer(
    redis_url=args.redis_url,
    redis_input_queue=args.redis_input_queue,
    redis_consumer_id=args.redis_consumer_id,
    predict_timeout=args.predict_timeout,
)
app = create_app(
    redis_consumer=redis_consumer,
    predict_timeout=args.predict_timeout,
    max_failure_count=args.max_failure_count,
)
uvicorn.run(app, port=4900, log_config=None)