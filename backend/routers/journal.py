from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import WeeklyJournal, get_db
from backend.models.journal import JournalCreate, JournalResponse, JournalUpdate

router = APIRouter(prefix="/journal", tags=["Journal"])


@router.get("", response_model=list[JournalResponse])
def list_journals(db: Session = Depends(get_db)):
    """List all weekly journals, most recent first."""
    return (
        db.query(WeeklyJournal)
        .order_by(WeeklyJournal.week_start.desc())
        .all()
    )


@router.get("/{week_start}", response_model=JournalResponse)
def get_journal(week_start: date, db: Session = Depends(get_db)):
    """Get a specific week's journal."""
    journal = (
        db.query(WeeklyJournal)
        .filter(WeeklyJournal.week_start == week_start)
        .first()
    )
    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return journal


@router.post("", response_model=JournalResponse)
def create_journal(entry: JournalCreate, db: Session = Depends(get_db)):
    """Create a new weekly journal entry."""
    # Check for duplicate week
    existing = (
        db.query(WeeklyJournal)
        .filter(WeeklyJournal.week_start == entry.week_start)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Journal entry for week starting {entry.week_start} already exists",
        )

    # Calculate weekly return if both values provided
    weekly_return_pct = None
    if entry.account_value_start and entry.account_value_end:
        weekly_return_pct = round(
            ((entry.account_value_end - entry.account_value_start)
             / entry.account_value_start)
            * 100,
            2,
        )

    db_journal = WeeklyJournal(
        **entry.model_dump(),
        weekly_return_pct=weekly_return_pct,
    )
    db.add(db_journal)
    db.commit()
    db.refresh(db_journal)
    return db_journal


@router.patch("/{week_start}", response_model=JournalResponse)
def update_journal(
    week_start: date, update: JournalUpdate, db: Session = Depends(get_db)
):
    """Update or complete a journal entry."""
    journal = (
        db.query(WeeklyJournal)
        .filter(WeeklyJournal.week_start == week_start)
        .first()
    )
    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(journal, field, value)

    # Recalculate weekly return if account values changed
    if journal.account_value_start and journal.account_value_end:
        journal.weekly_return_pct = round(
            ((journal.account_value_end - journal.account_value_start)
             / journal.account_value_start)
            * 100,
            2,
        )

    db.commit()
    db.refresh(journal)
    return journal
