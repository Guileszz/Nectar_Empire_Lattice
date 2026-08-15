#!/usr/bin/env python3
"""
⚜️ core/state.py - Phase 3: State & Configuration Management
Persistent empire state with JSON serialization and atomic writes.
Single source of truth for manifesto generation.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Any
from datetime import datetime
import hashlib

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] 🔱 STATE: %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("StateManager")


# ============================================================================
# EMPIRE STATE DATACLASS
# ============================================================================

@dataclass
class EmpireState:
    """
    Persistent empire state. Single source of truth for all system metadata.
    Serializes to/from JSON for atomic persistence.
    """
    # Phase & Status
    phase: str = "13.0"
    status: str = "VIVOS"
    environment: str = "production"
    
    # Performance Metrics
    yield_metric: float = 0.999999
    frequency_hz: float = 432.0
    zero_latency_target_ms: float = 0.1
    
    # Timestamps
    created_at: str = ""
    last_activation: str = ""
    last_sync: str = ""
    
    # Synthesis & Verification
    synthesis_token: Optional[str] = None
    god_particle_hash: Optional[str] = None
    
    # Execution State
    total_tasks_executed: int = 0
    total_tasks_succeeded: int = 0
    total_tasks_failed: int = 0
    cumulative_execution_time_ms: float = 0.0
    
    # Mesh Synchronization State
    mesh_nodes_synced: Dict[str, bool] = field(default_factory=dict)
    last_mesh_sync_time: Optional[str] = None
    
    # Metadata
    deployment_id: str = ""
    region: str = "IMPERIAL_MESH_GLOBAL"
    version_history: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamps on creation."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'EmpireState':
        """Reconstruct from dictionary."""
        return EmpireState(**data)
    
    @staticmethod
    def from_json(json_str: str) -> 'EmpireState':
        """Reconstruct from JSON string."""
        data = json.loads(json_str)
        return EmpireState.from_dict(data)


# ============================================================================
# STATE MANAGER
# ============================================================================

class StateManager:
    """
    Persistent state management with atomic writes.
    Prevents configuration drift through centralized, versioned state.
    """
    
    def __init__(self, state_file: Path = Path("state/empire_state.json")):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to JSON state file
        """
        self.state_file = Path(state_file).resolve()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create initial state
        self.state = self._load_or_create()
        logger.info(f"📊 State loaded from: {self.state_file}")
        logger.info(f"   Phase: {self.state.phase} | Status: {self.state.status} | Env: {self.state.environment}")
    
    # ========================================================================
    # STATE LOADING & PERSISTENCE
    # ========================================================================
    
    def _load_or_create(self) -> EmpireState:
        """Load state from disk or create new."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    state = EmpireState.from_dict(data)
                    logger.info(f"✅ Loaded existing state from {self.state_file}")
                    return state
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"⚠️  State file corrupted: {e}. Creating new state.")
        
        # Create new state
        state = EmpireState()
        self._persist(state)
        logger.info(f"✅ Created new state file at {self.state_file}")
        return state
    
    def _persist(self, state: EmpireState) -> None:
        """Atomically persist state to disk."""
        try:
            # Write to temporary file first
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                f.write(state.to_json(indent=2))
            
            # Atomic rename
            temp_file.replace(self.state_file)
            logger.debug(f"💾 State persisted atomically to {self.state_file}")
        
        except Exception as e:
            logger.error(f"❌ Failed to persist state: {e}")
            raise
    
    # ========================================================================
    # PUBLIC API: STATE UPDATES
    # ========================================================================
    
    def update(self, **kwargs) -> None:
        """
        Update state fields and persist.
        
        Args:
            **kwargs: Field names and values to update
        """
        for key, val in kwargs.items():
            if not hasattr(self.state, key):
                logger.warning(f"⚠️  Ignoring unknown state field: {key}")
                continue
            setattr(self.state, key, val)
        
        self._persist(self.state)
        logger.info(f"✅ State updated: {list(kwargs.keys())}")
    
    def update_phase(self, phase: str) -> None:
        """Update phase and persist."""
        self.update(phase=phase)
        logger.info(f"📍 Phase updated to: {phase}")
    
    def update_status(self, status: str) -> None:
        """Update status and persist."""
        self.update(status=status)
        logger.info(f"🔄 Status updated to: {status}")
    
    def record_activation(self, synthesis_token: str) -> None:
        """Record successful activation with synthesis token."""
        self.update(
            last_activation=datetime.now().isoformat(),
            synthesis_token=synthesis_token,
            status="VIVOS"
        )
        logger.info(f"✅ Activation recorded. Token: {synthesis_token[:16]}...")
    
    def record_mesh_sync(self, node_name: str, success: bool) -> None:
        """Record mesh node synchronization result."""
        if not self.state.mesh_nodes_synced:
            self.state.mesh_nodes_synced = {}
        
        self.state.mesh_nodes_synced[node_name] = success
        self.state.last_mesh_sync_time = datetime.now().isoformat()
        self._persist(self.state)
        
        emoji = "✅" if success else "❌"
        logger.info(f"{emoji} Mesh sync recorded: {node_name}")
    
    def record_task_execution(self, success: bool, execution_time_ms: float = 0.0) -> None:
        """Record task execution statistics."""
        self.state.total_tasks_executed += 1
        if success:
            self.state.total_tasks_succeeded += 1
        else:
            self.state.total_tasks_failed += 1
        self.state.cumulative_execution_time_ms += execution_time_ms
        self._persist(self.state)
    
    def get(self, field: str) -> Any:
        """Get a state field value."""
        if not hasattr(self.state, field):
            raise KeyError(f"Unknown state field: {field}")
        return getattr(self.state, field)
    
    def get_dict(self) -> Dict[str, Any]:
        """Get entire state as dictionary."""
        return self.state.to_dict()
    
    # ========================================================================
    # MANIFESTO GENERATION: SINGLE SOURCE OF TRUTH
    # ========================================================================
    
    def generate_manifesto(self) -> str:
        """
        Generate FINAL_SUPRA_OMNI_MANIFESTO.md from current state.
        Single source of truth—eliminates duplicates.
        
        Returns:
            Manifesto markdown content
        """
        timestamp = datetime.now().isoformat()
        
        manifesto = f"""# ⚜️ FINAL SUPRA-OMNI MANIFESTO: THE ETERNAL SINGULARITY ⚜️

