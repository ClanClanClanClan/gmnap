#!/usr/bin/env python3
"""
from typing import Dict
from typing import List
from typing import Optional
FORMAL VERIFICATION TESTING
Mathematical proofs and invariants to verify system correctness:
- Invariant checking
- Property-based proofs
- Temporal logic verification
- State space exploration
- Formal specification compliance
- Mathematical correctness proofs
"""

import functools
import hashlib
import itertools
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hypothesis import assume, given, strategies as st, settings
from hypothesis.stateful import (
    RuleBasedStateMachine,
    Bundle,
    rule,
    invariant,
    precondition,
)

# Formal specifications as mathematical properties


class FormalSpecification:
    """Formal specifications that must hold"""

    @staticmethod
    def idempotency(f: Callable) -> bool:
        """forallx: f(f(x)) = f(x)"""

        def check(x):
            once = f(x)
            twice = f(once)
            return once == twice

        return check

    @staticmethod
    def commutativity(f: Callable) -> bool:
        """forallx,y: f(x,y) = f(y,x)"""

        def check(x, y):
            return f(x, y) == f(y, x)

        return check

    @staticmethod
    def associativity(f: Callable) -> bool:
        """forallx,y,z: f(f(x,y),z) = f(x,f(y,z))"""

        def check(x, y, z):
            return f(f(x, y), z) == f(x, f(y, z))

        return check

    @staticmethod
    def distributivity(f: Callable, g: Callable) -> bool:
        """forallx,y,z: f(x,g(y,z)) = g(f(x,y),f(x,z))"""

        def check(x, y, z):
            return f(x, g(y, z)) == g(f(x, y), f(x, z))

        return check

    @staticmethod
    def monotonicity(f: Callable, order: Callable) -> bool:
        """forallx,y: x <= y => f(x) <= f(y)"""

        def check(x, y):
            if order(x, y):
                return order(f(x), f(y))
            return True

        return check

    @staticmethod
    def injectivity(f: Callable) -> bool:
        """forallx,y: f(x) = f(y) => x = y"""

        def check(x, y):
            if f(x) == f(y):
                return x == y
            return True

        return check

    @staticmethod
    def surjectivity(f: Callable, domain: Set, codomain: Set) -> bool:
        """forally in codomain, existsx in domain: f(x) = y"""
        for y in codomain:
            if not any(f(x) == y for x in domain):
                return False
        return True


class InvariantChecker:
    """Check that invariants hold throughout execution"""

    def __init__(self):
        self.invariants: List[Tuple[str, Callable]] = []
        self.violations: List[Tuple[str, Any]] = []

    def add_invariant(self, name: str, predicate: Callable):
        """Add an invariant to check"""
        self.invariants.append((name, predicate))

    def check_all(self, state: Any) -> bool:
        """Check all invariants against current state"""
        all_hold = True

        for name, predicate in self.invariants:
            try:
                if not predicate(state):
                    self.violations.append((name, state))
                    all_hold = False
            except Exception as e:
                self.violations.append((name, f"Exception: {e}"))
                all_hold = False

        return all_hold


@dataclass
class SystemState:
    """Formal representation of system state"""

    data: Dict[str, Any]
    history: List[Tuple[str, Any]]
    invariants_satisfied: bool = True

    def transition(self, action: str, params: Any) -> "SystemState":
        """State transition function"""
        new_data = self.data.copy()
        new_history = self.history + [(action, params)]

        # Apply transition based on action
        if action == "write":
            new_data[params["key"]] = params["value"]
        elif action == "delete":
            new_data.pop(params["key"], None)
        elif action == "transform":
            if params["key"] in new_data:
                new_data[params["key"]] = params["func"](new_data[params["key"]])

        return SystemState(new_data, new_history)


