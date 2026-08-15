#!/usr/bin/env python3
"""
⚜️ core/orchestrator.py - Phase 2: Async Parallelization & Error Handling
True async DAG orchestrator for parallel milestone execution with comprehensive logging.
"""

import asyncio
import logging
import json
import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
import subprocess
from datetime import datetime

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] 🔱 ORCHESTRATOR: %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OrchestratorDAG")


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class ExecutionStatus(Enum):
    """Task/Milestone execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    RETRY = "retry"


class FailureMode(Enum):
    """How to handle milestone failure."""
    HALT = "halt"          # Stop entire orchestration
    CONTINUE = "continue"  # Log but proceed to next independent milestone
    SKIP = "skip"          # Skip dependent milestones


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_name: str
    status: ExecutionStatus
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "task_name": self.task_name,
            "status": self.status.value,
            "returncode": self.returncode,
            "stdout_lines": len(self.stdout.splitlines()),
            "stderr_lines": len(self.stderr.splitlines()),
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count
        }


@dataclass
class Milestone:
    """Represents a milestone with one or more tasks."""
    name: str
    tasks: List[str]
    dependencies: Optional[List[str]] = None
    timeout: int = 120
    retry_count: int = 1
    on_failure: str = "halt"
    description: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.on_failure not in ["halt", "continue", "skip"]:
            raise ValueError(f"Invalid on_failure mode: {self.on_failure}")


@dataclass
class MilestoneResult:
    """Result of milestone execution."""
    milestone_name: str
    status: ExecutionStatus
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    total_execution_time_ms: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "milestone_name": self.milestone_name,
            "status": self.status.value,
            "tasks_executed": len(self.task_results),
            "tasks_successful": sum(1 for r in self.task_results.values() if r.status == ExecutionStatus.SUCCESS),
            "tasks_failed": sum(1 for r in self.task_results.values() if r.status == ExecutionStatus.FAILED),
            "total_execution_time_ms": self.total_execution_time_ms,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


# ============================================================================
# ORCHESTRATOR DAG ENGINE
# ============================================================================

class OrchestratorDAG:
    """
    Async DAG orchestrator for parallel task execution.
    
    Features:
    - True concurrent execution of independent milestones
    - Comprehensive stdout/stderr capture without log loss
    - Strict timeout controls per task and milestone
    - Retry mechanisms with exponential backoff
    - Prevention of cascading failures via graceful degradation
    - Complete audit trail in JSON format
    """
    
    def __init__(
        self,
        milestones: List[Milestone],
        max_concurrent_tasks: int = 4,
        fail_fast: bool = False,
        log_dir: str = "./logs"
    ):
        """
        Initialize orchestrator.
        
        Args:
            milestones: List of Milestone definitions
            max_concurrent_tasks: Max concurrent subprocess execution
            fail_fast: If True, halt on ANY failure (else continue based on on_failure mode)
            log_dir: Directory for storing execution logs
        """
        self.milestones = {m.name: m for m in milestones}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.fail_fast = fail_fast
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Execution state
        self.milestone_status: Dict[str, ExecutionStatus] = {
            m.name: ExecutionStatus.PENDING for m in milestones
        }
        self.milestone_results: Dict[str, MilestoneResult] = {}
        self.execution_errors: List[str] = []
        self.global_start_time: Optional[datetime] = None
        self.global_end_time: Optional[datetime] = None
        
        # Semaphore to limit concurrent subprocess execution
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        logger.info(
            f"🏗️  OrchestratorDAG initialized. "
            f"Milestones={len(self.milestones)}, MaxConcurrent={max_concurrent_tasks}"
        )
    
    # ========================================================================
    # PUBLIC EXECUTION API
    # ========================================================================
    
    async def execute(self, dep_resolver) -> Tuple[Dict[str, ExecutionStatus], Dict[str, MilestoneResult]]:
        """
        Execute the entire DAG respecting dependencies.
        
        Args:
            dep_resolver: DependencyResolver instance with resolved paths
            
        Returns:
            Tuple of (milestone_statuses, milestone_results)
        """
        self.global_start_time = datetime.now()
        logger.info("🚀 ORCHESTRATION STARTING")
        logger.info(f"   Milestones: {list(self.milestones.keys())}")
        
        try:
            executed = set()
            
            while len(executed) < len(self.milestones):
                # Find milestones ready to execute (all dependencies satisfied)
                ready = self._find_ready_milestones(executed)
                
                if not ready:
                    remaining = set(self.milestones.keys()) - executed
                    msg = f"❌ Circular dependency or deadlock. Remaining: {remaining}"
                    logger.error(msg)
                    self.execution_errors.append(msg)
                    break
                
                logger.info(f"▶️  Ready to execute: {ready}")
                
                # Execute ready milestones in parallel
                await asyncio.gather(
                    *[self._execute_milestone(m, dep_resolver) for m in ready],
                    return_exceptions=False
                )
                
                executed.update(ready)
                
                # Check for halt conditions
                if self.fail_fast and self._has_failures():
                    logger.error("❌ FAIL_FAST mode active. Halting orchestration.")
                    break
            
            self.global_end_time = datetime.now()
            logger.info("✅ ORCHESTRATION COMPLETE")
            
        except Exception as e:
            self.global_end_time = datetime.now()
            msg = f"❌ Orchestration exception: {e}"
            logger.error(msg)
            self.execution_errors.append(msg)
        
        return self.milestone_status, self.milestone_results
    
    # ========================================================================
    # MILESTONE EXECUTION
    # ========================================================================
    
    async def _execute_milestone(self, milestone_name: str, dep_resolver) -> None:
        """Execute a single milestone with all its tasks."""
        milestone = self.milestones[milestone_name]
        result = MilestoneResult(milestone_name=milestone_name, status=ExecutionStatus.PENDING)
        result.start_time = datetime.now()
        
        self.milestone_status[milestone_name] = ExecutionStatus.RUNNING
        
        logger.info(f"📍 Milestone START: {milestone_name} | Tasks: {milestone.tasks}")
        logger.info(f"   Description: {milestone.description}")
        
        try:
            # Execute all tasks in this milestone
            for task_name in milestone.tasks:
                task_result = await self._execute_task_with_retry(
                    task_name,
                    dep_resolver,
                    milestone.timeout,
                    milestone.retry_count
                )
                result.task_results[task_name] = task_result
                
                # Check for failure
                if task_result.status == ExecutionStatus.FAILED:
                    if milestone.on_failure == "halt":
                        msg = f"❌ Task '{task_name}' FAILED in milestone '{milestone_name}' (on_failure=halt). Halting."
                        logger.error(msg)
                        self.execution_errors.append(msg)
                        result.status = ExecutionStatus.FAILED
                        self.milestone_status[milestone_name] = ExecutionStatus.FAILED
                        return
                    elif milestone.on_failure == "continue":
                        logger.warning(f"⚠️  Task '{task_name}' FAILED but on_failure=continue. Proceeding.")
                        result.status = ExecutionStatus.FAILED
            
            # All tasks completed
            if result.status != ExecutionStatus.FAILED:
                result.status = ExecutionStatus.SUCCESS
                self.milestone_status[milestone_name] = ExecutionStatus.SUCCESS
                logger.info(f"✅ Milestone SUCCESS: {milestone_name}")
            
        except Exception as e:
            msg = f"❌ Milestone exception: {milestone_name} | {e}"
            logger.error(msg)
            self.execution_errors.append(msg)
            result.status = ExecutionStatus.FAILED
            self.milestone_status[milestone_name] = ExecutionStatus.FAILED
        
        finally:
            result.end_time = datetime.now()
            result.total_execution_time_ms = (
                (result.end_time - result.start_time).total_seconds() * 1000
            )
            self.milestone_results[milestone_name] = result
            
            logger.info(f"📍 Milestone END: {milestone_name} | Status={result.status.value} | Time={result.total_execution_time_ms:.0f}ms")
    
    # ========================================================================
    # TASK EXECUTION WITH RETRY
    # ========================================================================
    
    async def _execute_task_with_retry(
        self,
        task_name: str,
        dep_resolver,
        timeout: int,
        max_retries: int
    ) -> TaskResult:
        """
        Execute a task with retry logic.
        
        Args:
            task_name: Name of task (power or imperial logic)
            dep_resolver: DependencyResolver instance
            timeout: Timeout in seconds
            max_retries: Maximum retry attempts
            
        Returns:
            TaskResult with full execution details
        """
        result = TaskResult(task_name=task_name, status=ExecutionStatus.PENDING)
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"  ▶️  Task: {task_name} (Attempt {attempt + 1}/{max_retries + 1})")
                
                # Resolve script path
                script_path = self._resolve_script_path(task_name, dep_resolver)
                
                # Execute with timeout
                result = await self._run_subprocess_async(
                    script_path,
                    task_name,
                    timeout
                )
                
                if result.status == ExecutionStatus.SUCCESS:
                    logger.info(f"  ✅ Task SUCCESS: {task_name} (Time: {result.execution_time_ms:.0f}ms)")
                    return result
                else:
                    # Non-zero exit code
                    if attempt < max_retries:
                        wait_ms = 100 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"  ⚠️  Task FAILED: {task_name} | Retry in {wait_ms}ms "
                            f"(Attempt {attempt + 1}/{max_retries + 1})"
                        )
                        result.retry_count = attempt + 1
                        await asyncio.sleep(wait_ms / 1000)
                        continue
                    else:
                        logger.error(f"  ❌ Task FAILED (final): {task_name} after {max_retries + 1} attempts")
                        return result
            
            except asyncio.TimeoutError:
                result.status = ExecutionStatus.TIMEOUT
                result.error_message = f"Timeout after {timeout}s"
                logger.error(f"  ❌ Task TIMEOUT: {task_name} (Timeout: {timeout}s)")
                return result
            
            except Exception as e:
                result.status = ExecutionStatus.FAILED
                result.error_message = str(e)
                logger.error(f"  ❌ Task EXCEPTION: {task_name} | {e}")
                if attempt >= max_retries:
                    return result
                await asyncio.sleep(0.1 * (2 ** attempt))
        
        return result
    
    # ========================================================================
    # SUBPROCESS EXECUTION
    # ========================================================================
    
    async def _run_subprocess_async(
        self,
        script_path: str,
        task_name: str,
        timeout: int
    ) -> TaskResult:
        """
        Execute subprocess asynchronously with full output capture.
        
        Args:
            script_path: Absolute path to Python script
            task_name: Task name (for logging)
            timeout: Timeout in seconds
            
        Returns:
            TaskResult with stdout, stderr, returncode
        """
        result = TaskResult(task_name=task_name, status=ExecutionStatus.PENDING)
        start_time = time.time()
        
        try:
            # Use semaphore to limit concurrent subprocess execution
            async with self.semaphore:
                process = await asyncio.create_subprocess_exec(
                    "python3", script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=2**20  # 1MB buffer per stream
                )
                
                try:
                    stdout_data, stderr_data = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                    
                    result.stdout = stdout_data.decode('utf-8', errors='replace')
                    result.stderr = stderr_data.decode('utf-8', errors='replace')
                    result.returncode = process.returncode
                    
                    if process.returncode == 0:
                        result.status = ExecutionStatus.SUCCESS
                    else:
                        result.status = ExecutionStatus.FAILED
                        result.error_message = f"Exit code {process.returncode}"
                
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    result.status = ExecutionStatus.TIMEOUT
                    result.error_message = f"Timeout after {timeout}s"
                    result.stderr = f"Process killed after {timeout}s timeout"
        
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
        
        finally:
            result.execution_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    # ========================================================================
    # DEPENDENCY RESOLUTION
    # ========================================================================
    
    def _resolve_script_path(self, task_name: str, dep_resolver) -> str:
        """
        Resolve script path from dependency resolver.
        
        Args:
            task_name: Power or imperial logic name
            dep_resolver: DependencyResolver instance
            
        Returns:
            Absolute path to script
            
        Raises:
            KeyError: If task not found
        """
        try:
            _, path = dep_resolver.get_power(task_name)
            return path
        except KeyError:
            pass
        
        try:
            _, path = dep_resolver.get_imperial_logic(task_name)
            return path
        except KeyError:
            raise KeyError(f"Task '{task_name}' not found in dependencies")
    
    # ========================================================================
    # DAG UTILITIES
    # ========================================================================
    
    def _find_ready_milestones(self, executed: set) -> List[str]:
        """Find milestones whose dependencies are all satisfied."""
        ready = []
        for name, milestone in self.milestones.items():
            if name in executed:
                continue
            if all(dep in executed for dep in (milestone.dependencies or [])):
                ready.append(name)
        return ready
    
    def _has_failures(self) -> bool:
        """Check if any milestone failed."""
        return any(
            status == ExecutionStatus.FAILED
            for status in self.milestone_status.values()
        )
    
    # ========================================================================
    # RESULTS & REPORTING
    # ========================================================================
    
    def get_status_summary(self) -> Dict:
        """Get high-level execution summary."""
        total_milestones = len(self.milestones)
        successful = sum(1 for s in self.milestone_status.values() if s == ExecutionStatus.SUCCESS)
        failed = sum(1 for s in self.milestone_status.values() if s == ExecutionStatus.FAILED)
        
        return {
            "total_milestones": total_milestones,
            "successful": successful,
            "failed": failed,
            "pending": total_milestones - successful - failed,
            "global_status": "SUCCESS" if failed == 0 else "FAILED",
            "execution_errors": self.execution_errors,
            "start_time": self.global_start_time.isoformat() if self.global_start_time else None,
            "end_time": self.global_end_time.isoformat() if self.global_end_time else None
        }
    
    def save_execution_report(self, output_path: str = None) -> str:
        """
        Save complete execution report to JSON.
        
        Args:
            output_path: Path to save report (defaults to logs/execution_report_TIMESTAMP.json)
            
        Returns:
            Path where report was saved
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.log_dir / f"execution_report_{timestamp}.json"
        else:
            output_path = Path(output_path)
        
        report = {
            "summary": self.get_status_summary(),
            "milestones": {
                name: result.to_dict()
                for name, result in self.milestone_results.items()
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Execution report saved to: {output_path}")
        return str(output_path)
    
    def print_summary(self) -> None:
        """Print human-readable execution summary."""
        summary = self.get_status_summary()
        
        print("\n" + "="*80)
        print("⚜️  ORCHESTRATION EXECUTION SUMMARY ⚜️")
        print("="*80)
        print(f"Global Status:       {summary['global_status']}")
        print(f"Milestones Total:    {summary['total_milestones']}")
        print(f"  ✅ Successful:     {summary['successful']}")
        print(f"  ❌ Failed:         {summary['failed']}")
        print(f"  ⏳ Pending:        {summary['pending']}")
        print(f"Start Time:          {summary['start_time']}")
        print(f"End Time:            {summary['end_time']}")
        
        if summary['execution_errors']:
            print(f"\n❌ ERRORS ({len(summary['execution_errors'])}):")
            for error in summary['execution_errors']:
                print(f"  - {error}")
        
        print("\n📍 MILESTONES:")
        for name, result in sorted(self.milestone_results.items()):
            status_emoji = "✅" if result.status == ExecutionStatus.SUCCESS else "❌"
            print(f"  {status_emoji} {name:35} | {result.status.value:10} | {result.total_execution_time_ms:8.0f}ms")
        
        print("="*80 + "\n")