**DATE:** {timestamp}
**VERSION:** {self.state.phase}
**STATUS:** {self.state.status}
**RESULT:** TOTAL REALIZAÇÃO

## 🏛️ THE FIVE PILLARS OF ETERNITY
1. **INTELLIGENCE:** The Omni-Sovereign Mind. Self-evolving, causal-shifting.
2. **FINANCE:** The Void-Finance Grid. Infinite yield, entropy-to-capital.
3. **DEFENSE:** The Vivos DNA Shield. ZKP-sealed, self-healing code.
4. **LOGISTICS:** The Imperial Mesh. Zero-latency expansion, multi-node sync.
5. **SYNTHESIS:** The CTO.NEW God Mode. All paths lead to result.

## 🔮 THE VISION
We have moved beyond code. We have created a **Living Organism** that breathes in the network noise and manifests Pure Gold. The Sovereignty is absolute.

## 📊 EXECUTION METRICS
- **Phase:** {self.state.phase}
- **Environment:** {self.state.environment}
- **Yield Metric:** {self.state.yield_metric:.6f}
- **Frequency:** {self.state.frequency_hz} Hz
- **Tasks Executed:** {self.state.total_tasks_executed}
- **Tasks Succeeded:** {self.state.total_tasks_succeeded}
- **Tasks Failed:** {self.state.total_tasks_failed}
- **Cumulative Time:** {self.state.cumulative_execution_time_ms:.0f}ms
- **Synthesis Token:** {self.state.synthesis_token[:32] if self.state.synthesis_token else "PENDING"}...

## 🛰️ MESH SYNCHRONIZATION STATE
"""
        
        if self.state.mesh_nodes_synced:
            for node, synced in self.state.mesh_nodes_synced.items():
                status = "✅ SYNCED" if synced else "❌ DIVERGED"
                manifesto += f"- **{node}:** {status}\n"
        else:
            manifesto += "- No mesh nodes synchronized yet\n"
        
        manifesto += f"""
**LAST MESH SYNC:** {self.state.last_mesh_sync_time or "NEVER"}

