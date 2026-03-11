"""
populate_corpus_a.py — One-time Corpus A (Methodology Bible) ingestion.

Run once: python -m scripts.populate_corpus_a
Never run again after initial population (static corpus).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.intelligence.rag_engine import ingest_document, get_corpus_stats


def populate():
    """Populate Corpus A with methodology documents."""
    total_chunks = 0

    # 1. METHODOLOGY.md
    methodology_path = project_root / "docs" / "METHODOLOGY.md"
    if methodology_path.exists():
        text = methodology_path.read_text()
        n = ingest_document(
            text=text,
            metadata={"corpus": "a", "type": "methodology", "source": "METHODOLOGY.md"},
            corpus="corpus_a",
        )
        print(f"  METHODOLOGY.md: {n} chunks")
        total_chunks += n
    else:
        print("  WARNING: METHODOLOGY.md not found")

    # 2. Pine Scripts
    pine_dir = project_root / "backend" / "pine_scripts"
    if pine_dir.exists():
        for pine_file in sorted(pine_dir.glob("*.pine")):
            text = pine_file.read_text()
            n = ingest_document(
                text=text,
                metadata={"corpus": "a", "type": "pine_script", "source": pine_file.name},
                corpus="corpus_a",
            )
            print(f"  {pine_file.name}: {n} chunks")
            total_chunks += n

    # 3. Trading Rules
    rules_path = project_root / "backend" / "services" / "trading_rules.py"
    if rules_path.exists():
        text = rules_path.read_text()
        n = ingest_document(
            text=text,
            metadata={"corpus": "a", "type": "trading_rules", "source": "trading_rules.py"},
            corpus="corpus_a",
        )
        print(f"  trading_rules.py: {n} chunks")
        total_chunks += n

    # 4. Dhan Setup
    dhan_path = project_root / "docs" / "DHAN_SETUP.md"
    if dhan_path.exists():
        text = dhan_path.read_text()
        n = ingest_document(
            text=text,
            metadata={"corpus": "a", "type": "broker_setup", "source": "DHAN_SETUP.md"},
            corpus="corpus_a",
        )
        print(f"  DHAN_SETUP.md: {n} chunks")
        total_chunks += n

    # 5. Pine Script Guide
    guide_path = project_root / "docs" / "PINE_SCRIPT_GUIDE.md"
    if guide_path.exists():
        text = guide_path.read_text()
        n = ingest_document(
            text=text,
            metadata={"corpus": "a", "type": "pine_guide", "source": "PINE_SCRIPT_GUIDE.md"},
            corpus="corpus_a",
        )
        print(f"  PINE_SCRIPT_GUIDE.md: {n} chunks")
        total_chunks += n

    print(f"\nCorpus A population complete: {total_chunks} total chunks")
    print(f"Corpus stats: {get_corpus_stats()}")


if __name__ == "__main__":
    print("Populating Corpus A (Methodology Bible)...")
    populate()
    print("Done. Do not run this script again.")
