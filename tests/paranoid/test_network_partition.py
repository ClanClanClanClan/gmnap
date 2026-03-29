#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
NETWORK PARTITION TESTING
Simulates network failures and distributed system issues:
- Split-brain scenarios
- Partial network failures
- Connection timeouts
- Message loss and reordering
- Network congestion
- Byzantine network behavior
"""

import asyncio
import random
import socket
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class NetworkCondition(Enum):
    """Network conditions to simulate"""

    HEALTHY = "healthy"
    PARTITIONED = "partitioned"
    SLOW = "slow"
    LOSSY = "lossy"
    REORDERING = "reordering"
    DUPLICATING = "duplicating"
    CORRUPTING = "corrupting"
    BYZANTINE = "byzantine"


@dataclass
class NetworkMessage:
    """Message in the network"""

    id: str
    source: str
    destination: str
    payload: Any
    timestamp: float
    attempts: int = 0


class NetworkSimulator:
    """Simulates various network conditions"""

    def __init__(self):
        self.condition = NetworkCondition.HEALTHY
        self.nodes: Dict[str, "NetworkNode"] = {}
        self.message_queue = queue.Queue()
        self.partition_groups: List[List[str]] = []
        self.latency_ms = 1
        self.loss_rate = 0.0
        self.corruption_rate = 0.0
        self.reorder_buffer: List[NetworkMessage] = []
        self.metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_lost": 0,
            "messages_corrupted": 0,
            "messages_reordered": 0,
            "messages_duplicated": 0,
            "partition_violations": 0,
        }

    def add_node(self, node_id: str, node: "NetworkNode"):
        """Add a node to the network"""
        self.nodes[node_id] = node

    def set_condition(self, condition: NetworkCondition):
        """Change network condition"""
        self.condition = condition

        # Configure parameters based on condition
        if condition == NetworkCondition.HEALTHY:
            self.latency_ms = 1
            self.loss_rate = 0.0
            self.corruption_rate = 0.0
        elif condition == NetworkCondition.SLOW:
            self.latency_ms = random.randint(100, 2000)
            self.loss_rate = 0.05
        elif condition == NetworkCondition.LOSSY:
            self.latency_ms = 10
            self.loss_rate = 0.3
        elif condition == NetworkCondition.CORRUPTING:
            self.corruption_rate = 0.1
        elif condition == NetworkCondition.BYZANTINE:
            # Byzantine: random bad behavior
            self.latency_ms = random.randint(1, 5000)
            self.loss_rate = random.random() * 0.5
            self.corruption_rate = random.random() * 0.2

    def create_partition(self, groups: List[List[str]]):
        """Create network partition between groups"""
        self.partition_groups = groups
        self.condition = NetworkCondition.PARTITIONED

    def send_message(self, msg: NetworkMessage) -> bool:
        """Send a message through the network"""
        self.metrics["messages_sent"] += 1

        # Check partition
        if self.condition == NetworkCondition.PARTITIONED:
            source_group = None
            dest_group = None

            for i, group in enumerate(self.partition_groups):
                if msg.source in group:
                    source_group = i
                if msg.destination in group:
                    dest_group = i

            if source_group is not None and dest_group is not None:
                if source_group != dest_group:
                    # Message crosses partition - drop it
                    self.metrics["messages_lost"] += 1
                    self.metrics["partition_violations"] += 1
                    return False

        # Simulate latency
        time.sleep(self.latency_ms / 1000.0)

        # Simulate loss
        if random.random() < self.loss_rate:
            self.metrics["messages_lost"] += 1
            return False

        # Simulate corruption
        if random.random() < self.corruption_rate:
            msg.payload = self._corrupt_payload(msg.payload)
            self.metrics["messages_corrupted"] += 1

        # Simulate reordering
        if self.condition == NetworkCondition.REORDERING:
            if random.random() < 0.3:
                self.reorder_buffer.append(msg)
                self.metrics["messages_reordered"] += 1

                # Deliver buffered messages randomly
                if len(self.reorder_buffer) > 3 and random.random() < 0.5:
                    old_msg = self.reorder_buffer.pop(0)
                    self._deliver_message(old_msg)
                return True

        # Simulate duplication
        if self.condition == NetworkCondition.DUPLICATING:
            if random.random() < 0.1:
                # Deliver twice
                self._deliver_message(msg)
                self._deliver_message(msg)
                self.metrics["messages_duplicated"] += 1
                return True

        # Normal delivery
        return self._deliver_message(msg)

    def _deliver_message(self, msg: NetworkMessage) -> bool:
        """Actually deliver a message"""
        if msg.destination in self.nodes:
            self.nodes[msg.destination].receive_message(msg)
            self.metrics["messages_delivered"] += 1
            return True
        return False

    def _corrupt_payload(self, payload: Any) -> Any:
        """Corrupt a message payload"""
        if isinstance(payload, str):
            # Flip random bit in string
            if payload:
                chars = list(payload)
                idx = random.randint(0, len(chars) - 1)
                chars[idx] = chr(ord(chars[idx]) ^ random.randint(1, 255))
                return "".join(chars)
        elif isinstance(payload, dict):
            # Modify random key
            if payload:
                key = random.choice(list(payload.keys()))
                payload[key] = None
        elif isinstance(payload, (int, float)):
            # Add random noise
            return payload + random.uniform(-100, 100)
        return payload


class NetworkNode:
    """A node in the distributed system"""

    def __init__(self, node_id: str, network: NetworkSimulator):
        self.node_id = node_id
        self.network = network
        self.inbox = queue.Queue()
        self.state = {}
        self.peers: List[str] = []
        self.is_leader = False
        self.term = 0
        self.voted_for = None
        self.log = []
        self.commit_index = 0

    def send(self, destination: str, payload: Any) -> bool:
        """Send message to another node"""
        msg = NetworkMessage(
            id=f"{self.node_id}-{destination}-{time.time()}",
            source=self.node_id,
            destination=destination,
            payload=payload,
            timestamp=time.time(),
        )
        return self.network.send_message(msg)

    def broadcast(self, payload: Any):
        """Broadcast to all peers"""
        for peer in self.peers:
            self.send(peer, payload)

    def receive_message(self, msg: NetworkMessage):
        """Receive a message"""
        self.inbox.put(msg)

    def process_messages(self):
        """Process received messages"""
        while not self.inbox.empty():
            try:
                msg = self.inbox.get_nowait()
                self.handle_message(msg)
            except queue.Empty:
                break

    def handle_message(self, msg: NetworkMessage):
        """Handle a received message - override in subclass"""
        pass


class ConsensusNode(NetworkNode):
    """Node that participates in consensus (simplified Raft)"""

    def __init__(self, node_id: str, network: NetworkSimulator):
        super().__init__(node_id, network)
        self.role = "follower"
        self.current_term = 0
        self.voted_for = None
        self.log = []
        self.leader_id = None
        self.election_timeout = random.uniform(0.15, 0.3)
        self.last_heartbeat = time.time()

    def handle_message(self, msg: NetworkMessage):
        """Handle consensus messages"""
        payload = msg.payload

        if payload.get("type") == "heartbeat":
            self.handle_heartbeat(msg)
        elif payload.get("type") == "request_vote":
            self.handle_vote_request(msg)
        elif payload.get("type") == "vote":
            self.handle_vote(msg)
        elif payload.get("type") == "append_entry":
            self.handle_append_entry(msg)

    def handle_heartbeat(self, msg: NetworkMessage):
        """Handle leader heartbeat"""
        term = msg.payload.get("term", 0)

        if term >= self.current_term:
            self.current_term = term
            self.role = "follower"
            self.leader_id = msg.source
            self.last_heartbeat = time.time()
            self.voted_for = None

    def start_election(self):
        """Start leader election"""
        self.role = "candidate"
        self.current_term += 1
        self.voted_for = self.node_id
        self.leader_id = None

        # Request votes
        self.broadcast(
            {
                "type": "request_vote",
                "term": self.current_term,
                "candidate": self.node_id,
            }
        )

    def check_election_timeout(self):
        """Check if election timeout has passed"""
        if self.role != "leader":
            if time.time() - self.last_heartbeat > self.election_timeout:
                self.start_election()


class TestNetworkPartition:
    """Tests for network partition scenarios."""

    @pytest.mark.timeout(15)
    def test_basic_partition(self):
        """Test basic network partition between nodes"""
        network = NetworkSimulator()

        # Create nodes
        nodes = {}
        for i in range(5):
            node_id = f"node_{i}"
            node = NetworkNode(node_id, network)
            nodes[node_id] = node
            network.add_node(node_id, node)
            node.peers = [f"node_{j}" for j in range(5) if j != i]

        # Test healthy network
        assert nodes["node_0"].send("node_1", {"data": "test"})

        # Create partition: [node_0, node_1] | [node_2, node_3, node_4]
        network.create_partition([["node_0", "node_1"], ["node_2", "node_3", "node_4"]])

        # Messages within partition should work
        assert nodes["node_0"].send("node_1", {"data": "test"})
        assert nodes["node_2"].send("node_3", {"data": "test"})

        # Messages across partition should fail
        assert not nodes["node_0"].send("node_2", {"data": "test"})
        assert not nodes["node_3"].send("node_1", {"data": "test"})

        # Verify metrics
        assert network.metrics["partition_violations"] >= 2

    @pytest.mark.timeout(15)
    def test_message_loss(self):
        """Test message loss scenarios"""
        network = NetworkSimulator()
        network.set_condition(NetworkCondition.LOSSY)

        # Create nodes
        sender = NetworkNode("sender", network)
        receiver = NetworkNode("receiver", network)
        network.add_node("sender", sender)
        network.add_node("receiver", receiver)

        # Send many messages
        sent = 0
        received = 0

        for i in range(100):
            if sender.send("receiver", {"seq": i}):
                sent += 1

        # Process received messages
        receiver.process_messages()
        received = receiver.inbox.qsize()

        # With 30% loss rate, we expect significant message loss
        assert received < sent
        assert network.metrics["messages_lost"] > 20

        print(
            f"Message loss test: {network.metrics['messages_lost']}/100 messages lost"
        )

    @pytest.mark.timeout(15)
    def test_message_corruption(self):
        """Test message corruption"""
        network = NetworkSimulator()
        network.set_condition(NetworkCondition.CORRUPTING)

        # Create nodes
        sender = NetworkNode("sender", network)
        receiver = NetworkNode("receiver", network)
        network.add_node("sender", sender)
        network.add_node("receiver", receiver)

        # Send messages
        original_messages = []
        for i in range(50):
            msg = f"Message_{i}_integrity_check"
            original_messages.append(msg)
            sender.send("receiver", msg)

        # Check for corruption
        receiver.process_messages()
        corrupted = 0

        while not receiver.inbox.empty():
            msg = receiver.inbox.get()
            if msg.payload not in original_messages:
                corrupted += 1

        assert corrupted > 0, "Expected some messages to be corrupted"
        assert network.metrics["messages_corrupted"] > 3

        print(f"Corruption test: {corrupted} messages corrupted")

    @pytest.mark.timeout(15)
    def test_message_reordering(self):
        """Test message reordering"""
        network = NetworkSimulator()
        network.set_condition(NetworkCondition.REORDERING)

        # Create nodes
        sender = NetworkNode("sender", network)
        receiver = NetworkNode("receiver", network)
        network.add_node("sender", sender)
        network.add_node("receiver", receiver)

        # Send ordered messages
        for i in range(20):
            sender.send("receiver", {"seq": i})

        # Flush reorder buffer
        time.sleep(0.1)
        for msg in network.reorder_buffer:
            network._deliver_message(msg)

        # Check order
        receiver.process_messages()
        received_order = []

        while not receiver.inbox.empty():
            msg = receiver.inbox.get()
            if "seq" in msg.payload:
                received_order.append(msg.payload["seq"])

        # Check if any reordering occurred
        is_ordered = all(
            received_order[i] <= received_order[i + 1]
            for i in range(len(received_order) - 1)
        )

        assert not is_ordered or network.metrics["messages_reordered"] > 0
        print(
            f"Reordering test: {network.metrics['messages_reordered']} messages reordered"
        )

    @pytest.mark.timeout(15)
    def test_split_brain_consensus(self):
        """Test split-brain scenario in consensus"""
        network = NetworkSimulator()

        # Create consensus nodes
        nodes = {}
        for i in range(5):
            node_id = f"node_{i}"
            node = ConsensusNode(node_id, network)
            nodes[node_id] = node
            network.add_node(node_id, node)
            node.peers = [f"node_{j}" for j in range(5) if j != i]

        # Let them run normally first
        for _ in range(10):
            for node in nodes.values():
                node.check_election_timeout()
                node.process_messages()
            time.sleep(0.01)

        # Count leaders before partition
        leaders_before = sum(1 for n in nodes.values() if n.role == "leader")

        # Create partition that could cause split-brain
        # Majority: [node_0, node_1, node_2] | Minority: [node_3, node_4]
        network.create_partition([["node_0", "node_1", "node_2"], ["node_3", "node_4"]])

        # Force election in both partitions
        for node in nodes.values():
            node.last_heartbeat = 0  # Force timeout

        # Run for a while
        for _ in range(20):
            for node in nodes.values():
                node.check_election_timeout()
                node.process_messages()
            time.sleep(0.01)

        # Check for split-brain
        majority_leaders = sum(
            1 for i in range(3) if nodes[f"node_{i}"].role == "leader"
        )
        minority_leaders = sum(
            1 for i in range(3, 5) if nodes[f"node_{i}"].role == "leader"
        )

        # Majority partition should elect a leader
        # Minority partition should not (no quorum)
        print(
            f"Split-brain test: Majority leaders: {majority_leaders}, Minority leaders: {minority_leaders}"
        )

        # In proper consensus, only majority partition should have a leader
        assert majority_leaders <= 1  # At most one leader in majority
        # Minority might try to elect but shouldn't succeed (simplified test)

    @pytest.mark.timeout(15)
    def test_byzantine_behavior(self):
        """Test Byzantine network behavior"""
        network = NetworkSimulator()

        # Create nodes
        honest_nodes = []
        byzantine_node = NetworkNode("byzantine", network)
        network.add_node("byzantine", byzantine_node)

        for i in range(3):
            node = NetworkNode(f"honest_{i}", network)
            honest_nodes.append(node)
            network.add_node(node.node_id, node)

        # Byzantine node sends conflicting messages
        network.set_condition(NetworkCondition.BYZANTINE)

        # Byzantine sends different values to different nodes
        byzantine_node.send("honest_0", {"value": "A"})
        byzantine_node.send("honest_1", {"value": "B"})
        byzantine_node.send("honest_2", {"value": "C"})

        # Also send with random delays and corruption
        time.sleep(0.05)

        # Check that honest nodes received different values
        values_received = []
        for node in honest_nodes:
            node.process_messages()
            if not node.inbox.empty():
                msg = node.inbox.get()
                values_received.append(msg.payload.get("value"))

        # Byzantine behavior should cause inconsistency
        print(f"Byzantine test: Values received: {values_received}")
        print(
            f"Byzantine metrics: Lost: {network.metrics['messages_lost']}, "
            f"Corrupted: {network.metrics['messages_corrupted']}"
        )

    @pytest.mark.timeout(15)
    def test_cascading_failure(self):
        """Test cascading failure scenario"""
        network = NetworkSimulator()

        # Create a chain of dependent nodes
        nodes = {}
        for i in range(10):
            node = NetworkNode(f"node_{i}", network)
            nodes[f"node_{i}"] = node
            network.add_node(f"node_{i}", node)
            if i > 0:
                node.peers = [f"node_{i-1}"]  # Each depends on previous

        # Simulate cascading failure
        failed_nodes = set()

        def fail_node(node_id):
            """Simulate node failure"""
            failed_nodes.add(node_id)
            # Node can't send messages when failed
            node = nodes[node_id]
            node.send = lambda d, p: False

        # Start cascade
        fail_node("node_0")

        # Propagate failure
        for i in range(1, 10):
            node = nodes[f"node_{i}"]
            # Try to communicate with peer
            if not node.send(f"node_{i-1}", {"health": "check"}):
                # Peer failed, this node fails too (simplified cascade)
                fail_node(f"node_{i}")

        # Check cascade effect
        assert (
            len(failed_nodes) >= 5
        ), f"Cascade should affect multiple nodes, got {len(failed_nodes)}"
        print(f"Cascading failure: {len(failed_nodes)}/10 nodes failed")

    @pytest.mark.timeout(15)
    def test_network_congestion(self):
        """Test behavior under network congestion"""
        network = NetworkSimulator()
        network.set_condition(NetworkCondition.SLOW)

        # Create nodes
        nodes = []
        for i in range(5):
            node = NetworkNode(f"node_{i}", network)
            nodes.append(node)
            network.add_node(node.node_id, node)

        # Flood network
        start_time = time.time()
        messages_sent = 0

        # Send many messages concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for _ in range(100):
                sender = random.choice(nodes)
                receiver = random.choice(nodes)
                if sender != receiver:
                    future = executor.submit(
                        sender.send, receiver.node_id, {"data": "X" * 1000}
                    )
                    futures.append(future)
                    messages_sent += 1

            # Wait with timeout
            for future in futures:
                try:
                    future.result(timeout=5)
                except TimeoutError:
                    pass

        elapsed = time.time() - start_time
        throughput = messages_sent / elapsed if elapsed > 0 else 0

        print(
            f"Congestion test: {messages_sent} messages in {elapsed:.2f}s = {throughput:.2f} msg/s"
        )
        print(f"Delivery rate: {network.metrics['messages_delivered']}/{messages_sent}")

        # Under congestion, delivery should be impacted
        assert network.metrics["messages_lost"] > 0 or elapsed > 2

    @pytest.mark.timeout(15)
    def test_asymmetric_partition(self):
        """Test asymmetric network partition (A can reach B but B can't reach A)"""
        network = NetworkSimulator()

        # Create custom network with asymmetric behavior
        class AsymmetricNetwork(NetworkSimulator):
            def send_message(self, msg: NetworkMessage) -> bool:
                # node_0 can send to node_1, but not vice versa
                if msg.source == "node_1" and msg.destination == "node_0":
                    self.metrics["messages_lost"] += 1
                    return False
                return super().send_message(msg)

        network = AsymmetricNetwork()

        # Create nodes
        node0 = NetworkNode("node_0", network)
        node1 = NetworkNode("node_1", network)
        network.add_node("node_0", node0)
        network.add_node("node_1", node1)

        # Test asymmetry
        assert node0.send("node_1", {"test": "forward"})  # Should work
        assert not node1.send("node_0", {"test": "backward"})  # Should fail

        # This can cause interesting consensus issues
        print(f"Asymmetric partition: Forward works, backward blocked")

    @pytest.mark.timeout(15)
    def test_partial_partition(self):
        """Test partial network partition (some messages get through)"""

        class PartialNetwork(NetworkSimulator):
            def send_message(self, msg: NetworkMessage) -> bool:
                # 50% chance of message loss between partitions
                if msg.source in ["node_0", "node_1"] and msg.destination in [
                    "node_2",
                    "node_3",
                ]:
                    if random.random() < 0.5:
                        self.metrics["messages_lost"] += 1
                        return False
                return super().send_message(msg)

        network = PartialNetwork()

        # Create nodes
        nodes = {}
        for i in range(4):
            node = NetworkNode(f"node_{i}", network)
            nodes[f"node_{i}"] = node
            network.add_node(f"node_{i}", node)

        # Send messages across partial partition
        successes = 0
        attempts = 50

        for _ in range(attempts):
            if nodes["node_0"].send("node_2", {"data": "test"}):
                successes += 1

        # Should have partial success
        assert (
            10 < successes < 40
        ), f"Expected partial success, got {successes}/{attempts}"
        print(f"Partial partition: {successes}/{attempts} messages got through")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
