import logging

from sqlalchemy import text

from common.database.postgres_database import SessionLocal

logger = logging.getLogger(__name__)


def delete_records():
    """delete any transcripts that might have crept into the DB by cabinet office or dsit users, to comply with DPIA"""
    with SessionLocal() as session:
        statement = text("""DELETE FROM transcription
    USING "user"
    WHERE transcription.user_id = "user".id
      AND ("user".email LIKE '%cabinetoffice%' OR "user".email LIKE '%dsit%');
    """)
        result = session.exec(statement)
        session.commit()
        logger.info("deleted %s rows", result.rowcount)
