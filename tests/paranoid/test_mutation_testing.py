#!/usr/bin/env python3
"""
from typing import Dict
from typing import Any
MUTATION TESTING - Test the quality of our tests
Kill mutants to prove our tests actually work
"""

import ast
import copy
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MutationOperator:
    """Base class for mutation operators"""

    def mutate(self, node: ast.AST) -> ast.AST:
        raise NotImplementedError


class ArithmeticMutator(MutationOperator):
    """Mutate arithmetic operators"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Add):
            return ast.Sub()
        elif isinstance(node, ast.Sub):
            return ast.Add()
        elif isinstance(node, ast.Mult):
            return ast.Div()
        elif isinstance(node, ast.Div):
            return ast.Mult()
        elif isinstance(node, ast.Mod):
            return ast.Mult()
        elif isinstance(node, ast.Pow):
            return ast.Mult()
        return node


class ComparisonMutator(MutationOperator):
    """Mutate comparison operators"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Eq):
            return ast.NotEq()
        elif isinstance(node, ast.NotEq):
            return ast.Eq()
        elif isinstance(node, ast.Lt):
            return ast.GtE()
        elif isinstance(node, ast.LtE):
            return ast.Gt()
        elif isinstance(node, ast.Gt):
            return ast.LtE()
        elif isinstance(node, ast.GtE):
            return ast.Lt()
        elif isinstance(node, ast.Is):
            return ast.IsNot()
        elif isinstance(node, ast.IsNot):
            return ast.Is()
        elif isinstance(node, ast.In):
            return ast.NotIn()
        elif isinstance(node, ast.NotIn):
            return ast.In()
        return node


class BooleanMutator(MutationOperator):
    """Mutate boolean operators"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.And):
            return ast.Or()
        elif isinstance(node, ast.Or):
            return ast.And()
        elif isinstance(node, ast.Not):
            # Remove the Not
            return None
        return node


class ConstantMutator(MutationOperator):
    """Mutate constants"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                node.value = not node.value
            elif isinstance(node.value, int):
                if node.value == 0:
                    node.value = 1
                elif node.value == 1:
                    node.value = 0
                else:
                    node.value = node.value + 1
            elif isinstance(node.value, str):
                if node.value == "":
                    node.value = "mutated"
                else:
                    node.value = ""
            elif node.value is None:
                node.value = "not_none"
        return node


class ReturnMutator(MutationOperator):
    """Mutate return statements"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Return):
            if node.value is None:
                # Return True instead of None
                node.value = ast.Constant(value=True)
            elif isinstance(node.value, ast.Constant):
                if node.value.value is True:
                    node.value.value = False
                elif node.value.value is False:
                    node.value.value = True
                elif node.value.value is None:
                    node.value.value = 0
        return node


class ExceptionMutator(MutationOperator):
    """Mutate exception handling"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Raise):
            # Remove the raise
            return ast.Pass()
        elif isinstance(node, ast.ExceptHandler):
            # Change exception type
            if node.type:
                node.type = ast.Name(id="Exception", ctx=ast.Load())
        return node


class StringMutator(MutationOperator):
    """Mutate string operations"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Mutate string methods
                if node.func.attr == "strip":
                    node.func.attr = "lstrip"
                elif node.func.attr == "lstrip":
                    node.func.attr = "rstrip"
                elif node.func.attr == "rstrip":
                    node.func.attr = "strip"
                elif node.func.attr == "upper":
                    node.func.attr = "lower"
                elif node.func.attr == "lower":
                    node.func.attr = "upper"
                elif node.func.attr == "startswith":
                    node.func.attr = "endswith"
                elif node.func.attr == "endswith":
                    node.func.attr = "startswith"
        return node


class BoundaryMutator(MutationOperator):
    """Mutate boundary conditions"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if isinstance(op, ast.Lt):
                    node.ops[i] = ast.LtE()
                elif isinstance(op, ast.LtE):
                    node.ops[i] = ast.Lt()
                elif isinstance(op, ast.Gt):
                    node.ops[i] = ast.GtE()
                elif isinstance(op, ast.GtE):
                    node.ops[i] = ast.Gt()
        return node


