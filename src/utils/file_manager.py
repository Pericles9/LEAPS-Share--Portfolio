"""
Portfolio File Management System

Comprehensive file management for organizing all generated files, reports, and analyses.
Provides version control, cleanup, and organization capabilities.
"""

import os
import shutil
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import glob
import zipfile
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class FileMetadata:
    """Metadata for tracked files."""
    filename: str
    filepath: str
    file_type: str
    category: str
    created_date: str
    size_bytes: int
    description: str
    tags: List[str]
    related_files: List[str]
    checksum: str


class PortfolioFileManager:
    """Manages all generated files in the portfolio system."""
    
    def __init__(self, base_dir: str = None):
        """Initialize the file manager."""
        if base_dir is None:
            base_dir = os.getcwd()
        
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "file_metadata.json"
        
        # Create organized directory structure
        self.directories = {
            'analyses': self.base_dir / 'analyses',
            'reports': self.base_dir / 'reports', 
            'data_exports': self.base_dir / 'data_exports',
            'visualizations': self.base_dir / 'visualizations',
            'portfolios': self.base_dir / 'portfolios',
            'temp': self.base_dir / 'temp',
            'archives': self.base_dir / 'archives'
        }
        
        # Create directories if they don't exist
        for directory in self.directories.values():
            directory.mkdir(exist_ok=True)
        
        # Load existing metadata
        self.metadata = self._load_metadata()
        
        # File type mappings
        self.file_categories = {
            '.csv': 'data_exports',
            '.xlsx': 'data_exports', 
            '.json': 'data_exports',
            '.png': 'visualizations',
            '.jpg': 'visualizations',
            '.pdf': 'reports',
            '.html': 'reports',
            '.txt': 'analyses',
            '.log': 'temp'
        }
        
        print(f"📁 Portfolio File Manager initialized")
        print(f"   Base directory: {self.base_dir}")
        print(f"   Organized directories: {len(self.directories)}")
    
    def _load_metadata(self) -> Dict:
        """Load file metadata from JSON."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save file metadata to JSON."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save metadata: {e}")
    
    def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return "unknown"
    
    def register_file(self, filepath: str, category: str = None, 
                     description: str = "", tags: List[str] = None,
                     related_files: List[str] = None) -> bool:
        """
        Register a file in the management system.
        
        Args:
            filepath: Path to the file
            category: File category (auto-detected if None)
            description: Description of the file
            tags: List of tags for the file
            related_files: List of related file paths
            
        Returns:
            True if successfully registered
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            return False
        
        # Auto-detect category if not provided
        if category is None:
            category = self.file_categories.get(filepath.suffix.lower(), 'analyses')
        
        # Create metadata
        metadata = FileMetadata(
            filename=filepath.name,
            filepath=str(filepath.absolute()),
            file_type=filepath.suffix.lower(),
            category=category,
            created_date=datetime.now().isoformat(),
            size_bytes=filepath.stat().st_size,
            description=description,
            tags=tags or [],
            related_files=related_files or [],
            checksum=self._calculate_checksum(filepath)
        )
        
        # Store metadata
        self.metadata[str(filepath.absolute())] = asdict(metadata)
        self._save_metadata()
        
        print(f"✓ Registered: {filepath.name} ({category})")
        return True
    
    def organize_files(self, move_files: bool = True) -> Dict[str, List[str]]:
        """
        Organize files into appropriate directories.
        
        Args:
            move_files: If True, move files. If False, just return organization plan.
            
        Returns:
            Dictionary of category -> list of files
        """
        print("📋 ORGANIZING FILES")
        print("-" * 40)
        
        organization_plan = {}
        
        # Find all relevant files in base directory
        patterns = [
            "*.csv", "*.xlsx", "*.json", "*.png", "*.jpg", 
            "*.pdf", "*.html", "*.txt", "*.log"
        ]
        
        all_files = []
        for pattern in patterns:
            all_files.extend(self.base_dir.glob(pattern))
        
        # Skip files already in organized directories
        files_to_organize = []
        for file_path in all_files:
            if not any(str(directory) in str(file_path.parent) for directory in self.directories.values()):
                files_to_organize.append(file_path)
        
        print(f"Found {len(files_to_organize)} files to organize")
        
        # Categorize files
        for file_path in files_to_organize:
            # Determine category based on filename patterns and extensions
            category = self._determine_file_category(file_path)
            
            if category not in organization_plan:
                organization_plan[category] = []
            organization_plan[category].append(str(file_path))
            
            if move_files:
                # Move file to appropriate directory
                target_dir = self.directories[category]
                target_path = target_dir / file_path.name
                
                # Handle name conflicts
                counter = 1
                original_target = target_path
                while target_path.exists():
                    stem = original_target.stem
                    suffix = original_target.suffix
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                try:
                    shutil.move(str(file_path), str(target_path))
                    print(f"  ✓ Moved {file_path.name} → {category}/")
                    
                    # Register the moved file
                    self.register_file(
                        target_path,
                        category=category,
                        description=f"Auto-organized from base directory"
                    )
                    
                except Exception as e:
                    print(f"  ❌ Error moving {file_path.name}: {e}")
        
        return organization_plan
    
    def _determine_file_category(self, file_path: Path) -> str:
        """Determine the appropriate category for a file."""
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Specific filename patterns
        if any(pattern in filename for pattern in [
            'stock_selection', 'etf_holdings', 'universe', 'allocation'
        ]):
            return 'data_exports'
        
        if any(pattern in filename for pattern in [
            'portfolio', 'strategy', 'optimization', 'monte_carlo'
        ]):
            return 'portfolios'
        
        if any(pattern in filename for pattern in [
            'analysis', 'breakdown', 'report'
        ]):
            return 'analyses'
        
        if any(pattern in filename for pattern in [
            'chart', 'plot', 'visualization'
        ]):
            return 'visualizations'
        
        # Default based on extension
        return self.file_categories.get(extension, 'analyses')
    
    def create_session_report(self, session_name: str = None) -> str:
        """Create a comprehensive report of the current session's files."""
        
        if session_name is None:
            session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report_path = self.directories['reports'] / f"{session_name}_report.html"
        
        # Get recent files (last 24 hours)
        recent_files = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for filepath, metadata in self.metadata.items():
            try:
                created_date = datetime.fromisoformat(metadata['created_date'])
                if created_date > cutoff_time:
                    recent_files.append(metadata)
            except:
                continue
        
        # Sort by creation date
        recent_files.sort(key=lambda x: x['created_date'], reverse=True)
        
        # Generate HTML report
        html_content = self._generate_html_report(session_name, recent_files)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✓ Created session report: {report_path}")
        return str(report_path)
    
    def _generate_html_report(self, session_name: str, files: List[Dict]) -> str:
        """Generate HTML report content."""
        
        total_files = len(files)
        total_size = sum(f.get('size_bytes', 0) for f in files)
        
        # Group by category
        by_category = {}
        for file_meta in files:
            category = file_meta.get('category', 'unknown')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(file_meta)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Session Report - {session_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat {{ text-align: center; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
                .category {{ margin: 20px 0; }}
                .file-list {{ background-color: #f9f9f9; padding: 10px; border-radius: 5px; }}
                .file-item {{ margin: 5px 0; padding: 5px; border-left: 3px solid #007acc; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Portfolio Session Report</h1>
                <h2>{session_name}</h2>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="stat">
                    <h3>{total_files}</h3>
                    <p>Files Created</p>
                </div>
                <div class="stat">
                    <h3>{len(by_category)}</h3>
                    <p>Categories</p>
                </div>
                <div class="stat">
                    <h3>{total_size / 1024:.1f} KB</h3>
                    <p>Total Size</p>
                </div>
            </div>
            
            <h2>📁 Files by Category</h2>
        """
        
        for category, category_files in by_category.items():
            html += f"""
            <div class="category">
                <h3>🗂️ {category.replace('_', ' ').title()} ({len(category_files)} files)</h3>
                <div class="file-list">
                    <table>
                        <tr>
                            <th>Filename</th>
                            <th>Description</th>
                            <th>Size</th>
                            <th>Created</th>
                        </tr>
            """
            
            for file_meta in category_files:
                created = datetime.fromisoformat(file_meta['created_date']).strftime('%H:%M:%S')
                size_kb = file_meta.get('size_bytes', 0) / 1024
                
                html += f"""
                        <tr>
                            <td><strong>{file_meta['filename']}</strong></td>
                            <td>{file_meta.get('description', 'No description')}</td>
                            <td>{size_kb:.1f} KB</td>
                            <td>{created}</td>
                        </tr>
                """
            
            html += """
                    </table>
                </div>
            </div>
            """
        
        html += """
            <h2>💡 Quick Actions</h2>
            <ul>
                <li>📈 View latest portfolio analysis in <code>analyses/</code></li>
                <li>📊 Check visualization files in <code>visualizations/</code></li>
                <li>💾 Export data files in <code>data_exports/</code></li>
                <li>📁 Archive old files using the file manager</li>
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def cleanup_old_files(self, days_old: int = 7, dry_run: bool = True) -> List[str]:
        """
        Clean up old files.
        
        Args:
            days_old: Files older than this many days
            dry_run: If True, just show what would be deleted
            
        Returns:
            List of files that were (or would be) deleted
        """
        print(f"🧹 CLEANUP: Files older than {days_old} days")
        print("-" * 40)
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        files_to_delete = []
        
        for filepath, metadata in self.metadata.items():
            try:
                created_date = datetime.fromisoformat(metadata['created_date'])
                if created_date < cutoff_date:
                    files_to_delete.append(filepath)
            except:
                continue
        
        if dry_run:
            print(f"Would delete {len(files_to_delete)} files:")
            for filepath in files_to_delete:
                print(f"  - {Path(filepath).name}")
        else:
            deleted_count = 0
            for filepath in files_to_delete:
                try:
                    if Path(filepath).exists():
                        Path(filepath).unlink()
                        deleted_count += 1
                    # Remove from metadata
                    del self.metadata[filepath]
                except Exception as e:
                    print(f"  ❌ Error deleting {filepath}: {e}")
            
            self._save_metadata()
            print(f"✓ Deleted {deleted_count} files")
        
        return files_to_delete
    
    def archive_session(self, session_name: str = None, 
                       include_patterns: List[str] = None) -> str:
        """
        Archive files into a ZIP file.
        
        Args:
            session_name: Name for the archive
            include_patterns: File patterns to include
            
        Returns:
            Path to created archive
        """
        if session_name is None:
            session_name = f"portfolio_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if include_patterns is None:
            include_patterns = ["*.csv", "*.png", "*.html", "*.json"]
        
        archive_path = self.directories['archives'] / f"{session_name}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_added = 0
            
            # Add files from organized directories
            for dir_name, directory in self.directories.items():
                if dir_name in ['temp', 'archives']:
                    continue
                
                for pattern in include_patterns:
                    for file_path in directory.glob(pattern):
                        arcname = f"{dir_name}/{file_path.name}"
                        zipf.write(file_path, arcname)
                        files_added += 1
        
        print(f"✓ Created archive: {archive_path} ({files_added} files)")
        return str(archive_path)
    
    def get_file_summary(self) -> Dict:
        """Get summary of all managed files."""
        summary = {
            'total_files': len(self.metadata),
            'by_category': {},
            'by_type': {},
            'total_size': 0,
            'recent_files': 0
        }
        
        recent_cutoff = datetime.now() - timedelta(hours=24)
        
        for filepath, metadata in self.metadata.items():
            # By category
            category = metadata.get('category', 'unknown')
            if category not in summary['by_category']:
                summary['by_category'][category] = 0
            summary['by_category'][category] += 1
            
            # By type
            file_type = metadata.get('file_type', 'unknown')
            if file_type not in summary['by_type']:
                summary['by_type'][file_type] = 0
            summary['by_type'][file_type] += 1
            
            # Size
            summary['total_size'] += metadata.get('size_bytes', 0)
            
            # Recent files
            try:
                created_date = datetime.fromisoformat(metadata['created_date'])
                if created_date > recent_cutoff:
                    summary['recent_files'] += 1
            except:
                pass
        
        return summary
    
    def print_status(self):
        """Print current file management status."""
        summary = self.get_file_summary()
        
        print("\n📁 PORTFOLIO FILE MANAGER STATUS")
        print("=" * 50)
        
        print(f"📊 Overview:")
        print(f"  • Total files tracked: {summary['total_files']}")
        print(f"  • Total size: {summary['total_size'] / 1024:.1f} KB")
        print(f"  • Files created today: {summary['recent_files']}")
        
        print(f"\n📂 By Category:")
        for category, count in summary['by_category'].items():
            print(f"  • {category.replace('_', ' ').title()}: {count} files")
        
        print(f"\n🗂️ By Type:")
        for file_type, count in summary['by_type'].items():
            print(f"  • {file_type.upper()}: {count} files")
        
        print(f"\n📁 Directory Structure:")
        for name, directory in self.directories.items():
            if directory.exists():
                file_count = len(list(directory.glob("*")))
                print(f"  • {name}/: {file_count} files")


def main():
    """Demo the file management system."""
    
    # Initialize file manager
    manager = PortfolioFileManager()
    
    # Show current status
    manager.print_status()
    
    # Organize existing files
    print(f"\n🔄 ORGANIZING FILES")
    print("=" * 50)
    organization_plan = manager.organize_files(move_files=True)
    
    # Show organization results
    for category, files in organization_plan.items():
        print(f"  {category}: {len(files)} files organized")
    
    # Create session report
    print(f"\n📋 CREATING SESSION REPORT")
    print("=" * 50)
    report_path = manager.create_session_report()
    
    # Show final status
    manager.print_status()
    
    print(f"\n✅ FILE MANAGEMENT COMPLETE!")
    print(f"📄 Session report: {report_path}")


if __name__ == "__main__":
    main()