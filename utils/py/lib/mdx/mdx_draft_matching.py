#!/usr/bin/env python3
"""
Document Discovery Scanner

Provides utilities for discovering and pairing documentation files,
particularly for comparing generated vs live documentation.
"""

from pathlib import Path
from typing import List, Tuple, Optional
from ..utils.logging_utils import get_logger


class DocumentDiscoveryScanner:
    """Scanner for discovering and pairing documentation files."""
    
    def __init__(self, 
                 generated_docs_dir: Optional[Path] = None,
                 live_docs_dir: Optional[Path] = None):
        self.logger = get_logger("document-discovery-scanner")
        self.script_dir = Path(__file__).parent.parent.parent
        
        # Set up directories with sensible defaults
        self.generated_docs_dir = generated_docs_dir or (self.script_dir / "data" / "generated_docs")
        self.live_docs_dir = live_docs_dir or (self.script_dir.parent.parent / "src" / "pages" / "komodo-defi-framework" / "api")
    
    def find_corresponding_files(self) -> List[Tuple[Path, Path]]:
        """Find pairs of generated and live documentation files."""
        pairs = []
        
        if not self.generated_docs_dir.exists():
            self.logger.warning(f"Generated docs directory not found: {self.generated_docs_dir}")
            return pairs
        
        if not self.live_docs_dir.exists():
            self.logger.warning(f"Live docs directory not found: {self.live_docs_dir}")
            return pairs
        
        # Find all generated MDX files
        for generated_file in self.generated_docs_dir.rglob("*.mdx"):
            # Extract method path from generated file
            relative_path = generated_file.relative_to(self.generated_docs_dir)
            
            # Look for corresponding live file
            potential_live_paths = [
                self.live_docs_dir / relative_path,
                self.live_docs_dir / relative_path.with_name("index.mdx"),
                self.live_docs_dir / relative_path.parent / "index.mdx"
            ]
            
            for live_path in potential_live_paths:
                if live_path.exists():
                    pairs.append((generated_file, live_path))
                    break
            else:
                self.logger.debug(f"No corresponding live file found for {generated_file}")
        
        self.logger.info(f"Found {len(pairs)} file pairs for comparison")
        return pairs
    
    def find_generated_files(self, pattern: str = "*.mdx") -> List[Path]:
        """Find all generated files matching the pattern."""
        if not self.generated_docs_dir.exists():
            self.logger.warning(f"Generated docs directory not found: {self.generated_docs_dir}")
            return []
        
        files = list(self.generated_docs_dir.rglob(pattern))
        self.logger.info(f"Found {len(files)} generated files matching {pattern}")
        return files
    
    def find_live_files(self, pattern: str = "*.mdx") -> List[Path]:
        """Find all live files matching the pattern."""
        if not self.live_docs_dir.exists():
            self.logger.warning(f"Live docs directory not found: {self.live_docs_dir}")
            return []
        
        files = list(self.live_docs_dir.rglob(pattern))
        self.logger.info(f"Found {len(files)} live files matching {pattern}")
        return files
    
    def find_corresponding_file(self, source_file: Path, target_dir: Path) -> Optional[Path]:
        """Find the corresponding file for a source file in the target directory."""
        if source_file.parent == self.generated_docs_dir:
            # Source is generated, target should be live
            relative_path = source_file.relative_to(self.generated_docs_dir)
        elif source_file.parent == self.live_docs_dir:
            # Source is live, target should be generated
            relative_path = source_file.relative_to(self.live_docs_dir)
        else:
            self.logger.warning(f"Source file {source_file} is not in expected directories")
            return None
        
        # Look for corresponding file with various naming patterns
        potential_paths = [
            target_dir / relative_path,
            target_dir / relative_path.with_name("index.mdx"),
            target_dir / relative_path.parent / "index.mdx"
        ]
        
        for path in potential_paths:
            if path.exists():
                return path
        
        return None
    
    def get_file_statistics(self) -> dict:
        """Get statistics about discovered files."""
        generated_files = self.find_generated_files()
        live_files = self.find_live_files()
        file_pairs = self.find_corresponding_files()
        
        return {
            'generated_files_count': len(generated_files),
            'live_files_count': len(live_files),
            'paired_files_count': len(file_pairs),
            'unpaired_generated': len(generated_files) - len(file_pairs),
            'unpaired_live': len(live_files) - len(file_pairs),
            'generated_docs_dir': str(self.generated_docs_dir),
            'live_docs_dir': str(self.live_docs_dir)
        } 