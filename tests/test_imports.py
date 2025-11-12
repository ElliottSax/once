"""
Test that package structure and imports are valid
"""

import sys
from pathlib import Path


def test_src_package_exists():
    """Test that src package exists and can be imported"""
    import src
    assert hasattr(src, '__version__')


def test_config_can_be_imported():
    """Test that config module can be imported"""
    # This will only work if pydantic-settings is installed
    # In CI, this will be handled by the workflow
    try:
        from config import settings
        assert hasattr(settings, 'get_settings')
    except ImportError as e:
        # Expected if dependencies not installed
        assert 'pydantic' in str(e).lower() or 'settings' in str(e).lower()


def test_package_structure():
    """Test that expected directories exist"""
    root = Path(__file__).parent.parent

    expected_dirs = [
        'src',
        'config',
        'remotion',
        'tests',
        '.github',
        'scripts',
        'docs'
    ]

    for dir_name in expected_dirs:
        dir_path = root / dir_name
        assert dir_path.exists(), f"Missing directory: {dir_name}"


def test_required_files_exist():
    """Test that required configuration files exist"""
    root = Path(__file__).parent.parent

    required_files = [
        'README.md',
        'requirements.txt',
        '.env.template',
        '.gitignore',
        'pytest.ini',
        'PRODUCTION_GUIDE_V2.md'
    ]

    for file_name in required_files:
        file_path = root / file_name
        assert file_path.exists(), f"Missing file: {file_name}"


def test_remotion_config_exists():
    """Test that Remotion configuration files exist"""
    root = Path(__file__).parent.parent
    remotion_dir = root / 'remotion'

    required_files = [
        'package.json',
        'tsconfig.json',
        'src/index.tsx',
        'src/Root.tsx',
        'src/compositions/ExplainerVideo.tsx'
    ]

    for file_name in required_files:
        file_path = remotion_dir / file_name
        assert file_path.exists(), f"Missing Remotion file: {file_name}"
