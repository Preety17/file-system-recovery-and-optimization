import os
import time
import random
import json
import shutil
import copy
from datetime import datetime
import hashlib
from typing import Dict, List, Tuple, Optional, Any

class FileSystemManager:
    """Main class for file system management, recovery, and optimization."""
    
    def __init__(self, root_dir: str, metadata_file: str = "fs_metadata.json"):
        """
        Initialize the file system manager.
    
        Args:
            root_dir: Root directory for the file system
            metadata_file: File to store metadata information
        """
        self.root_dir = os.path.abspath(root_dir)
        self.metadata_file = os.path.join(self.root_dir, metadata_file)
        self.block_size = 4096  # Default block size (4KB)
        self.free_blocks = []
        self.file_table = {}
        self.directory_structure = {}
        self.backup_dir = os.path.join(self.root_dir, ".backups")
    
    # Cache initialization
        self.read_cache = {}  # Cache for read operations
        self.cache_max_size = 100  # Default max cache size
        self.cache_ttl = 300  # Default TTL in seconds
        self.cache_timestamps = {}  # To track when entries were added
    
    # Create necessary directories if they don't exist
        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    # Load or initialize the file system metadata
        self._load_metadata()
    
    def _check_cache_expiration(self) -> None:
        """Remove expired cache entries based on TTL."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items() 
            if current_time - timestamp > self.cache_ttl
        ]
    
        for key in expired_keys:
            if key in self.read_cache:
                del self.read_cache[key]
            del self.cache_timestamps[key]

    def _add_to_cache(self, path: str, content: str) -> None:
        """Add content to cache with expiration management."""
    # Enforce cache size limit
        if len(self.read_cache) >= self.cache_max_size:
        # Remove oldest entry
            if self.cache_timestamps:
                oldest_key = min(self.cache_timestamps, key=self.cache_timestamps.get)
                if oldest_key in self.read_cache:
                    del self.read_cache[oldest_key]
                del self.cache_timestamps[oldest_key]
    
        self.read_cache[path] = content
        self.cache_timestamps[path] = time.time()
    
    def _load_metadata(self) -> None:
        """Load metadata from disk or initialize if not found."""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.block_size = data.get('block_size', 4096)
                    self.free_blocks = data.get('free_blocks', [])
                    self.file_table = data.get('file_table', {})
                    self.directory_structure = data.get('directory_structure', {})
            else:
                # Initialize a new file system
                self._initialize_file_system()
        except Exception as e:
            print(f"Error loading metadata: {e}")
            # Attempt recovery if metadata is corrupted
            self._recover_metadata()
    
    def _save_metadata(self) -> None:
        """Save current metadata to disk."""
        try:
            # Create a backup of the current metadata first
            if os.path.exists(self.metadata_file):
                backup_path = os.path.join(
                    self.backup_dir, 
                    f"metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                shutil.copy2(self.metadata_file, backup_path)
            
            # Save the current metadata
            with open(self.metadata_file, 'w') as f:
                json.dump({
                    'block_size': self.block_size,
                    'free_blocks': self.free_blocks,
                    'file_table': self.file_table,
                    'directory_structure': self.directory_structure,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def _initialize_file_system(self) -> None:
        """Initialize a new file system structure."""
        # Set up initial free blocks (simulated)
        self.free_blocks = list(range(1, 1001))  # 1000 free blocks
        
        # Initialize root directory
        self.directory_structure = {
            '/': {
                'type': 'directory',
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'contents': {}
            }
        }
        
        self.file_table = {}
        self._save_metadata()
        print("Initialized new file system")
    
    def _recover_metadata(self) -> None:
        """Attempt to recover metadata from backups or by scanning the file system."""
        # First try to restore from the most recent backup
        backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith("metadata_backup_")]
        
        if backup_files:
            # Sort by timestamp to get the most recent
            latest_backup = sorted(backup_files)[-1]
            backup_path = os.path.join(self.backup_dir, latest_backup)
            
            try:
                with open(backup_path, 'r') as f:
                    data = json.load(f)
                    self.block_size = data.get('block_size', 4096)
                    self.free_blocks = data.get('free_blocks', [])
                    self.file_table = data.get('file_table', {})
                    self.directory_structure = data.get('directory_structure', {})
                print(f"Recovered metadata from backup: {latest_backup}")
                return
            except Exception as e:
                print(f"Failed to recover from backup: {e}")
        
        # If no backups or backup restoration failed, scan the file system
        print("Performing file system scan for recovery...")
        self._initialize_file_system()  # Start with a clean slate
        
        # Scan the physical directory structure to rebuild metadata
        self._scan_directory(self.root_dir, '/')
        self._save_metadata()
        print("File system recovery completed")
    
    def _scan_directory(self, physical_path: str, virtual_path: str) -> None:
        """
        Scan a directory to rebuild metadata.
        
        Args:
            physical_path: Actual path on disk
            virtual_path: Path in our virtual file system
        """
        try:
            for item in os.listdir(physical_path):
                # Skip metadata and backup files
                if item == os.path.basename(self.metadata_file) or item == os.path.basename(self.backup_dir):
                    continue
                
                item_physical_path = os.path.join(physical_path, item)
                item_virtual_path = os.path.join(virtual_path, item).replace('\\', '/')
                
                if os.path.isdir(item_physical_path):
                    # Add directory to structure
                    self.directory_structure[item_virtual_path] = {
                        'type': 'directory',
                        'created': datetime.fromtimestamp(os.path.getctime(item_physical_path)).isoformat(),
                        'modified': datetime.fromtimestamp(os.path.getmtime(item_physical_path)).isoformat(),
                        'contents': {}
                    }
                    
                    # Recursively scan subdirectories
                    self._scan_directory(item_physical_path, item_virtual_path)
                else:
                    # Add file to structure
                    file_size = os.path.getsize(item_physical_path)
                    file_id = hashlib.md5(item_virtual_path.encode()).hexdigest()
                    
                    # Calculate required blocks
                    blocks_needed = (file_size + self.block_size - 1) // self.block_size
                    allocated_blocks = self._allocate_blocks(blocks_needed)
                    
                    # Add to file table
                    self.file_table[file_id] = {
                        'path': item_virtual_path,
                        'size': file_size,
                        'blocks': allocated_blocks,
                        'created': datetime.fromtimestamp(os.path.getctime(item_physical_path)).isoformat(),
                        'modified': datetime.fromtimestamp(os.path.getmtime(item_physical_path)).isoformat(),
                        'checksum': self._calculate_checksum(item_physical_path)
                    }
                    
                    # Add to directory structure
                    parent_dir = os.path.dirname(item_virtual_path).replace('\\', '/')
                    if parent_dir not in self.directory_structure:
                        self.directory_structure[parent_dir] = {
                            'type': 'directory',
                            'created': datetime.now().isoformat(),
                            'modified': datetime.now().isoformat(),
                            'contents': {}
                        }
                    
                    self.directory_structure[parent_dir]['contents'][item] = {
                        'type': 'file',
                        'file_id': file_id
                    }
        except Exception as e:
            print(f"Error scanning directory {physical_path}: {e}")
    
    def _allocate_blocks(self, num_blocks: int) -> List[int]:
        """
        Allocate the specified number of blocks from free space.
        
        Args:
            num_blocks: Number of blocks to allocate
            
        Returns:
            List of allocated block IDs
        """
        if len(self.free_blocks) < num_blocks:
            # Expand free space if needed
            current_max = max(self.free_blocks) if self.free_blocks else 0
            new_blocks = list(range(current_max + 1, current_max + 1 + num_blocks))
            self.free_blocks.extend(new_blocks)
        
        # Allocate blocks
        allocated = self.free_blocks[:num_blocks]
        self.free_blocks = self.free_blocks[num_blocks:]
        return allocated
    
    def _free_blocks(self, blocks: List[int]) -> None:
        """
        Return blocks to the free list.
        
        Args:
            blocks: List of block IDs to free
        """
        self.free_blocks.extend(blocks)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """
        Calculate MD5 checksum for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 checksum as a hex string
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                buf = f.read(65536)  # Read in 64k chunks
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error calculating checksum for {file_path}: {e}")
            return ""
    
    # File Operations
    def create_file(self, path: str, content: str = "") -> bool:
        """
        Create a new file in the file system.
        
        Args:
            path: Path to the new file
            content: Initial content for the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            
            # Check if parent directory exists
            parent_dir = os.path.dirname(path)
            if parent_dir not in self.directory_structure:
                print(f"Parent directory {parent_dir} does not exist")
                return False
            
            # Check if file already exists
            file_name = os.path.basename(path)
            if file_name in self.directory_structure[parent_dir]['contents']:
                print(f"File {path} already exists")
                return False
            
            # Create physical file
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
            os.makedirs(os.path.dirname(physical_path), exist_ok=True)
            
            with open(physical_path, 'w') as f:
                f.write(content)
            
            # Update metadata
            file_size = len(content.encode())
            blocks_needed = (file_size + self.block_size - 1) // self.block_size
            allocated_blocks = self._allocate_blocks(blocks_needed)
            
            file_id = hashlib.md5(path.encode()).hexdigest()
            
            # Add to file table
            self.file_table[file_id] = {
                'path': path,
                'size': file_size,
                'blocks': allocated_blocks,
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(physical_path)
            }
            
            # Add to directory structure
            self.directory_structure[parent_dir]['contents'][file_name] = {
                'type': 'file',
                'file_id': file_id
            }
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error creating file {path}: {e}")
            return False
    
    def read_file(self, path: str) -> Optional[str]:
        """
        Read a file from the file system.
    
        Args:
            path: Path to the file
        
        Returns:
            File content as string or None if file doesn't exist
        """
        try:
        # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            
        # Check cache expiration
            self._check_cache_expiration()
        
        # Return from cache if available
            if path in self.read_cache:
                return self.read_cache[path]
        
        # Find file in directory structure
            parent_dir = os.path.dirname(path)
            file_name = os.path.basename(path)
        
            if parent_dir not in self.directory_structure:
                print(f"Directory {parent_dir} does not exist")
                return None
        
            if file_name not in self.directory_structure[parent_dir]['contents']:
                print(f"File {path} does not exist")
                return None
        
            file_entry = self.directory_structure[parent_dir]['contents'][file_name]
            if file_entry['type'] != 'file':
                print(f"{path} is not a file")
                return None
        
        # Read physical file
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
        
        # Verify file integrity
            file_id = file_entry['file_id']
            current_checksum = self._calculate_checksum(physical_path)
            stored_checksum = self.file_table[file_id]['checksum']
        
            if current_checksum != stored_checksum:
                print(f"Warning: File {path} may be corrupted (checksum mismatch)")
            # Attempt recovery
                if not self._recover_file(file_id, physical_path):
                    print(f"Could not recover file {path}")
        
            with open(physical_path, 'r') as f:
                content = f.read()
            # Add to cache
                self._add_to_cache(path, content)
                return content
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return None
    
    def write_file(self, path: str, content: str) -> bool:
        """
        Write content to a file, creating it if it doesn't exist.
    
        Args:
            path: Path to the file
            content: Content to write
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
        
        # Invalidate cache for this path
            self._invalidate_cache(path)
        
        # Check if file exists
            parent_dir = os.path.dirname(path)
            file_name = os.path.basename(path)
        
            if parent_dir not in self.directory_structure:
            # Create parent directory if it doesn't exist
                self.create_directory(parent_dir)
        
            file_exists = (file_name in self.directory_structure[parent_dir]['contents'])
        
            if file_exists:
            # Update existing file
                file_entry = self.directory_structure[parent_dir]['contents'][file_name]
                file_id = file_entry['file_id']
            
            # Free old blocks
                old_blocks = self.file_table[file_id]['blocks']
                self._free_blocks(old_blocks)
            
            # Create backup before writing
                physical_path = os.path.join(self.root_dir, path.lstrip('/'))
                self._backup_file(physical_path)
            else:
            # Create new file
                return self.create_file(path, content)
        
        # Write to physical file
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
            with open(physical_path, 'w') as f:
                f.write(content)
        
        # Update metadata
            file_size = len(content.encode())
            blocks_needed = (file_size + self.block_size - 1) // self.block_size
            allocated_blocks = self._allocate_blocks(blocks_needed)
        
            if file_exists:
                file_id = self.directory_structure[parent_dir]['contents'][file_name]['file_id']
                self.file_table[file_id].update({
                    'size': file_size,
                    'blocks': allocated_blocks,
                    'modified': datetime.now().isoformat(),
                    'checksum': self._calculate_checksum(physical_path)
                })
        
        # Add to cache after write
            self._add_to_cache(path, content)
        
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error writing to file {path}: {e}")
            return False
    
    
    def _invalidate_cache(self, path: str = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            path: Specific path to invalidate, or None to invalidate all
        """
        if path is None:
            self.read_cache.clear()
        else:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            
            if path in self.read_cache:
                del self.read_cache[path]

    def configure_cache(self, max_size: int = 100, ttl: int = 300) -> None:
        """
        Configure cache settings.
        
        Args:
            max_size: Maximum number of entries in cache
            ttl: Time to live for cache entries in seconds
        """
        self.cache_max_size = max_size
        self.cache_ttl = ttl
        self.cache_timestamps = {}  # To track when entries were added
    
        # Trim cache if it's already larger than the new max size
        if len(self.read_cache) > self.cache_max_size:
            items_to_remove = len(self.read_cache) - self.cache_max_size
            for _ in range(items_to_remove):
                if self.read_cache:
                    self.read_cache.pop(next(iter(self.read_cache)))    
    
    def delete_file(self, path: str) -> bool:
        """
        Delete a file from the file system.
        
        Args:
            path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            
            # Find file in directory structure
            parent_dir = os.path.dirname(path)
            file_name = os.path.basename(path)
            
            if parent_dir not in self.directory_structure:
                print(f"Directory {parent_dir} does not exist")
                return False
            
            if file_name not in self.directory_structure[parent_dir]['contents']:
                print(f"File {path} does not exist")
                return False
            
            file_entry = self.directory_structure[parent_dir]['contents'][file_name]
            if file_entry['type'] != 'file':
                print(f"{path} is not a file")
                return False
            
            # Backup file before deletion
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
            self._backup_file(physical_path)
            
            # Free blocks
            file_id = file_entry['file_id']
            self._free_blocks(self.file_table[file_id]['blocks'])
            
            # Remove from file table
            del self.file_table[file_id]
            
            # Remove from directory structure
            del self.directory_structure[parent_dir]['contents'][file_name]
            
            # Delete physical file
            if os.path.exists(physical_path):
                os.remove(physical_path)
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error deleting file {path}: {e}")
            return False
    
    # Directory Operations
    def create_directory(self, path: str) -> bool:
        """
        Create a new directory in the file system.
        
        Args:
            path: Path to the new directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            
            # Check if directory already exists
            if path in self.directory_structure:
                print(f"Directory {path} already exists")
                return False
            
            # Check if parent directory exists
            parent_dir = os.path.dirname(path)
            if parent_dir and parent_dir not in self.directory_structure:
                # Create parent directory recursively
                if not self.create_directory(parent_dir):
                    return False
            
            # Create physical directory
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
            os.makedirs(physical_path, exist_ok=True)
            
            # Update directory structure
            self.directory_structure[path] = {
                'type': 'directory',
                'created': datetime.now().isoformat(),
                'modified': datetime.now().isoformat(),
                'contents': {}
            }
            
            # Add to parent directory
            if path != '/':
                dir_name = os.path.basename(path)
                self.directory_structure[parent_dir]['contents'][dir_name] = {
                    'type': 'directory',
                    'path': path
                }
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False
    
    def list_directory(self, path: str) -> Optional[Dict[str, Any]]:
        """
        List the contents of a directory.
        
        Args:
            path: Path to the directory
            
        Returns:
            Dictionary with directory contents or None if directory doesn't exist
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            if path != '/' and path.endswith('/'):
                path = path[:-1]
            
            # Check if directory exists
            if path not in self.directory_structure:
                print(f"Directory {path} does not exist")
                return None
            
            dir_entry = self.directory_structure[path]
            if dir_entry['type'] != 'directory':
                print(f"{path} is not a directory")
                return None
            
            # Prepare result
            result = {
                'name': os.path.basename(path) or '/',
                'path': path,
                'created': dir_entry['created'],
                'modified': dir_entry['modified'],
                'contents': {}
            }
            
            # Add directory contents
            for name, entry in dir_entry['contents'].items():
                if entry['type'] == 'file':
                    file_id = entry['file_id']
                    file_info = self.file_table[file_id]
                    result['contents'][name] = {
                        'type': 'file',
                        'size': file_info['size'],
                        'created': file_info['created'],
                        'modified': file_info['modified']
                    }
                else:  # Directory
                    subdir_path = entry['path']
                    subdir_info = self.directory_structure[subdir_path]
                    result['contents'][name] = {
                        'type': 'directory',
                        'created': subdir_info['created'],
                        'modified': subdir_info['modified'],
                        'item_count': len(subdir_info['contents'])
                    }
            
            return result
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            return None
    
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """
        Delete a directory from the file system.
        
        Args:
            path: Path to the directory
            recursive: If True, delete all contents recursively
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize path
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            if path == '/':
                print("Cannot delete root directory")
                return False
            
            # Check if directory exists
            if path not in self.directory_structure:
                print(f"Directory {path} does not exist")
                return False
            
            dir_entry = self.directory_structure[path]
            if dir_entry['type'] != 'directory':
                print(f"{path} is not a directory")
                return False
            
            # Check if directory is empty or recursive flag is set
            if dir_entry['contents'] and not recursive:
                print(f"Directory {path} is not empty. Use recursive=True to delete")
                return False
            
            # Delete contents recursively if needed
            if recursive:
                for name, entry in list(dir_entry['contents'].items()):
                    if entry['type'] == 'file':
                        file_path = os.path.join(path, name)
                        self.delete_file(file_path)
                    else:  # Directory
                        subdir_path = entry['path']
                        self.delete_directory(subdir_path, recursive=True)
            
            # Remove from parent directory
            parent_dir = os.path.dirname(path)
            dir_name = os.path.basename(path)
            if dir_name in self.directory_structure[parent_dir]['contents']:
                del self.directory_structure[parent_dir]['contents'][dir_name]
            
            # Remove directory entry
            del self.directory_structure[path]
            
            # Delete physical directory
            physical_path = os.path.join(self.root_dir, path.lstrip('/'))
            if os.path.exists(physical_path):
                try:
                    os.rmdir(physical_path)  # Will only work if directory is empty
                except OSError:
                    if recursive:
                        shutil.rmtree(physical_path)
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error deleting directory {path}: {e}")
            return False
    
    # Backup and Recovery
    def _backup_file(self, file_path: str) -> bool:
        """
        Create a backup of a file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Create backup filename
            rel_path = os.path.relpath(file_path, self.root_dir)
            backup_filename = f"{rel_path.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Copy file to backup
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"Error backing up file {file_path}: {e}")
            return False
    
    def _recover_file(self, file_id: str, physical_path: str) -> bool:
        """
        Attempt to recover a corrupted file.
        
        Args:
            file_id: ID of the file in the file table
            physical_path: Physical path to the file
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            # Check if file exists in file table
            if file_id not in self.file_table:
                return False
            
            # Get relative path for finding backups
            rel_path = os.path.relpath(physical_path, self.root_dir)
            backup_prefix = f"{rel_path.replace('/', '_')}_"
            
            # Find all backups for this file
            backups = [f for f in os.listdir(self.backup_dir) if f.startswith(backup_prefix)]
            
            if not backups:
                print(f"No backups found for {physical_path}")
                return False
            
            # Sort backups by timestamp (newest first)
            backups.sort(reverse=True)
            
            # Try each backup until we find one with matching checksum
            for backup in backups:
                backup_path = os.path.join(self.backup_dir, backup)
                backup_checksum = self._calculate_checksum(backup_path)
                
                if backup_checksum == self.file_table[file_id]['checksum']:
                    # Found a valid backup, restore it
                    shutil.copy2(backup_path, physical_path)
                    print(f"Successfully recovered {physical_path} from backup")
                    return True
            
            # If we get here, no valid backup was found
            print(f"No valid backup found for {physical_path}")
            return False
        except Exception as e:
            print(f"Error recovering file {physical_path}: {e}")
            return False
    
    # Optimization
    def defragment(self) -> bool:
        """
        Defragment the file system to optimize block allocation.
    
        Returns:
            True if successful, False otherwise
        """
        try:
            print("Starting file system defragmentation...")
        
            # Take backup of current metadata
            backup_file_table = copy.deepcopy(self.file_table)
        
            # Sort free blocks
            self.free_blocks.sort()
        
        # Get total block count
            total_blocks = sum(len(info['blocks']) for info in self.file_table.values()) + len(self.free_blocks)
        
        # Reset all blocks
            self.free_blocks = list(range(1, total_blocks + 1))
        
        # Re-allocate blocks in optimal order
        # Sort files by path for consistent ordering
            sorted_files = sorted(self.file_table.items(), key=lambda x: x[1]['path'])
        
            for file_id, file_info in sorted_files:
                file_size = file_info['size']
                blocks_needed = (file_size + self.block_size - 1) // self.block_size
            
            # Allocate new contiguous blocks
                new_blocks = self._allocate_blocks(blocks_needed)
                self.file_table[file_id]['blocks'] = new_blocks
        
            self._save_metadata()
            print(f"Defragmentation completed successfully. {len(self.free_blocks)} free blocks available.")
            return True
        except Exception as e:
            print(f"Error during defragmentation: {e}")
        # Restore from backup on error
            self.file_table = backup_file_table
            return False
    
    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze file system performance and provide statistics.
    
        This method evaluates various metrics including fragmentation level,
        read/write speeds, and block allocation efficiency.
    
        Returns
        -------
        Dict[str, Any]
            A dictionary containing performance metrics:
            - total_files: Number of files in the system
            - total_directories: Number of directories
            - used_blocks: Count of allocated blocks
            - free_blocks: Count of available blocks
            - total_blocks: Total block count
            - average_fragmentation: Measure of file fragmentation (0-1)
            - average_read_time: Average time in seconds to read a file
            - average_write_time: Average time in seconds to write a file
    
        Examples
        --------
        >>> fs = FileSystemManager("test_fs")
        >>> stats = fs.analyze_performance()
        >>> print(f"Fragmentation level: {stats['average_fragmentation']:.2f}")
        """
        try:
            total_files = len(self.file_table)
            total_dirs = len(self.directory_structure)

            used_blocks = sum(len(info['blocks']) for info in self.file_table.values())
            free_blocks = len(self.free_blocks)
            total_blocks = used_blocks + free_blocks

            fragmentation = 0
            for file_info in self.file_table.values():
                blocks = file_info['blocks']
                discontinuities = sum(1 for i in range(len(blocks) - 1) if blocks[i+1] != blocks[i] + 1)
                fragmentation += (discontinuities / (len(blocks) - 1)) if len(blocks) > 1 else 0

            avg_fragmentation = fragmentation / total_files if total_files > 0 else 0

            read_times = []
            write_times = []

            test_files = list(self.file_table.keys())
            if test_files:
                for _ in range(min(5, len(test_files))):
                    file_id = random.choice(test_files)
                    path = self.file_table[file_id]['path']
                    physical_path = os.path.join(self.root_dir, path.lstrip('/'))
                    dummy_content = 'x' * self.file_table[file_id]['size']

                    start = time.time()
                    self.write_file(path, dummy_content)
                    write_times.append(time.time() - start)

                    start = time.time()
                    self.read_file(path)
                    read_times.append(time.time() - start)

            return {
                'total_files': total_files,
                'total_directories': total_dirs,
                'used_blocks': used_blocks,
                'free_blocks': free_blocks,
                'total_blocks': total_blocks,
                'average_fragmentation': avg_fragmentation,
                'average_read_time': sum(read_times)/len(read_times) if read_times else 0,
                'average_write_time': sum(write_times)/len(write_times) if write_times else 0,
            }

        except Exception as e:
            print(f"Error analyzing performance: {e}")
            return {}
        
    def simulate_disk_crash(self, corruption_type: str = "metadata") -> None:
        """
        Simulate a disk crash by corrupting metadata or files.

        Args:
            corruption_type: "metadata" or "files"
        """
        print(f"Simulating {corruption_type} corruption...")

        if corruption_type == "metadata":
            with open(self.metadata_file, 'w') as f:
                f.write("{{{Invalid JSON!!")
            print("Metadata corrupted.")
        elif corruption_type == "files":
            file_ids = list(self.file_table.keys())
            for file_id in random.sample(file_ids, min(3, len(file_ids))):
                file_path = self.file_table[file_id]['path']
                physical_path = os.path.join(self.root_dir, file_path.lstrip('/'))
                with open(physical_path, 'w') as f:
                    f.write("CORRUPTED DATA!!!")
                print(f"Corrupted {file_path}")
        else:
            print("Unknown corruption type.")

