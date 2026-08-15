#!/usr/bin/env python3
"""
⚜️ DEPENDENCY_RESOLVER.py - Phase 1 Foundation Integrity
Central dependency resolution engine. Decouples orchestration from hardcoded paths.
Reads from config/manifest.yml; resolves all external powers and mesh nodes.
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] 🔱 RESOLVER: %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("DependencyResolver")


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PowerDependency:
    """Represents a single power/external script dependency."""
    name: str
    category: str
    module: str
    path: str
    required: bool
    timeout: int
    description: str
    args: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MeshNode:
    """Represents a cross-repository mesh node for synchronization."""
    name: str
    repo_url: str
    sync_protocol: str
    api_endpoint: str
    domains: List[str]
    priority: int
    timeout: int
    retry_count: int
    description: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionConfig:
    """Runtime execution parameters from manifest."""
    parallel_milestones: bool
    max_concurrent_tasks: int
    default_task_timeout: int
    default_milestone_timeout: int
    global_timeout: int
    fail_fast: bool
    retry_strategy: str
    max_retries: int
    retry_delay_ms: int
    log_level: str
    log_format: str
    capture_stderr: bool
    capture_stdout: bool
    process_memory_limit_mb: int
    subprocess_memory_limit_mb: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# DEPENDENCY RESOLVER
# ============================================================================

class DependencyResolver:
    """
    Central resolver for all external dependencies and mesh nodes.
    Reads manifest.yml and resolves paths dynamically.
    
    Features:
    - Strict validation of all paths
    - Environment variable override support
    - Comprehensive error reporting
    - Logging of all resolution attempts
    """
    
    def __init__(self, manifest_path: str = "config/manifest.yml"):
        """
        Initialize resolver from manifest.
        
        Args:
            manifest_path: Path to config/manifest.yml (relative or absolute)
            
        Raises:
            FileNotFoundError: If manifest doesn't exist
            yaml.YAMLError: If manifest is malformed
        """
        self.manifest_path = Path(manifest_path).resolve()
        self.repo_root = self.manifest_path.parent.parent
        
        logger.info(f"📋 Loading manifest from: {self.manifest_path}")
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"❌ Manifest not found at {self.manifest_path}. "
                f"Expected: {self.repo_root / 'config' / 'manifest.yml'}"
            )
        
        try:
            with open(self.manifest_path, 'r') as f:
                self.manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"❌ Manifest YAML parse error: {e}")
            raise
        
        logger.info(f"✅ Manifest loaded. Version: {self.manifest.get('version')}")
        
        # Parse manifest sections
        self.version = self.manifest.get("version", "unknown")
        self.phase = self.manifest.get("phase", "UNKNOWN")
        
        # Resolve all dependencies
        self._powers = self._parse_powers()
        self._imperial_logic = self._parse_imperial_logic()
        self._mesh_nodes = self._parse_mesh_nodes()
        self._execution_config = self._parse_execution_config()
        self._resolved_paths: Dict[str, str] = {}
        self._validation_errors: List[str] = []
        
        # Validate and resolve all paths
        self._validate_and_resolve_all()
    
    # ========================================================================
    # PARSING
    # ========================================================================
    
    def _parse_powers(self) -> Dict[str, PowerDependency]:
        """Parse external_dependencies.powers from manifest."""
        powers = {}
        for power_def in self.manifest.get("external_dependencies", {}).get("powers", []):
            dep = PowerDependency(
                name=power_def["name"],
                category=power_def.get("category", "unknown"),
                module=power_def.get("module", ""),
                path=power_def["path"],
                required=power_def.get("required", True),
                timeout=power_def.get("timeout", 60),
                description=power_def.get("description", ""),
                args=power_def.get("args", None)
            )
            powers[dep.name] = dep
        logger.info(f"✅ Parsed {len(powers)} power dependencies")
        return powers
    
    def _parse_imperial_logic(self) -> Dict[str, PowerDependency]:
        """Parse external_dependencies.imperial_logic from manifest."""
        logic = {}
        for logic_def in self.manifest.get("external_dependencies", {}).get("imperial_logic", []):
            dep = PowerDependency(
                name=logic_def["name"],
                category=logic_def.get("category", "unknown"),
                module=logic_def.get("module", ""),
                path=logic_def["path"],
                required=logic_def.get("required", True),
                timeout=logic_def.get("timeout", 60),
                description=logic_def.get("description", ""),
                args=logic_def.get("args", None)
            )
            logic[dep.name] = dep
        logger.info(f"✅ Parsed {len(logic)} imperial logic dependencies")
        return logic
    
    def _parse_mesh_nodes(self) -> Dict[str, MeshNode]:
        """Parse mesh_nodes from manifest."""
        nodes = {}
        for node_def in self.manifest.get("mesh_nodes", []):
            node = MeshNode(
                name=node_def["name"],
                repo_url=node_def["repo_url"],
                sync_protocol=node_def.get("sync_protocol", "lattice_v13"),
                api_endpoint=node_def.get("api_endpoint", ""),
                domains=node_def.get("domains", []),
                priority=node_def.get("priority", 999),
                timeout=node_def.get("timeout", 30),
                retry_count=node_def.get("retry_count", 3),
                description=node_def.get("description", "")
            )
            nodes[node.name] = node
        logger.info(f"✅ Parsed {len(nodes)} mesh nodes")
        return nodes
    
    def _parse_execution_config(self) -> ExecutionConfig:
        """Parse execution configuration from manifest."""
        exec_cfg = self.manifest.get("execution", {})
        config = ExecutionConfig(
            parallel_milestones=exec_cfg.get("parallel_milestones", True),
            max_concurrent_tasks=exec_cfg.get("max_concurrent_tasks", 4),
            default_task_timeout=exec_cfg.get("default_task_timeout", 60),
            default_milestone_timeout=exec_cfg.get("default_milestone_timeout", 120),
            global_timeout=exec_cfg.get("global_timeout", 3600),
            fail_fast=exec_cfg.get("fail_fast", False),
            retry_strategy=exec_cfg.get("retry_strategy", "exponential_backoff"),
            max_retries=exec_cfg.get("max_retries", 2),
            retry_delay_ms=exec_cfg.get("retry_delay_ms", 100),
            log_level=exec_cfg.get("log_level", "INFO"),
            log_format=exec_cfg.get("log_format", "json"),
            capture_stderr=exec_cfg.get("capture_stderr", True),
            capture_stdout=exec_cfg.get("capture_stdout", True),
            process_memory_limit_mb=exec_cfg.get("process_memory_limit_mb", 1024),
            subprocess_memory_limit_mb=exec_cfg.get("subprocess_memory_limit_mb", 512)
        )
        logger.info(f"✅ Loaded execution config. Parallel={config.parallel_milestones}, MaxRetries={config.max_retries}")
        return config
    
    # ========================================================================
    # VALIDATION & RESOLUTION
    # ========================================================================
    
    def _validate_and_resolve_all(self) -> None:
        """
        Validate all dependencies and resolve their paths.
        Sets self._validation_errors if any required dependencies are missing.
        """
        logger.info("🔍 Starting comprehensive dependency validation...")
        
        # Resolve power dependencies
        for name, power in self._powers.items():
            resolved_path = self._resolve_dependency_path(power.path, name, power.required)
            if resolved_path:
                self._resolved_paths[name] = resolved_path
        
        # Resolve imperial logic dependencies
        for name, logic in self._imperial_logic.items():
            resolved_path = self._resolve_dependency_path(logic.path, name, logic.required)
            if resolved_path:
                self._resolved_paths[name] = resolved_path
        
        # Log validation summary
        if self._validation_errors:
            logger.warning(f"⚠️  {len(self._validation_errors)} validation error(s) found:")
            for error in self._validation_errors:
                logger.warning(f"   - {error}")
        else:
            logger.info("✅ All dependencies validated successfully")
    
    def _resolve_dependency_path(
        self, 
        relative_path: str, 
        dep_name: str,
        required: bool
    ) -> Optional[str]:
        """
        Resolve a dependency path. Searches:
        1. Absolute path (if already absolute)
        2. Relative to repo root
        3. NECTAR_DEPS_DIR environment variable
        
        Args:
            relative_path: Path from manifest (relative to deps_dir)
            dep_name: Dependency name (for logging)
            required: Whether this dependency is required
            
        Returns:
            Resolved absolute path, or None if not found
        """
        # Try repo root first
        repo_path = self.repo_root / relative_path
        if repo_path.exists():
            logger.info(f"✅ {dep_name:40} → {repo_path}")
            return str(repo_path)
        
        # Try NECTAR_DEPS_DIR environment variable
        deps_dir = os.getenv("NECTAR_DEPS_DIR")
        if deps_dir:
            env_path = Path(deps_dir) / relative_path
            if env_path.exists():
                logger.info(f"✅ {dep_name:40} → {env_path} (from NECTAR_DEPS_DIR)")
                return str(env_path)
        
        # Try ./dependencies subdirectory (local clone)
        local_deps_path = self.repo_root / "dependencies" / relative_path
        if local_deps_path.exists():
            logger.info(f"✅ {dep_name:40} → {local_deps_path} (local deps/)")
            return str(local_deps_path)
        
        # Not found
        msg = (
            f"❌ {dep_name} NOT FOUND at:\n"
            f"   - {repo_path}\n"
            f"   - {Path(deps_dir) / relative_path if deps_dir else 'NECTAR_DEPS_DIR not set'}\n"
            f"   - {local_deps_path}"
        )
        
        if required:
            self._validation_errors.append(msg)
            logger.error(msg)
        else:
            logger.warning(f"⚠️  Optional dependency missing: {dep_name}")
        
        return None
    
    # ========================================================================
    # PUBLIC API: GET RESOLVED DEPENDENCIES
    # ========================================================================
    
    def get_power(self, name: str) -> Tuple[PowerDependency, str]:
        """
        Get a power dependency and its resolved path.
        
        Args:
            name: Power name (e.g., "Singularity_Cooling")
            
        Returns:
            Tuple of (PowerDependency, resolved_path)
            
        Raises:
            KeyError: If power not found
            FileNotFoundError: If resolved path does not exist
        """
        if name not in self._powers:
            raise KeyError(f"Power '{name}' not found in manifest")
        
        power = self._powers[name]
        resolved_path = self._resolved_paths.get(name)
        
        if not resolved_path:
            raise FileNotFoundError(
                f"Power '{name}' could not be resolved. "
                f"Check NECTAR_DEPS_DIR or run: "
                f"git clone https://github.com/guitriloco/Nectar_Powers.git dependencies/powers"
            )
        
        return power, resolved_path
    
    def get_imperial_logic(self, name: str) -> Tuple[PowerDependency, str]:
        """
        Get an imperial logic dependency and its resolved path.
        
        Args:
            name: Logic module name (e.g., "IMPERIAL_LOGIC_Vivos")
            
        Returns:
            Tuple of (PowerDependency, resolved_path)
            
        Raises:
            KeyError: If logic module not found
            FileNotFoundError: If resolved path does not exist
        """
        if name not in self._imperial_logic:
            raise KeyError(f"Imperial logic module '{name}' not found in manifest")
        
        logic = self._imperial_logic[name]
        resolved_path = self._resolved_paths.get(name)
        
        if not resolved_path:
            raise FileNotFoundError(
                f"Imperial logic '{name}' could not be resolved. "
                f"Check repository structure in {self.repo_root}"
            )
        
        return logic, resolved_path
    
    def get_all_powers(self) -> Dict[str, PowerDependency]:
        """Get all power dependencies."""
        return self._powers.copy()
    
    def get_all_imperial_logic(self) -> Dict[str, PowerDependency]:
        """Get all imperial logic dependencies."""
        return self._imperial_logic.copy()
    
    def get_mesh_node(self, name: str) -> MeshNode:
        """Get a mesh node by name."""
        if name not in self._mesh_nodes:
            raise KeyError(f"Mesh node '{name}' not found in manifest")
        return self._mesh_nodes[name]
    
    def get_all_mesh_nodes(self) -> Dict[str, MeshNode]:
        """Get all mesh nodes."""
        return self._mesh_nodes.copy()
    
    def get_execution_config(self) -> ExecutionConfig:
        """Get execution configuration."""
        return self._execution_config
    
    def get_resolved_paths(self) -> Dict[str, str]:
        """Get all resolved dependency paths."""
        return self._resolved_paths.copy()
    
    def get_validation_errors(self) -> List[str]:
        """Get all validation errors."""
        return self._validation_errors.copy()
    
    def has_validation_errors(self) -> bool:
        """Check if any required dependencies failed validation."""
        return len(self._validation_errors) > 0
    
    # ========================================================================
    # DEBUGGING & INTROSPECTION
    # ========================================================================
    
    def debug_dump(self) -> Dict:
        """
        Return complete resolver state for debugging.
        """
        return {
            "manifest_path": str(self.manifest_path),
            "repo_root": str(self.repo_root),
            "version": self.version,
            "phase": self.phase,
            "powers_count": len(self._powers),
            "imperial_logic_count": len(self._imperial_logic),
            "mesh_nodes_count": len(self._mesh_nodes),
            "resolved_count": len(self._resolved_paths),
            "validation_errors": self._validation_errors,
            "execution_config": self._execution_config.to_dict()
        }
    
    def print_summary(self) -> None:
        """Print human-readable resolution summary."""
        print("\n" + "="*80)
        print("⚜️  DEPENDENCY RESOLVER SUMMARY ⚜️")
        print("="*80)
        print(f"Manifest:           {self.manifest_path}")
        print(f"Repository Root:    {self.repo_root}")
        print(f"Version:            {self.version}")
        print(f"Phase:              {self.phase}")
        print(f"Powers:             {len(self._powers)} dependencies")
        print(f"Imperial Logic:     {len(self._imperial_logic)} modules")
        print(f"Mesh Nodes:         {len(self._mesh_nodes)} nodes")
        print(f"Successfully Resolved: {len(self._resolved_paths)} paths")
        print(f"Validation Errors:  {len(self._validation_errors)}")
        
        if self._validation_errors:
            print("\n❌ ERRORS:")
            for error in self._validation_errors:
                print(f"  {error}")
        
        print("\n✅ RESOLVED PATHS:")
        for name, path in sorted(self._resolved_paths.items()):
            print(f"  {name:40} → {path}")
        
        print("\n🛰️  MESH NODES:")
        for name, node in sorted(self._mesh_nodes.items(), key=lambda x: x[1].priority):
            print(f"  [{node.priority}] {name:25} | {node.api_endpoint} | Retry={node.retry_count}")
        
        print("="*80 + "\n")