class LoopMutator(MutationOperator):
    """Mutate loop conditions"""

    def mutate(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.While):
            # Invert while condition
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        elif isinstance(node, ast.For):
            # Skip first iteration
            if isinstance(node.iter, ast.Call):
                if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                    if len(node.iter.args) > 0:
                        # Start from 1 instead of 0
                        if (
                            isinstance(node.iter.args[0], ast.Constant)
                            and node.iter.args[0].value == 0
                        ):
                            node.iter.args[0].value = 1
        return node


class MutationEngine:
    """Engine for applying mutations and running tests"""

    def __init__(self, source_file: Path, test_file: Path):
        self.source_file = source_file
        self.test_file = test_file
        self.original_source = source_file.read_text()
        self.tree = ast.parse(self.original_source)
        self.mutators = [
            ArithmeticMutator(),
            ComparisonMutator(),
            BooleanMutator(),
            ConstantMutator(),
            ReturnMutator(),
            ExceptionMutator(),
            StringMutator(),
            BoundaryMutator(),
            LoopMutator(),
        ]
        self.mutations_applied = 0
        self.mutations_killed = 0
        self.mutations_survived = 0
        self.survived_mutations = []

    def generate_mutants(self) -> List[Tuple[ast.AST, str, int]]:
        """Generate all possible mutants"""
        mutants = []

        for node in ast.walk(self.tree):
            for mutator in self.mutators:
                try:
                    mutated = copy.deepcopy(node)
                    mutated = mutator.mutate(mutated)
                    if mutated != node:
                        # Find line number
                        line_no = getattr(node, "lineno", 0)
                        mutants.append((mutated, mutator.__class__.__name__, line_no))
                except:
                    continue

        return mutants

    def apply_mutation(self, mutant: ast.AST, original_node: ast.AST) -> str:
        """Apply a mutation and return mutated source"""
        tree_copy = copy.deepcopy(self.tree)

        # Replace the original node with mutant in the tree
        class NodeReplacer(ast.NodeTransformer):
            def visit(self, node):
                if node == original_node:
                    return mutant
                return self.generic_visit(node)

        replacer = NodeReplacer()
        mutated_tree = replacer.visit(tree_copy)

        # Convert back to source
        return ast.unparse(mutated_tree)

    def run_tests(self) -> bool:
        """Run tests and return True if all pass"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(self.test_file), "-xvs", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=10,
                env={"PYTHONPATH": str(Path.cwd())},
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def run_mutation_testing(self, sample_size: int = 100) -> Dict[str, Any]:
        """Run mutation testing on a sample of mutants"""
        mutants = self.generate_mutants()

        # Sample mutants if there are too many
        if len(mutants) > sample_size:
            mutants = random.sample(mutants, sample_size)

        print(f"Testing {len(mutants)} mutants...")

        for i, (mutant, mutator_name, line_no) in enumerate(mutants):
            self.mutations_applied += 1

            # Apply mutation
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                # Write mutated code
                mutated_source = self.apply_mutation(mutant, mutant)
                f.write(mutated_source)
                temp_file = f.name

            try:
                # Temporarily replace the source file
                backup = self.source_file.read_text()
                self.source_file.write_text(mutated_source)

                # Run tests
                if self.run_tests():
                    # Mutation survived! This is bad - tests didn't catch it
                    self.mutations_survived += 1
                    self.survived_mutations.append(
                        {
                            "mutator": mutator_name,
                            "line": line_no,
                            "description": f"Mutation at line {line_no} using {mutator_name}",
                        }
                    )
                    print(
                        f"  FAIL Mutation {i+1}/{len(mutants)} SURVIVED: {mutator_name} at line {line_no}"
                    )
                else:
                    # Mutation was killed! This is good
                    self.mutations_killed += 1
                    print(f"  PASS Mutation {i+1}/{len(mutants)} KILLED: {mutator_name}")

            finally:
                # Restore original source
                self.source_file.write_text(backup)
                Path(temp_file).unlink(missing_ok=True)

        # Calculate mutation score
        mutation_score = (
            (self.mutations_killed / self.mutations_applied * 100)
            if self.mutations_applied > 0
            else 0
        )

        return {
            "mutations_applied": self.mutations_applied,
            "mutations_killed": self.mutations_killed,
            "mutations_survived": self.mutations_survived,
            "mutation_score": mutation_score,
            "survived_details": self.survived_mutations,
        }


class TestMutationTesting:
    """Tests for mutation testing."""

    @pytest.mark.timeout(15)
    def test_example_mutation(self):
        """Test mutation on a simple example"""

        # Create a simple source file
        source_code = """
