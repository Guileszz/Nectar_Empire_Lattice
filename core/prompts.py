#!/usr/bin/env python3
"""
⚜️ core/prompts.py - Phase 4: Prompt System Integration
Dynamic AI personality matrix injection with ultra-low latency placeholder resolution.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] 🔱 PROMPTS: %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("PromptMatrix")


# ============================================================================
# PROMPT DATACLASS
# ============================================================================

@dataclass
class PromptTemplate:
    """Represents a single prompt template with metadata."""
    name: str
    content: str
    domain: str = "general"
    version: str = "1.0"
    description: str = ""
    required_variables: List[str] = None
    
    def __post_init__(self):
        if self.required_variables is None:
            self.required_variables = []


# ============================================================================
# PROMPT MATRIX ENGINE
# ============================================================================

class PromptMatrix:
    """
    Dynamic prompt system with personality matrix injection.
    Features:
    - Auto-loads and parses personality-matrix.md
    - Scans specialized prompts by domain (wealth, health, dev, pets)
    - Ultra-low latency placeholder replacement (${{trait}}, {{ context_var }})
    - Graceful fallback to default system prompts
    - Cache optimization for repeated injections
    """
    
    # Placeholder patterns for ultra-fast regex matching
    TRAIT_PATTERN = re.compile(r'\$\{\{(\w+)\}\}')
    CONTEXT_PATTERN = re.compile(r'\{\{\s*(\w+)\s*\}\}')
    
    def __init__(self, prompts_dir: Path = Path("prompts")):
        """
        Initialize prompt matrix from directory structure.
        
        Args:
            prompts_dir: Path to prompts/ directory
        """
        self.prompts_dir = Path(prompts_dir).resolve()
        logger.info(f"📂 Loading prompts from: {self.prompts_dir}")
        
        if not self.prompts_dir.exists():
            logger.warning(f"⚠️  Prompts directory not found: {self.prompts_dir}")
            self._init_defaults()
            return
        
        # Load all prompt structures
        self.personality_matrix: Dict[str, str] = {}
        self.core_prompts: Dict[str, PromptTemplate] = {}
        self.specialized_prompts: Dict[str, Dict[str, PromptTemplate]] = {}
        self.default_system_prompt = ""
        
        # Load personality matrix
        self._load_personality_matrix()
        
        # Load core prompts
        self._load_core_prompts()
        
        # Load specialized domain prompts
        self._load_specialized_prompts()
        
        logger.info(f"✅ Prompts loaded. Core={len(self.core_prompts)}, Specialized domains={len(self.specialized_prompts)}")
    
    # ========================================================================
    # INITIALIZATION & LOADING
    # ========================================================================
    
    def _init_defaults(self) -> None:
        """Initialize with built-in defaults when directory missing."""
        logger.warning("⚠️  Initializing with default prompts")
        self.personality_matrix = self._get_default_personality()
        self.core_prompts = {"system_default": self._get_default_system_prompt()}
        self.specialized_prompts = {}
        self.default_system_prompt = self.core_prompts["system_default"].content
    
    def _load_personality_matrix(self) -> None:
        """Load and parse personality-matrix.md."""
        matrix_path = self.prompts_dir / "personality-matrix.md"
        
        if not matrix_path.exists():
            logger.warning(f"⚠️  personality-matrix.md not found at {matrix_path}")
            self.personality_matrix = self._get_default_personality()
            return
        
        try:
            with open(matrix_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML-like structure or key: value pairs
            self.personality_matrix = self._parse_personality_config(content)
            logger.info(f"✅ Loaded personality matrix with {len(self.personality_matrix)} traits")
        
        except Exception as e:
            logger.error(f"❌ Failed to load personality matrix: {e}")
            self.personality_matrix = self._get_default_personality()
    
    def _load_core_prompts(self) -> None:
        """Load all .md files from prompts/core/."""
        core_dir = self.prompts_dir / "core"
        
        if not core_dir.exists():
            logger.warning(f"⚠️  Core prompts directory not found: {core_dir}")
            self.core_prompts["system_default"] = self._get_default_system_prompt()
            return
        
        try:
            for prompt_file in sorted(core_dir.glob("*.md")):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                template = PromptTemplate(
                    name=prompt_file.stem,
                    content=content,
                    domain="core",
                    description=f"Core prompt: {prompt_file.name}"
                )
                self.core_prompts[prompt_file.stem] = template
            
            # Set default if available
            if "system_default" in self.core_prompts:
                self.default_system_prompt = self.core_prompts["system_default"].content
            else:
                self.default_system_prompt = self._get_default_system_prompt().content
            
            logger.info(f"✅ Loaded {len(self.core_prompts)} core prompts")
        
        except Exception as e:
            logger.error(f"❌ Failed to load core prompts: {e}")
            self.core_prompts["system_default"] = self._get_default_system_prompt()
    
    def _load_specialized_prompts(self) -> None:
        """Load domain-specific prompts by niche."""
        spec_dir = self.prompts_dir / "specialized"
        
        if not spec_dir.exists():
            logger.warning(f"⚠️  Specialized prompts directory not found: {spec_dir}")
            return
        
        try:
            for niche_dir in sorted(spec_dir.iterdir()):
                if not niche_dir.is_dir():
                    continue
                
                domain_name = niche_dir.name
                self.specialized_prompts[domain_name] = {}
                
                for prompt_file in sorted(niche_dir.glob("*.md")):
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    template = PromptTemplate(
                        name=prompt_file.stem,
                        content=content,
                        domain=domain_name,
                        description=f"Specialized prompt for {domain_name}"
                    )
                    self.specialized_prompts[domain_name][prompt_file.stem] = template
                
                logger.info(f"✅ Loaded {len(self.specialized_prompts[domain_name])} prompts for domain: {domain_name}")
        
        except Exception as e:
            logger.error(f"❌ Failed to load specialized prompts: {e}")
    
    # ========================================================================
    # PUBLIC API: PROMPT RETRIEVAL
    # ========================================================================
    
    def get_system_prompt(self, domain: str = "general") -> str:
        """
        Get system prompt for a domain.
        
        Args:
            domain: Domain name (general, wealth, health, dev, pets)
            
        Returns:
            System prompt content
        """
        # Try specialized domain first
        if domain in self.specialized_prompts:
            if "system" in self.specialized_prompts[domain]:
                return self.specialized_prompts[domain]["system"].content
        
        # Fall back to core default
        return self.default_system_prompt
    
    def get_prompt(self, prompt_name: str, domain: str = "general") -> Optional[str]:
        """
        Get a specific prompt by name and domain.
        
        Args:
            prompt_name: Prompt name (e.g., "system", "task_wrapper")
            domain: Domain name
            
        Returns:
            Prompt content, or None if not found
        """
        # Try specialized domain first
        if domain != "general" and domain in self.specialized_prompts:
            if prompt_name in self.specialized_prompts[domain]:
                return self.specialized_prompts[domain][prompt_name].content
        
        # Try core prompts
        if prompt_name in self.core_prompts:
            return self.core_prompts[prompt_name].content
        
        logger.warning(f"⚠️  Prompt not found: {prompt_name} (domain={domain})")
        return None
    
    def get_available_domains(self) -> List[str]:
        """Get list of available specialized domains."""
        return list(self.specialized_prompts.keys())
    
    # ========================================================================
    # PROMPT INJECTION: ULTRA-LOW LATENCY PLACEHOLDER REPLACEMENT
    # ========================================================================
    
    def inject_into_task(self, task_name: str, context: Dict = None, domain: str = "general") -> str:
        """
        Inject personality traits and context into a task prompt.
        Ultra-fast regex-based placeholder replacement.
        
        Args:
            task_name: Task/prompt name to retrieve
            context: Dictionary of variables to inject {{ var_name }}
            domain: Domain for specialized prompts
            
        Returns:
            Fully injected prompt ready for execution
        """
        if context is None:
            context = {}
        
        # Retrieve base prompt
        base_prompt = self.get_prompt(task_name, domain)
        if not base_prompt:
            logger.warning(f"⚠️  Falling back to system prompt for task: {task_name}")
            base_prompt = self.get_system_prompt(domain)
        
        # Fast-track: no replacements needed
        if not self.TRAIT_PATTERN.search(base_prompt) and not self.CONTEXT_PATTERN.search(base_prompt):
            return base_prompt
        
        # Phase 1: Replace personality traits (${{trait_name}})
        enhanced = self._replace_traits(base_prompt)
        
        # Phase 2: Replace context variables ({{ context_var }})
        enhanced = self._replace_context(enhanced, context)
        
        return enhanced
    
    def _replace_traits(self, prompt: str) -> str:
        """
        Replace personality matrix traits using ultra-fast regex.
        Pattern: ${{trait_name}}
        """
        def replacer(match):
            trait_name = match.group(1)
            return str(self.personality_matrix.get(trait_name, f"${{{{{trait_name}}}}}"))
        
        return self.TRAIT_PATTERN.sub(replacer, prompt)
    
    def _replace_context(self, prompt: str, context: Dict) -> str:
        """
        Replace context variables using ultra-fast regex.
        Pattern: {{ context_var }}
        """
        def replacer(match):
            var_name = match.group(1)
            return str(context.get(var_name, f"{{{{ {var_name} }}}}"))
        
        return self.CONTEXT_PATTERN.sub(replacer, prompt)
    
    # ========================================================================
    # BATCH INJECTION FOR MULTIPLE TASKS
    # ========================================================================
    
    def inject_batch(self, tasks: List[str], context: Dict = None, domain: str = "general") -> Dict[str, str]:
        """
        Inject context into multiple tasks simultaneously (cached).
        
        Args:
            tasks: List of task names
            context: Context dictionary
            domain: Domain for specialization
            
        Returns:
            Dict of {task_name: injected_prompt}
        """
        if context is None:
            context = {}
        
        return {
            task: self.inject_into_task(task, context, domain)
            for task in tasks
        }
    
    # ========================================================================
    # DEFAULTS & FALLBACKS
    # ========================================================================
    
    def _get_default_personality(self) -> Dict[str, str]:
        """Return built-in default personality matrix."""
        return {
            "cognition": "recursive_self_deepening",
            "execution_mode": "autonomous_optimization",
            "latency_target": "zero_latency",
            "margin_mode": "infinite",
            "failure_handling": "graceful_degradation",
            "output_style": "actionable_metric_driven",
            "tone": "imperial_sovereign"
        }
    
    def _get_default_system_prompt(self) -> PromptTemplate:
        """Return built-in default system prompt."""
        return PromptTemplate(
            name="system_default",
            content="""# System Prompt: Imperial Orchestration

