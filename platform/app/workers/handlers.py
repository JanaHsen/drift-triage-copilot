from app.workers.replay import handle_replay
from app.workers.retrain import handle_retrain
from app.workers.rollback import handle_rollback

HANDLERS = {
    "replay": handle_replay,
    "retrain": handle_retrain,
    "rollback": handle_rollback,
}