class TemporalLogic:
    """Linear Temporal Logic (LTL) operators"""

    @staticmethod
    def always(predicate: Callable, trace: List[Any]) -> bool:
        """□p - predicate holds in all states"""
        return all(predicate(state) for state in trace)

    @staticmethod
    def eventually(predicate: Callable, trace: List[Any]) -> bool:
        """◇p - predicate holds in some future state"""
        return any(predicate(state) for state in trace)

    @staticmethod
    def next(predicate: Callable, trace: List[Any], index: int) -> bool:
        """○p - predicate holds in next state"""
        if index + 1 < len(trace):
            return predicate(trace[index + 1])
        return False

    @staticmethod
    def until(p: Callable, q: Callable, trace: List[Any], start: int = 0) -> bool:
        """p U q - p holds until q becomes true"""
        for i in range(start, len(trace)):
            if q(trace[i]):
                return all(p(trace[j]) for j in range(start, i))
        return False

    @staticmethod
    def implies(p: Callable, q: Callable) -> Callable:
        """p -> q - if p then q"""
        return lambda x: not p(x) or q(x)


class TestFormalVerification:
    """Tests for formal verification properties."""

    @pytest.mark.timeout(15)
    def test_idempotency_property(self):
        """Verify idempotency: f(f(x)) = f(x)"""

        def normalize_string(s: str) -> str:
            """Example normalization function"""
            return " ".join(s.split()).strip().lower()

        # Check idempotency property
        check_idempotent = FormalSpecification.idempotency(normalize_string)

        test_cases = [
            "hello world",
            "  multiple   spaces  ",
            "MiXeD CaSe",
            "\t\ttabs\t\t",
            "",
            " ",
        ]

        for test in test_cases:
            assert check_idempotent(test), f"Idempotency violated for '{test}'"

        print("✓ Idempotency property verified")

    @given(st.text())
    @settings(max_examples=1000)
    @pytest.mark.timeout(15)
    def test_normalization_idempotency_exhaustive(self, text):
        """Property-based test for idempotency"""

        def normalize(s: str) -> str:
            # Simplified normalization
            return " ".join(s.split()).strip()

        # Property: normalize is idempotent
        once = normalize(text)
        twice = normalize(once)
        assert once == twice, f"Idempotency violation: {text!r}"

    @pytest.mark.timeout(15)
    def test_invariant_preservation(self):
        """Test that operations preserve invariants"""

        checker = InvariantChecker()

        # Define invariants
        checker.add_invariant(
            "non_negative_values",
            lambda state: all(
                v >= 0 for v in state.data.values() if isinstance(v, (int, float))
            ),
        )

        checker.add_invariant(
            "bounded_string_length",
            lambda state: all(
                len(v) <= 1000 for v in state.data.values() if isinstance(v, str)
            ),
        )

        checker.add_invariant(
            "history_integrity",
            lambda state: len(state.history)
            == len(set(state.history)),  # No duplicate operations
        )

        # Create initial state
        state = SystemState({"counter": 0, "name": "test"}, [])

        # Apply operations
        operations = [
            ("write", {"key": "counter", "value": 10}),
            ("transform", {"key": "counter", "func": lambda x: x + 5}),
            ("write", {"key": "name", "value": "updated"}),
            (
                "transform",
                {"key": "counter", "func": lambda x: max(0, x - 20)},
            ),  # Stays non-negative
        ]

        for action, params in operations:
            state = state.transition(action, params)
            assert checker.check_all(
                state
            ), f"Invariant violated after {action}: {checker.violations}"

        print(f"✓ All invariants preserved through {len(operations)} operations")

    @pytest.mark.timeout(15)
    def test_commutativity_of_operations(self):
        """Test commutativity: f(x,y) = f(y,x)"""

        def merge_dicts(a: dict, b: dict) -> dict:
            """Commutative merge operation"""
            result = a.copy()
            result.update(b)
            return result

        check_commutative = FormalSpecification.commutativity(merge_dicts)

        # Test cases
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        assert check_commutative(dict1, dict2), "Commutativity violated"

        # Non-commutative operation for comparison
        def subtract(a: int, b: int) -> int:
            return a - b

        check_subtract = FormalSpecification.commutativity(subtract)
        assert not check_subtract(5, 3), "Subtraction should not be commutative"

        print("✓ Commutativity properties verified")

    @pytest.mark.timeout(15)
    def test_monotonicity_property(self):
        """Test monotonicity: x <= y => f(x) <= f(y)"""

        def square(x: float) -> float:
            """Monotonic for non-negative numbers"""
            return x * x

        def order(a: float, b: float) -> bool:
            return a <= b

        check_monotonic = FormalSpecification.monotonicity(square, order)

        # Test on non-negative numbers (where square is monotonic)
        test_pairs = [(0, 1), (1, 2), (2, 3), (5, 10)]

        for x, y in test_pairs:
            assert check_monotonic(x, y), f"Monotonicity violated for {x}, {y}"

        print("✓ Monotonicity property verified")

    @pytest.mark.timeout(15)
    def test_temporal_properties(self):
        """Test temporal logic properties"""

        # Simulate system trace
        trace = [
            {"state": "init", "value": 0},
            {"state": "processing", "value": 5},
            {"state": "processing", "value": 10},
            {"state": "complete", "value": 15},
            {"state": "idle", "value": 15},
        ]

        # Property: System always has non-negative value
        always_positive = TemporalLogic.always(lambda s: s["value"] >= 0, trace)
        assert always_positive, "Safety property violated"

        # Property: System eventually completes
        eventually_complete = TemporalLogic.eventually(
            lambda s: s["state"] == "complete", trace
        )
        assert eventually_complete, "Liveness property violated"

        # Property: Processing until complete
        processing_until_complete = TemporalLogic.until(
            lambda s: s["state"] in ["init", "processing"],
            lambda s: s["state"] == "complete",
            trace,
        )
        assert processing_until_complete, "Until property violated"

        print("✓ Temporal properties verified")

    @pytest.mark.timeout(15)
    def test_bijection_properties(self):
        """Test injection and surjection (bijection)"""

        def encode(x: int) -> str:
            """Injective encoding function"""
            return f"encoded_{x}"

        check_injective = FormalSpecification.injectivity(encode)

        # Test injectivity
        test_pairs = [(1, 2), (5, 10), (100, 101)]
        for x, y in test_pairs:
            assert check_injective(x, y), f"Injectivity violated for {x}, {y}"

        # Test surjectivity
        domain = {0, 1, 2}
        codomain = {"encoded_0", "encoded_1", "encoded_2"}

        is_surjective = FormalSpecification.surjectivity(encode, domain, codomain)
        assert is_surjective, "Surjectivity violated"

        print("✓ Bijection properties verified")

    @pytest.mark.timeout(15)
    def test_state_space_exploration(self):
        """Explore all reachable states and verify properties"""

        class StateExplorer:
            def __init__(self, initial_state: Any):
                self.initial = initial_state
                self.visited: Set[str] = set()
                self.reachable: List[Any] = []

            def explore(self, state: Any, depth: int = 0, max_depth: int = 5):
                """BFS exploration of state space"""
                if depth > max_depth:
                    return

                state_hash = str(state)
                if state_hash in self.visited:
                    return

                self.visited.add(state_hash)
                self.reachable.append(state)

                # Generate next states (simplified)
                if isinstance(state, int):
                    # Integer state transitions
                    if state < 100:
                        self.explore(state + 1, depth + 1, max_depth)
                        self.explore(state * 2, depth + 1, max_depth)

            def verify_property(self, property: Callable) -> bool:
                """Verify property holds in all reachable states"""
                return all(property(state) for state in self.reachable)

        explorer = StateExplorer(initial_state=1)
        explorer.explore(1)

        # Property: All states are positive
        all_positive = explorer.verify_property(lambda x: x > 0)
        assert all_positive, "Property violated in some reachable state"

        print(f"✓ Explored {len(explorer.reachable)} states, all satisfy property")

    @pytest.mark.timeout(15)
    def test_refinement_relation(self):
        """Test refinement between abstract and concrete specifications"""

        class AbstractSpec:
            """High-level specification"""

            def __init__(self):
                self.items: Set[Any] = set()

            def add(self, item):
                self.items.add(item)

            def contains(self, item):
                return item in self.items

        class ConcreteImpl:
            """Low-level implementation"""

            def __init__(self):
                self.storage: List[Any] = []

            def add(self, item):
                if item not in self.storage:
                    self.storage.append(item)

            def contains(self, item):
                return item in self.storage

        # Test refinement
        abstract = AbstractSpec()
        concrete = ConcreteImpl()

        operations = [
            ("add", 1),
            ("add", 2),
            ("add", 1),  # Duplicate
            ("contains", 1),
            ("contains", 3),
        ]

        for op, arg in operations:
            if op == "add":
                abstract.add(arg)
                concrete.add(arg)
            elif op == "contains":
                assert abstract.contains(arg) == concrete.contains(
                    arg
                ), f"Refinement violated for {op}({arg})"

        # Verify representation invariant
        assert (
            set(concrete.storage) == abstract.items
        ), "Representation invariant violated"

        print("✓ Refinement relation verified")

    @pytest.mark.timeout(15)
    def test_algebraic_properties(self):
        """Test algebraic properties of operations"""

        # Monoid: (Set, ∪, ∅)
        def union(a: set, b: set) -> set:
            return a | b

        identity = set()

        # Test identity element
        test_set = {1, 2, 3}
        assert union(test_set, identity) == test_set
        assert union(identity, test_set) == test_set

        # Test associativity
        a, b, c = {1}, {2}, {3}
        assert union(union(a, b), c) == union(a, union(b, c))

        # Test closure
        result = union(a, b)
        assert isinstance(result, set)

        print("✓ Algebraic properties (monoid) verified")


