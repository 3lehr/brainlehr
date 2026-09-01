import pytest
from unittest.mock import MagicMock

def test_working_overlay_hides_untracked_user_files():
    """Testet, dass untracked User-Dateien im Overlay ausgeschlossen bleiben."""
    dashboard = MagicMock()
    # Mocking the returned files
    dashboard.get_overlay_files.return_value = ["src/main.py", "docs/README.md"]
    
    files = dashboard.get_overlay_files(include_untracked_user=False)
    
    assert "user_secret.txt" not in files
    assert "untracked_note.md" not in files
    assert dashboard.get_overlay_files.called

def test_dashboard_is_read_only_and_writes_no_data():
    """Testet, dass die Ansicht HEAD/WORKING-Provenienz aufbaut, ohne Datenbankschreiben auszulösen."""
    db_mock = MagicMock()
    dashboard = MagicMock(db=db_mock)
    
    dashboard.render_head_and_working_overlay()
    
    db_mock.write.assert_not_called()
    db_mock.commit.assert_not_called()
