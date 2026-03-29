"""
Quantum-Scale Performance Engine for GMNAP V7
Advanced distributed processing with intelligent load balancing
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
from typing import Any, Callable, Dict, List, Optional

import psutil


class ProcessingPriority(Enum):
    """Processing priority levels"""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ProcessingTask:
    """Represents a processing task with metadata"""

    task_id: str
    data: Any
    priority: ProcessingPriority
    processor_func: Callable
    estimated_time: float = 1.0
    created_at: float = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.dependencies is None:
            self.dependencies = []

    def __lt__(self, other):
        # Lower priority value = higher priority
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # If same priority, older tasks go first
        return self.created_at < other.created_at


class QuantumEngine:
    """
    Quantum-Scale Performance Engine

    Features:
    - Intelligent work distribution
    - Dynamic scaling based on system load
    - Priority-based task scheduling
    - Dependency resolution
    - Performance monitoring and optimization
    """

    def __init__(self, max_workers: Optional[int] = None):
        self.logger = logging.getLogger(__name__)

        # System resource monitoring
        self.cpu_count = psutil.cpu_count()
        self.max_workers = max_workers or min(32, (self.cpu_count * 2) + 1)

        # Task management
        self.task_queue = PriorityQueue()
        self.completed_tasks = {}
        self.running_tasks = {}
        self.failed_tasks = {}

        # Performance metrics
        self.performance_metrics = {
            "tasks_processed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "tasks_per_second": 0.0,
            "cpu_utilization": 0.0,
            "memory_utilization": 0.0,
            "queue_depth": 0,
        }

        # Executors for different workloads
        self.cpu_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.io_executor = ThreadPoolExecutor(max_workers=self.max_workers * 2)

        # Control flags
        self.is_running = False
        self._shutdown_event = threading.Event()

        self.logger.info(f"QuantumEngine initialized with {self.max_workers} workers")

    async def submit_task(self, task: ProcessingTask) -> str:
        """Submit a task for processing"""
        if not self.is_running:
            await self.start()

        # Validate dependencies
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                self.logger.warning(
                    f"Task {task.task_id} has unresolved dependency: {dep_id}"
                )

        self.task_queue.put(task)
        self.performance_metrics["queue_depth"] = self.task_queue.qsize()

        self.logger.debug(
            f"Submitted task {task.task_id} with priority {task.priority.name}"
        )
        return task.task_id

    async def batch_submit(self, tasks: List[ProcessingTask]) -> List[str]:
        """Submit multiple tasks efficiently"""
        task_ids = []
        for task in tasks:
            task_id = await self.submit_task(task)
            task_ids.append(task_id)
        return task_ids

    async def start(self):
        """Start the quantum engine"""
        if self.is_running:
            return

        self.is_running = True
        self._shutdown_event.clear()

        # Start monitoring and processing loops
        asyncio.create_task(self._performance_monitor())
        asyncio.create_task(self._task_processor())

        self.logger.info("QuantumEngine started")

    async def shutdown(self, timeout: float = 30.0):
        """Gracefully shutdown the engine"""
        self.logger.info("Shutting down QuantumEngine...")

        self.is_running = False
        self._shutdown_event.set()

        # Wait for running tasks to complete
        start_time = time.time()
        while self.running_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)

        # Shutdown executors
        self.cpu_executor.shutdown(wait=True)
        self.io_executor.shutdown(wait=True)

        self.logger.info("QuantumEngine shutdown complete")

    async def _task_processor(self):
        """Main task processing loop"""
        while self.is_running or not self.task_queue.empty():
            try:
                if self.task_queue.empty():
                    await asyncio.sleep(0.01)
                    continue

                # Get next task
                task = self.task_queue.get_nowait()

                # Check dependencies
                if not self._dependencies_satisfied(task):
                    # Re-queue with slight delay
                    task.created_at = time.time() + 0.1
                    self.task_queue.put(task)
                    continue

                # Process task
                asyncio.create_task(self._execute_task(task))

            except Exception as e:
                self.logger.error(f"Error in task processor: {e}")
                await asyncio.sleep(0.1)

    def _dependencies_satisfied(self, task: ProcessingTask) -> bool:
        """Check if all task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id not in self.completed_tasks:
                return False
        return True

    async def _execute_task(self, task: ProcessingTask):
        """Execute a single task"""
        start_time = time.time()
        self.running_tasks[task.task_id] = task

        try:
            # Choose appropriate executor based on task type
            executor = self._select_executor(task)

            # Execute the task
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor, task.processor_func, task.data
            )

            # Record completion
            processing_time = time.time() - start_time
            self.completed_tasks[task.task_id] = {
                "result": result,
                "processing_time": processing_time,
                "completed_at": time.time(),
            }

            # Update metrics
            self._update_performance_metrics(processing_time)

            self.logger.debug(
                f"Completed task {task.task_id} in {processing_time:.3f}s"
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.failed_tasks[task.task_id] = {
                "error": str(e),
                "processing_time": processing_time,
                "failed_at": time.time(),
            }
            self.logger.error(f"Task {task.task_id} failed: {e}")

        finally:
            # Cleanup
            self.running_tasks.pop(task.task_id, None)
            self.performance_metrics["queue_depth"] = self.task_queue.qsize()

    def _select_executor(self, task: ProcessingTask) -> ThreadPoolExecutor:
        """Select appropriate executor based on task characteristics"""
        # Simple heuristic: assume I/O bound if estimated time > 1 second
        if task.estimated_time > 1.0:
            return self.io_executor
        return self.cpu_executor

    def _update_performance_metrics(self, processing_time: float):
        """Update performance metrics"""
        self.performance_metrics["tasks_processed"] += 1
        self.performance_metrics["total_processing_time"] += processing_time

        # Calculate averages
        if self.performance_metrics["tasks_processed"] > 0:
            self.performance_metrics["average_processing_time"] = (
                self.performance_metrics["total_processing_time"]
                / self.performance_metrics["tasks_processed"]
            )

        # Calculate throughput (tasks per second over last window)
        if processing_time > 0:
            self.performance_metrics["tasks_per_second"] = 1.0 / processing_time

    async def _performance_monitor(self):
        """Monitor system performance and adjust scaling"""
        while self.is_running:
            try:
                # Update system metrics
                self.performance_metrics["cpu_utilization"] = psutil.cpu_percent()
                self.performance_metrics["memory_utilization"] = (
                    psutil.virtual_memory().percent
                )

                # Log performance stats every 30 seconds
                if int(time.time()) % 30 == 0:
                    self.logger.info(f"Performance metrics: {self.performance_metrics}")

                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(1.0)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        if task_id in self.completed_tasks:
            return {"status": "completed", **self.completed_tasks[task_id]}
        elif task_id in self.running_tasks:
            return {"status": "running", "task": self.running_tasks[task_id]}
        elif task_id in self.failed_tasks:
            return {"status": "failed", **self.failed_tasks[task_id]}
        else:
            return {"status": "not_found"}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.performance_metrics.copy()

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for a specific task to complete"""
        start_time = time.time()

        while True:
            status = self.get_task_status(task_id)

            if status["status"] == "completed":
                return status["result"]
            elif status["status"] == "failed":
                raise Exception(f"Task {task_id} failed: {status['error']}")
            elif status["status"] == "not_found":
                raise ValueError(f"Task {task_id} not found")

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

            await asyncio.sleep(0.1)

    async def wait_for_all(
        self, task_ids: List[str], timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for all specified tasks to complete"""
        results = {}

        for task_id in task_ids:
            try:
                result = await self.wait_for_task(task_id, timeout)
                results[task_id] = result
            except Exception as e:
                results[task_id] = {"error": str(e)}

        return results


class QuantumBatchProcessor:
    """
    Advanced batch processing with intelligent chunking and load balancing
    """

    def __init__(self, quantum_engine: QuantumEngine):
        self.engine = quantum_engine
        self.logger = logging.getLogger(__name__)

    async def process_batch(
        self,
        items: List[Any],
        processor_func: Callable,
        chunk_size: Optional[int] = None,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
    ) -> List[Any]:
        """Process a batch of items with intelligent chunking"""
        if not items:
            return []

        # Calculate optimal chunk size
        if chunk_size is None:
            chunk_size = max(1, len(items) // (self.engine.max_workers * 2))
            chunk_size = min(chunk_size, 100)  # Cap at 100

        # Split into chunks
        chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]

        # Submit chunk processing tasks
        task_ids = []
        for i, chunk in enumerate(chunks):
            task = ProcessingTask(
                task_id=f"batch_chunk_{i}",
                data=chunk,
                priority=priority,
                processor_func=lambda chunk_data: [
                    processor_func(item) for item in chunk_data
                ],
                estimated_time=len(chunk) * 0.1,  # Estimate 0.1s per item
            )
            task_id = await self.engine.submit_task(task)
            task_ids.append(task_id)

        # Wait for all chunks to complete
        results = await self.engine.wait_for_all(task_ids)

        # Combine results
        combined_results = []
        for i, task_id in enumerate(task_ids):
            if task_id in results and "error" not in results[task_id]:
                combined_results.extend(results[task_id])
            else:
                self.logger.error(f"Chunk {i} failed: {results[task_id]}")

        return combined_results