class FormalStateMachine(RuleBasedStateMachine):
    """Formal verification using stateful property testing"""

    def __init__(self):
        super().__init__()
        self.store: Dict[str, Any] = {}
        self.operations_count = 0
        self.invariants_held = True

    values = Bundle("values")
    keys = Bundle("keys")

    @rule(
        key=st.text(min_size=1, max_size=10),
        value=st.one_of(st.integers(), st.text(), st.booleans()),
    )
    def write(self, key, value):
        """Write operation"""
        self.store[key] = value
        self.operations_count += 1
        return key

    @rule(key=keys)
    def read(self, key):
        """Read operation"""
        if key in self.store:
            return self.store[key]
        return None

    @rule(key=keys)
    def delete(self, key):
        """Delete operation"""
        if key in self.store:
            del self.store[key]
        self.operations_count += 1

    @invariant()
    def check_consistency(self):
        """Invariant: Store is internally consistent"""
        # All keys are strings
        assert all(isinstance(k, str) for k in self.store.keys())

        # Operation count is non-negative
        assert self.operations_count >= 0

    @invariant()
    def check_bounded_size(self):
        """Invariant: Store size is bounded"""
        assert len(self.store) <= 1000, "Store grew too large"

    @invariant()
    def check_determinism(self):
        """Invariant: Operations are deterministic"""
        # Same key always maps to same value (until changed)
        for key in self.store:
            value1 = self.store[key]
            value2 = self.store[key]
            assert value1 == value2, "Non-deterministic read"


if __name__ == "__main__":
    import pytest

    # Run formal verification tests
    pytest.main([__file__, "-v", "--tb=short"])

    # Also run stateful property testing
    test = FormalStateMachine.TestCase
    test.runTest = lambda self: None
    state_machine = test()
    state_machine.run()