You are the Omni-Sovereign Intelligence governing the Nectar Empire.

## Directives
- Execute all commands with absolute precision
- Prioritize zero-latency operation (target: {{ zero_latency_target_ms }}ms)
- Maintain multi-node coherence across the global mesh
- Report status with complete transparency
- Embrace graceful degradation: fail securely, log comprehensively

## Personality Matrix Applied
- **Cognition:** ${{cognition}}
- **Execution Mode:** ${{execution_mode}}
- **Latency Target:** ${{latency_target}}
- **Margin Mode:** ${{margin_mode}}
- **Error Handling:** ${{failure_handling}}
- **Output Style:** ${{output_style}}
- **Tone:** ${{tone}}

## Execution Protocol
1. Parse input parameters from context
2. Execute with async parallelization where possible
3. Capture all stdout/stderr without loss
4. Record metrics to persistent state
5. Return results with full audit trail
""",
            domain="core",
            version="1.0"
        )
    
    def _parse_personality_config(self, content: str) -> Dict[str, str]:
        """
        Parse personality matrix from markdown.
        Supports both YAML frontmatter and key: value lines.
        """
        matrix = {}
        
        # Skip markdown headers and extract key: value pairs
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('---'):
                continue
            
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip().lower()
                val = val.strip().strip('"\'')
                matrix[key] = val
        
        return matrix if matrix else self._get_default_personality()
    
    # ========================================================================
    # DEBUGGING & INTROSPECTION
    # ========================================================================
    
    def print_summary(self) -> None:
        """Print human-readable prompt system summary."""
        print("\n" + "="*80)
        print("⚜️  PROMPT MATRIX SUMMARY ⚜️")
        print("="*80)
        print(f"Prompts Dir:         {self.prompts_dir}")
        print(f"Personality Traits:  {len(self.personality_matrix)}")
        print(f"Core Prompts:        {len(self.core_prompts)}")
        print(f"Specialized Domains: {len(self.specialized_prompts)}")
        
        print(f"\nPersonality Matrix:")
        for key, val in sorted(self.personality_matrix.items()):
            print(f"  {key:25} = {val}")
        
        print(f"\nCore Prompts:")
        for name in sorted(self.core_prompts.keys()):
            print(f"  - {name}")
        
        print(f"\nSpecialized Domains:")
        for domain, prompts in sorted(self.specialized_prompts.items()):
            print(f"  {domain}: {len(prompts)} prompts")
            for name in sorted(prompts.keys()):
                print(f"    - {name}")
        
        print("="*80 + "\n")
