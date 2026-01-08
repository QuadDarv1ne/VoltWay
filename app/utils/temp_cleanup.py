import logging
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TempFileCleanupManager:
    """Manages automatic cleanup of temporary files and directories"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        # Define patterns for temporary files to clean
        self.temp_patterns = [
            "*.tmp",
            "*.temp", 
            "*~",
            ".DS_Store",
            "Thumbs.db",
            ".coverage",
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".mypy_cache",
            ".ruff_cache",
            ".tox",
            "build/",
            "dist/",
            "*.egg-info/",
            ".eggs/",
        ]
        
        # Directories to clean completely
        self.temp_directories = [
            "tmp",
            "temp", 
            ".temp",
            ".tmp",
        ]
    
    def cleanup_temp_files(self) -> Tuple[int, List[str]]:
        """
        Clean up temporary files and directories
        
        Returns:
            Tuple of (files_deleted_count, errors_list)
        """
        logger.info("Starting temporary file cleanup")
        cleaned_count = 0
        errors = []
        
        # Clean temporary directories
        for temp_dir_name in self.temp_directories:
            temp_dir = self.project_root / temp_dir_name
            if temp_dir.exists():
                try:
                    logger.debug(f"Cleaning temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir, onerror=self._handle_remove_readonly)
                    cleaned_count += 1
                    logger.info(f"Removed temporary directory: {temp_dir}")
                except Exception as e:
                    error_msg = f"Failed to remove {temp_dir}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        # Clean files matching patterns
        for pattern in self.temp_patterns:
            try:
                # Handle directory patterns (ending with /)
                if pattern.endswith('/'):
                    dir_pattern = pattern.rstrip('/')
                    for item in self.project_root.rglob(dir_pattern):
                        if item.is_dir():
                            try:
                                logger.debug(f"Cleaning directory: {item}")
                                shutil.rmtree(item, onerror=self._handle_remove_readonly)
                                cleaned_count += 1
                                logger.info(f"Removed directory: {item}")
                            except Exception as e:
                                error_msg = f"Failed to remove {item}: {e}"
                                errors.append(error_msg)
                                logger.error(error_msg)
                else:
                    # Handle file patterns
                    for item in self.project_root.rglob(pattern):
                        if item.is_file():
                            try:
                                logger.debug(f"Cleaning file: {item}")
                                item.unlink()
                                cleaned_count += 1
                                logger.info(f"Removed file: {item}")
                            except Exception as e:
                                error_msg = f"Failed to remove {item}: {e}"
                                errors.append(error_msg)
                                logger.error(error_msg)
                        elif item.is_dir() and pattern == "__pycache__":
                            # Special handling for __pycache__ directories
                            try:
                                logger.debug(f"Cleaning __pycache__ directory: {item}")
                                shutil.rmtree(item, onerror=self._handle_remove_readonly)
                                cleaned_count += 1
                                logger.info(f"Removed __pycache__ directory: {item}")
                            except Exception as e:
                                error_msg = f"Failed to remove {item}: {e}"
                                errors.append(error_msg)
                                logger.error(error_msg)
                                
            except Exception as e:
                error_msg = f"Error processing pattern {pattern}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Clean system temporary files created by this application
        cleaned_system, system_errors = self._cleanup_system_temp()
        cleaned_count += cleaned_system
        errors.extend(system_errors)
        
        logger.info(f"Temporary file cleanup completed: {cleaned_count} items cleaned")
        return cleaned_count, errors
    
    def _cleanup_system_temp(self) -> Tuple[int, List[str]]:
        """Clean up system temporary files created by this application"""
        cleaned_count = 0
        errors = []
        
        try:
            temp_dir = Path(tempfile.gettempdir())
            app_prefixes = ["voltway_", "vw_", "charging_"]
            
            for prefix in app_prefixes:
                for temp_item in temp_dir.glob(f"{prefix}*"):
                    try:
                        if temp_item.is_file():
                            temp_item.unlink()
                            cleaned_count += 1
                            logger.debug(f"Removed system temp file: {temp_item}")
                        elif temp_item.is_dir():
                            shutil.rmtree(temp_item, onerror=self._handle_remove_readonly)
                            cleaned_count += 1
                            logger.debug(f"Removed system temp directory: {temp_item}")
                    except Exception as e:
                        error_msg = f"Failed to remove system temp {temp_item}: {e}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        
        except Exception as e:
            error_msg = f"Error cleaning system temporary files: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            
        return cleaned_count, errors
    
    def _handle_remove_readonly(self, func, path, exc):
        """Handle readonly files during removal"""
        try:
            if os.path.exists(path):
                os.chmod(path, stat.S_IWRITE)
                func(path)
        except Exception as e:
            logger.warning(f"Could not remove readonly file {path}: {e}")
    
    def get_temp_stats(self) -> dict:
        """Get statistics about temporary files"""
        stats = {
            "temp_directories": [],
            "temp_files": [],
            "total_size_bytes": 0
        }
        
        try:
            # Count temporary directories
            for temp_dir_name in self.temp_directories:
                temp_dir = self.project_root / temp_dir_name
                if temp_dir.exists():
                    size = sum(f.stat().st_size for f in temp_dir.rglob('*') if f.is_file())
                    stats["temp_directories"].append({
                        "path": str(temp_dir),
                        "size_bytes": size
                    })
                    stats["total_size_bytes"] += size
            
            # Count files matching patterns
            for pattern in self.temp_patterns:
                if not pattern.endswith('/'):
                    for item in self.project_root.rglob(pattern):
                        if item.is_file():
                            try:
                                size = item.stat().st_size
                                stats["temp_files"].append({
                                    "path": str(item),
                                    "size_bytes": size
                                })
                                stats["total_size_bytes"] += size
                            except OSError:
                                continue
                        
        except Exception as e:
            logger.error(f"Error getting temp stats: {e}")
            stats["error"] = str(e)
            
        return stats


# Global instance
temp_cleanup_manager = TempFileCleanupManager()


def cleanup_on_shutdown():
    """Function to be called on application shutdown"""
    try:
        logger.info("Initiating shutdown cleanup...")
        cleaned_count, errors = temp_cleanup_manager.cleanup_temp_files()
        
        if errors:
            logger.warning(f"Shutdown cleanup completed with {len(errors)} errors")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {error}")
            if len(errors) > 5:
                logger.warning(f"  ... and {len(errors) - 5} more errors")
        else:
            logger.info(f"Shutdown cleanup completed successfully: {cleaned_count} items cleaned")
            
        return cleaned_count, len(errors)
    except Exception as e:
        logger.error(f"Critical error during shutdown cleanup: {e}")
        return 0, 1