def add(a, b):
    return a + b

def is_positive(x):
    return x > 0

def process_string(s):
    return s.strip().upper()
"""

        # Create a simple test file
        test_code = """
@pytest.mark.timeout(15)


def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0


@pytest.mark.timeout(15)


def test_is_positive():
    assert is_positive(1) == True
    assert is_positive(0) == False
    assert is_positive(-1) == False


@pytest.mark.timeout(15)


def test_process_string():
    assert process_string("  hello  ") == "HELLO"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as src:
            src.write(source_code)
            source_file = Path(src.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tst:
            tst.write(test_code)
            test_file = Path(tst.name)

        try:
            engine = MutationEngine(source_file, test_file)
            results = engine.run_mutation_testing(sample_size=10)

            print(f"\nMutation Testing Results:")
            print(f"  Mutations applied: {results['mutations_applied']}")
            print(f"  Mutations killed: {results['mutations_killed']}")
            print(f"  Mutations survived: {results['mutations_survived']}")
            print(f"  Mutation score: {results['mutation_score']:.1f}%")

            if results["survived_details"]:
                print(f"\n  Survived mutations (test gaps):")
                for survivor in results["survived_details"]:
                    print(f"    - {survivor['description']}")

            # Good tests should kill most mutations
            assert (
                results["mutation_score"] >= 70
            ), f"Mutation score too low: {results['mutation_score']:.1f}%"

        finally:
            source_file.unlink(missing_ok=True)
            test_file.unlink(missing_ok=True)


def run_mutation_testing_on_project():
    """Run mutation testing on the actual project"""

    # Target the security validator and its tests
    source_file = Path("src/core/security_validator.py")
    test_file = Path("tests/security/test_security_validator.py")

    if not source_file.exists() or not test_file.exists():
        print("Source or test file not found")
        return

    engine = MutationEngine(source_file, test_file)
    results = engine.run_mutation_testing(sample_size=50)  # Test 50 mutations

    print("\n" + "=" * 60)
    print("MUTATION TESTING REPORT")
    print("=" * 60)
    print(f"Source: {source_file}")
    print(f"Tests: {test_file}")
    print(f"\nResults:")
    print(f"  Mutations applied: {results['mutations_applied']}")
    print(f"  Mutations killed: {results['mutations_killed']} PASS")
    print(f"  Mutations survived: {results['mutations_survived']} FAIL")
    print(f"  Mutation score: {results['mutation_score']:.1f}%")

    if results["mutation_score"] < 80:
        print(f"\nWARN WARNING: Low mutation score indicates weak tests!")
        print(f"  Your tests are not catching enough bugs.")
    else:
        print(f"\nPASS Good mutation score! Tests are effective.")

    if results["survived_details"]:
        print(f"\nSurvived mutations (areas needing better tests):")
        for i, survivor in enumerate(results["survived_details"][:10]):
            print(f"  {i+1}. {survivor['description']}")

    return results


if __name__ == "__main__":
    import pytest

    # Run self-tests first
    pytest.main([__file__, "-v", "--tb=short"])

    # Then run on actual project
    print("\n" + "=" * 60)
    print("Running mutation testing on actual project...")
    print("=" * 60)
    run_mutation_testing_on_project()