def __init__(self, root_dir: str, metadata_file: str = "fs_metadata.json"):
    """
    Initialize the file system manager.
    
    Args:
        root_dir: Root directory for the file system
        metadata_file: File to store metadata information
    """
    self.root_dir = os.path.abspath(root_dir)
    self.metadata_file = os.path.join(self.root_dir, metadata_file)
    self.block_size = 4096  # Default block size (4KB)
    self.free_blocks = []
    self.file_table = {}
    self.directory_structure = {}
    self.backup_dir = os.path.join(self.root_dir, ".backups")
    self.read_cache = {}  # Cache for read operations
    
    # Create necessary directories if they don't exist
    os.makedirs(self.root_dir, exist_ok=True)
    os.makedirs(self.backup_dir, exist_ok=True)
    
    # Load or initialize the file system metadata
    self._load_metadata()

def read_file(self, path: str) -> Optional[str]:
    """
    Read a file from the file system.
    
    Args:
        path: Path to the file
        
    Returns:
        File content as string or None if file doesn't exist
    """
    try:
        # Return from cache if available
        if path in self.read_cache:
            return self.read_cache[path]
            
        # Normalize path
        path = path.replace('\\', '/')
        if not path.startswith('/'):
            path = '/' + path
        
        # Find file in directory structure
        parent_dir = os.path.dirname(path)
        file_name = os.path.basename(path)
        
        if parent_dir not in self.directory_structure:
            print(f"Directory {parent_dir} does not exist")
            return None
        
        if file_name not in self.directory_structure[parent_dir]['contents']:
            print(f"File {path} does not exist")
            return None
        
        file_entry = self.directory_structure[parent_dir]['contents'][file_name]
        if file_entry['type'] != 'file':
            print(f"{path} is not a file")
            return None
        
        # Read physical file
        physical_path = os.path.join(self.root_dir, path.lstrip('/'))
        
        # Verify file integrity
        file_id = file_entry['file_id']
        current_checksum = self._calculate_checksum(physical_path)
        stored_checksum = self.file_table[file_id]['checksum']
        
        if current_checksum != stored_checksum:
            print(f"Warning: File {path} may be corrupted (checksum mismatch)")
            # Attempt recovery
            if not self._recover_file(file_id, physical_path):
                print(f"Could not recover file {path}")
        
        with open(physical_path, 'r') as f:
            content = f.read()
            self.read_cache[path] = content
            return content
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        return None

class FileSystemError(Exception):
    """Base exception for FileSystemManager errors."""
    pass

class FileNotFoundError(FileSystemError):
    """Raised when a file is not found."""
    pass

class DirectoryNotFoundError(FileSystemError):
    """Raised when a directory is not found."""
    pass

class CorruptionError(FileSystemError):
    """Raised when file corruption is detected."""
    pass   

def main():
    fs = FileSystemManager("virtual_fs")
    fs.create_directory("/docs")
    fs.create_file("/docs/readme.txt", "Welcome to the FS tool.")
    print(fs.read_file("/docs/readme.txt"))
    fs.simulate_disk_crash("files")
    fs.read_file("/docs/readme.txt")
    print("Performance:", fs.analyze_performance())

if __name__ == "__main__":
    main()