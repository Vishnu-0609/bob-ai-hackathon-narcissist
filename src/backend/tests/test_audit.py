import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.entities import Base, AuditLog
from app.services.audit_service import AuditService


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


def test_audit_hash_chain_validity(db_session):
    # Log multiple events
    AuditService.log_event(db_session, user_id="u1", role="ADMIN", action="LOGIN", entity_type="USER", entity_id="u1", details={"ip": "127.0.0.1"})
    AuditService.log_event(db_session, user_id="u1", role="COORDINATOR", action="AM_CREATED", entity_type="AM", entity_id="AM-001", details={"name": "Test Person"})
    AuditService.log_event(db_session, user_id="u1", role="COORDINATOR", action="MATCH_CALCULATED", entity_type="PM", entity_id="PM-001", details={"score": 92})

    verify = AuditService.verify_integrity(db_session)
    assert verify["valid"] is True
    assert verify["events_checked"] == 3
    assert verify["broken_at"] is None


def test_tampered_audit_event_detected(db_session):
    AuditService.log_event(db_session, user_id="u1", role="ADMIN", action="LOGIN", entity_type="USER", entity_id="u1", details={"ip": "127.0.0.1"})
    e2 = AuditService.log_event(db_session, user_id="u1", role="COORDINATOR", action="RECONCILIATION_CONFIRMED", entity_type="RECONCILIATION", entity_id="PM-001<->AM-001", details={"score": 92})
    AuditService.log_event(db_session, user_id="u1", role="COORDINATOR", action="REPORT_GENERATED", entity_type="REPORT", entity_id="REP-001", details={})

    # Tamper with event details directly in DB without updating hash
    e2.details = {"score": 99, "tampered": True}
    db_session.commit()

    verify = AuditService.verify_integrity(db_session)
    assert verify["valid"] is False
    assert verify["broken_at"] == e2.event_id
