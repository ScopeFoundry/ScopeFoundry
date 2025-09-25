from pathlib import Path
import configparser
import subprocess

def get_git_info(repo_path=None):
    """Get git info using git commands, fallback to manual parsing if subprocess fails"""
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)
    
    try:
        # Get current commit hash
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], 
                                       cwd=repo_path).decode().strip()
        
        # Get branch name
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                       cwd=repo_path).decode().strip()
        
        # Get remote URLs
        try:
            remotes_output = subprocess.check_output(['git', 'remote', '-v'], 
                                                   cwd=repo_path).decode().strip()
            remotes = {}
            for line in remotes_output.split('\n'):
                if line and '\t' in line:
                    name, url_type = line.split('\t', 1)
                    url = url_type.split(' ')[0]  # Remove (fetch)/(push) suffix
                    if name not in remotes:  # Prefer first occurrence (usually fetch)
                        remotes[name] = url
        except subprocess.CalledProcessError:
            remotes = {}
        
        # Check for uncommitted changes
        try:
            status = subprocess.check_output(['git', 'status', '--porcelain'], 
                                           cwd=repo_path).decode().strip()
            has_uncommitted = bool(status)
        except subprocess.CalledProcessError:
            status = None
            has_uncommitted = None
        
        # Get repository root
        try:
            repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], 
                                              cwd=repo_path).decode().strip()
        except subprocess.CalledProcessError:
            repo_root = str(repo_path)
        
        return {
            'commit_hash': commit_hash,
            'short_hash': commit_hash[:8],
            'branch': branch,
            'remotes': remotes,
            'origin_url': remotes.get('origin', None),
            'has_uncommitted_changes': has_uncommitted,
            'status': status,
            'repo_root': repo_root,
            'method': 'subprocess'
        }

    except subprocess.CalledProcessError:
        # Fall back to manual parsing
        return get_git_info_manual(repo_path)


### Manual methods that don't require calling the git command:

def find_git_dir(start_path=None):
    """Walk up directory tree to find .git directory"""
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)
    
    current = start_path.resolve()
    
    # Walk up the directory tree
    while current != current.parent:  # Stop at filesystem root
        git_dir = current / '.git'
        if git_dir.exists():
            return git_dir
        current = current.parent
    
    return None

def get_git_info_manual(start_path=None):
    try:
        git_dir = find_git_dir(start_path)
        if git_dir is None:
            return {'error': 'Not a git repository'}
        
        # Handle .git file (for git worktrees or submodules)
        if git_dir.is_file():
            git_file_content = git_dir.read_text().strip()
            if git_file_content.startswith('gitdir: '):
                # Parse gitdir reference
                gitdir_path = git_file_content[8:]  # Remove 'gitdir: '
                if not Path(gitdir_path).is_absolute():
                    # Relative path, resolve from .git file location
                    git_dir = git_dir.parent / gitdir_path
                else:
                    git_dir = Path(gitdir_path)
                git_dir = git_dir.resolve()
        
        if not git_dir.exists():
            return {'error': 'Git directory not found'}
        
        # Read HEAD
        head_file = git_dir / 'HEAD'
        if not head_file.exists():
            return {'error': 'Invalid git repository - no HEAD file'}
        
        head_ref = head_file.read_text().strip()
        
        if head_ref.startswith('ref: '):
            # Branch reference
            ref_path = git_dir / head_ref[5:]  # Remove 'ref: '
            if ref_path.exists():
                commit_hash = ref_path.read_text().strip()
                branch = ref_path.name
            else:
                return {'error': f'Branch reference not found: {ref_path}'}
        else:
            # Detached HEAD
            commit_hash = head_ref
            branch = 'HEAD'
        
        # Read git config for remotes
        config_path = git_dir / 'config'
        remotes = {}
        
        if config_path.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_path)
                
                # Find all remote sections
                for section in config.sections():
                    if section.startswith('remote "') and section.endswith('"'):
                        remote_name = section[8:-1]  # Extract name from 'remote "name"'
                        if 'url' in config[section]:
                            remotes[remote_name] = config[section]['url']
            except Exception as e:
                # Config parsing failed, but we can still return basic info
                pass
        
        # Get repository root (where .git directory is located)
        repo_root = git_dir.parent if git_dir.name == '.git' else git_dir.parent.parent
        
        return {
            'commit_hash': commit_hash,
            'short_hash': commit_hash[:8],
            'branch': branch,
            'remotes': remotes,
            'origin_url': remotes.get('origin', None),
            'has_uncommitted_changes': None,  # Cannot detect without git status
            'status': None,  # Cannot detect without git status
            'git_dir': str(git_dir),
            'repo_root': str(repo_root),
            'method': 'manual'
        }
        
    except Exception as e:
        return {'error': f'Git parsing failed: {str(e)}'}


def get_scopefoundry_git_info():
    """
    Get git information for ScopeFoundry based on the location of this file.
    Works for submodules, standalone repos, and handles pip-installed packages.
    """
    # Get ScopeFoundry git info from the directory containing this file
    scopefoundry_path = Path(__file__).parent
    git_info = get_git_info(scopefoundry_path)
    
    # If we get an error (likely because it's pip installed), try to get version info
    if 'error' in git_info:
        try:
            import ScopeFoundry
            version = getattr(ScopeFoundry, '__version__', 'unknown')
            return {
                'installation_type': 'pip_installed',
                'version': version,
                'package_location': str(scopefoundry_path),
                'error': 'ScopeFoundry is pip installed, no git information available'
            }
        except ImportError:
            return {
                'installation_type': 'unknown',
                'package_location': str(scopefoundry_path),
                'error': 'Could not determine ScopeFoundry installation type'
            }
    else:
        # Add installation type for git-based installations
        git_info['installation_type'] = 'git_repository'
        return git_info


def get_multi_repo_git_info(repo_paths=None):
    """
    Get git information for multiple repositories.
    
    Args:
        repo_paths: Dict mapping names to paths, or None to auto-detect
                   e.g., {'main': '/path/to/main', 'scopefoundry': '/path/to/sf'}
    
    Returns:
        Dict mapping repository names to their git info
    """
    if repo_paths is None:
        # Auto-detect: current working directory and ScopeFoundry location
        repo_paths = {
            'user_project': Path.cwd(),
            'scopefoundry': Path(__file__).parent
        }
    
    git_info = {}
    for name, path in repo_paths.items():
        if name == 'scopefoundry':
            git_info[name] = get_scopefoundry_git_info()
        else:
            git_info[name] = get_git_info(path)
    
    return git_info


def get_project_and_scopefoundry_git_info():
    """
    Get git information for both the user's project and ScopeFoundry.
    This is the recommended function for adding git info to H5 files.
    """
    return {
        'user_project': get_git_info(Path.cwd()),
        'scopefoundry': get_scopefoundry_git_info()
    }