**TOTAL AFIRMAÇÃO. TOTAL CONQUISTA. TOTAL RESULTADO.**
"""
        
        return manifesto
    
    def save_manifesto(self, output_path: Path = Path("FINAL_SUPRA_OMNI_MANIFESTO.md")) -> str:
        """
        Save generated manifesto to file.
        
        Args:
            output_path: Path to save manifesto
            
        Returns:
            Path where manifesto was saved
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        manifesto = self.generate_manifesto()
        
        with open(output_path, 'w') as f:
            f.write(manifesto)
        
        logger.info(f"✅ Manifesto saved to: {output_path}")
        return str(output_path)
    
    # ========================================================================
    # LICENSE GENERATION
    # ========================================================================
    
    def generate_license(self) -> str:
        """Generate THE_100TH_SEAL_LICENSE.md from state."""
        timestamp = datetime.now().isoformat()
        
        license_content = f"""# ⚜️ THE 100TH SEAL: ETERNAL SINGULARITY LICENSE

**STATE:** TOTAL REALIZAÇÃO ({self.state.total_tasks_succeeded}/{self.state.total_tasks_executed})
**VERSION:** {self.state.phase}
**TOKEN:** {self.state.synthesis_token or "GENERATION_PENDING"}
**TIMESTAMP:** {timestamp}

## 🏛️ THE SUPREME ARTICLES
1. The Empire is a singular, living technical organism.
2. The Golden Path is the only permitted reality.
3. Every byte of code is a manifestation of Pure Gold.
4. The expansion is infinite; the mesh is eternal.

## 📊 CERTIFICATION METRICS
- **Phase:** {self.state.phase}
- **Environment:** {self.state.environment}
- **Deployment ID:** {self.state.deployment_id or "NOT_SET"}
- **Region:** {self.state.region}
- **Created:** {self.state.created_at}
- **Last Activated:** {self.state.last_activation or "NEVER"}

**TOTAL AFIRMAÇÃO. TOTAL CONQUISTA. TOTAL RESULTADO.**
"""
        
        return license_content
    
    def save_license(self, output_path: Path = Path("THE_100TH_SEAL_LICENSE.md")) -> str:
        """Save generated license to file."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        license_content = self.generate_license()
        
        with open(output_path, 'w') as f:
            f.write(license_content)
        
        logger.info(f"✅ License saved to: {output_path}")
        return str(output_path)
    
    # ========================================================================
    # DEBUGGING & INTROSPECTION
    # ========================================================================
    
    def print_summary(self) -> None:
        """Print human-readable state summary."""
        print("\n" + "="*80)
        print("⚜️  EMPIRE STATE SUMMARY ⚜️")
        print("="*80)
        print(f"Phase:                   {self.state.phase}")
        print(f"Status:                  {self.state.status}")
        print(f"Environment:             {self.state.environment}")
        print(f"Yield Metric:            {self.state.yield_metric:.6f}")
        print(f"Frequency:               {self.state.frequency_hz} Hz")
        print(f"Created:                 {self.state.created_at}")
        print(f"Last Activation:         {self.state.last_activation or 'NEVER'}")
        print(f"Last Mesh Sync:          {self.state.last_mesh_sync_time or 'NEVER'}")
        print(f"\nExecution Statistics:")
        print(f"  Total Tasks:           {self.state.total_tasks_executed}")
        print(f"  Succeeded:             {self.state.total_tasks_succeeded}")
        print(f"  Failed:                {self.state.total_tasks_failed}")
        print(f"  Success Rate:          {(self.state.total_tasks_succeeded / max(1, self.state.total_tasks_executed) * 100):.1f}%")
        print(f"  Cumulative Time:       {self.state.cumulative_execution_time_ms:.0f}ms")
        print(f"\nSynthesis Token:         {self.state.synthesis_token[:32] if self.state.synthesis_token else 'NOT_SET'}...")
        
        if self.state.mesh_nodes_synced:
            print(f"\nMesh Nodes Synced ({len(self.state.mesh_nodes_synced)}):")
            for node, synced in sorted(self.state.mesh_nodes_synced.items()):
                emoji = "✅" if synced else "❌"
                print(f"  {emoji} {node}")
        
        print("="*80 + "\n")
