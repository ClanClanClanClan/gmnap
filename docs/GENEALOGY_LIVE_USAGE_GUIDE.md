# GENEALOGY API - LIVE USAGE GUIDE
**Created**: November 4, 2025
**Status**: ✅ Production Ready
**System**: GMNAP V7 Genealogy Module

---

## 🎯 QUICK START (5 minutes)

### Current Live System
```bash
# Server Status
Server PID: 96681
Uptime: 26+ hours
Port: 8080
Database: bolt://localhost:7688

# Check Health
curl http://localhost:8080/healthz
curl http://localhost:8080/genealogy/stats | jq
```

**Expected Response**:
```json
{
  "status": "ok",
  "database": "bolt://localhost:7688",
  "statistics": {
    "persons": 12649,
    "relationships": 15340,
    "confidence_distribution": {
      "high": 12640,
      "medium": 2700,
      "low": 0
    }
  }
}
```

---

## 📊 AVAILABLE ENDPOINTS

### 1. GET /genealogy/stats
**Purpose**: Database statistics and health check

**Example**:
```bash
curl -s http://localhost:8080/genealogy/stats | jq
```

**Response**:
```json
{
  "status": "ok",
  "database": "bolt://localhost:7688",
  "statistics": {
    "persons": 12649,
    "relationships": 15340,
    "confidence_distribution": {
      "high": 12640,
      "medium": 2700,
      "low": 0
    }
  }
}
```

**Use Cases**:
- Monitoring dashboard health check
- Verify database connectivity
- Check data availability

---

### 2. GET /genealogy/lineage/{global_id}
**Purpose**: Get academic ancestors (advisors) for a mathematician

**Parameters**:
- `global_id` (path): 22-character GMNAP GlobalID
- `max_depth` (query, optional): Maximum relationship depth (default: 10, max: 50)

**Example 1: Default depth**:
```bash
# Get lineage for Vincent Guedj
curl -s 'http://localhost:8080/genealogy/lineage/LG4TF2CGQIZNOYRQ52DVK5' | jq
```

**Example 2: Custom depth**:
```bash
# Get 3 generations of advisors
curl -s 'http://localhost:8080/genealogy/lineage/LG4TF2CGQIZNOYRQ52DVK5?max_depth=3' | jq
```

**Response**:
```json
{
  "global_id": "LG4TF2CGQIZNOYRQ52DVK5",
  "paths": [
    {
      "depth": 1,
      "node_ids": ["LG4TF2CGQIZNOYRQ52DVK5", "ECCGKCTYZIRX7F5VASIZBW"],
      "node_names": ["Vincent Guedj", "Henri Guenancia"]
    },
    {
      "depth": 2,
      "node_ids": ["LG4TF2CGQIZNOYRQ52DVK5", "ECCGKCTYZIRX7F5VASIZBW", "XXXXXXXXXXXXXXXXXXXX"],
      "node_names": ["Vincent Guedj", "Henri Guenancia", "Advisor Name"]
    }
  ],
  "total_paths": 2
}
```

**Use Cases**:
- Academic genealogy visualization
- Citation network analysis
- Research lineage tracking
- Advisor discovery

---

### 3. GET /genealogy/descendants/{global_id}
**Purpose**: Get academic descendants (students) for a mathematician

**Parameters**:
- `global_id` (path): 22-character GMNAP GlobalID
- `max_depth` (query, optional): Maximum relationship depth (default: 10, max: 50)

**Example**:
```bash
# Get descendants for Henri Guenancia
curl -s 'http://localhost:8080/genealogy/descendants/ECCGKCTYZIRX7F5VASIZBW?max_depth=2' | jq
```

**Response**:
```json
{
  "global_id": "ECCGKCTYZIRX7F5VASIZBW",
  "paths": [
    {
      "depth": 1,
      "node_ids": ["ECCGKCTYZIRX7F5VASIZBW", "LG4TF2CGQIZNOYRQ52DVK5"],
      "node_names": ["Henri Guenancia", "Vincent Guedj"]
    },
    {
      "depth": 1,
      "node_ids": ["ECCGKCTYZIRX7F5VASIZBW", "XXXXXXXXXXXXXXXXXXXXXXX"],
      "node_names": ["Henri Guenancia", "Other Student"]
    }
  ],
  "total_paths": 2
}
```

**Use Cases**:
- Track research impact
- Student network analysis
- Academic influence measurement
- Collaboration discovery

---

## 🔍 FINDING GLOBAL IDS

### Method 1: Direct Database Query
```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    # Search by name
    result = s.run("""
        MATCH (p:Person)
        WHERE p.canonical_name CONTAINS $name
        RETURN p.global_id, p.canonical_name
        LIMIT 10
    """, name="Einstein")

    for record in result:
        print(f"{record['p.canonical_name']}: {record['p.global_id']}")

driver.close()
EOF
```

### Method 2: Search All Persons
```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    result = s.run("""
        MATCH (p:Person)
        RETURN p.global_id, p.canonical_name
        ORDER BY p.canonical_name
        LIMIT 100
    """)

    for record in result:
        print(f"{record['p.canonical_name']}: {record['p.global_id']}")

driver.close()
EOF
```

### Method 3: Find by Relationship
```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    # Find advisors with students
    result = s.run("""
        MATCH (advisor:Person)<-[:DOCTORAL_ADVISOR]-(student:Person)
        RETURN advisor.global_id, advisor.canonical_name, count(student) as students
        ORDER BY students DESC
        LIMIT 20
    """)

    print("Top 20 Advisors by Student Count:")
    for record in result:
        print(f"{record['advisor.canonical_name']} ({record['advisor.global_id']}): {record['students']} students")

driver.close()
EOF
```

---

## 🧪 COMPREHENSIVE TESTING PLAN

### Test 1: Health Checks
```bash
echo "=== HEALTH CHECK TESTS ==="
echo "1. Server health:"
curl -s http://localhost:8080/healthz | jq

echo ""
echo "2. Readiness:"
curl -s http://localhost:8080/readyz | jq

echo ""
echo "3. Database stats:"
curl -s http://localhost:8080/genealogy/stats | jq
```

### Test 2: Lineage Queries
```bash
echo "=== LINEAGE TESTS ==="

# Test with known IDs from database
IDS=(
  "LG4TF2CGQIZNOYRQ52DVK5"  # Vincent Guedj
  "ECCGKCTYZIRX7F5VASIZBW"  # Henri Guenancia
)

for id in "${IDS[@]}"; do
  echo ""
  echo "Testing lineage for: $id"
  curl -s "http://localhost:8080/genealogy/lineage/$id?max_depth=3" | jq '.paths | length'
done
```

### Test 3: Descendants Queries
```bash
echo "=== DESCENDANTS TESTS ==="

for id in "${IDS[@]}"; do
  echo ""
  echo "Testing descendants for: $id"
  curl -s "http://localhost:8080/genealogy/descendants/$id?max_depth=2" | jq '.paths | length'
done
```

### Test 4: Edge Cases
```bash
echo "=== EDGE CASE TESTS ==="

echo "1. Non-existent ID:"
curl -s "http://localhost:8080/genealogy/lineage/INVALIDXXXXXXXXXXXXXX" | jq

echo ""
echo "2. Max depth boundary:"
curl -s "http://localhost:8080/genealogy/lineage/LG4TF2CGQIZNOYRQ52DVK5?max_depth=50" | jq

echo ""
echo "3. Min depth:"
curl -s "http://localhost:8080/genealogy/lineage/LG4TF2CGQIZNOYRQ52DVK5?max_depth=1" | jq '.paths | length'
```

### Test 5: Performance
```bash
echo "=== PERFORMANCE TESTS ==="

echo "Testing 10 sequential queries..."
time for i in {1..10}; do
  curl -s "http://localhost:8080/genealogy/stats" > /dev/null
done

echo ""
echo "Testing lineage query performance..."
time curl -s "http://localhost:8080/genealogy/lineage/LG4TF2CGQIZNOYRQ52DVK5?max_depth=10" > /dev/null
```

---

## 🔧 FIXING HEALTHCHECK (Next Deployment)

The Memgraph container healthcheck has been fixed but won't apply until container restart.

### Current Issue
```bash
# Check current health status
docker inspect gmnap-genealogy-memgraph --format '{{.State.Health.Status}}'
# Shows: unhealthy
```

**Root Cause**: Healthcheck uses `nc` command which doesn't exist in container

**Fix Applied**: Updated `genealogy-phase2/docker-compose.production.yml` line 23-28

### To Apply Fix (When Safe)
```bash
cd genealogy-phase2

# 1. Stop and recreate container (will apply new healthcheck)
docker-compose -f docker-compose.production.yml down memgraph-genealogy
docker-compose -f docker-compose.production.yml up -d memgraph-genealogy

# 2. Verify healthcheck working
sleep 30  # Wait for startup
docker inspect gmnap-genealogy-memgraph --format '{{.State.Health.Status}}'
# Should show: healthy

# 3. Test database still accessible
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); s = d.session(); r = s.run('MATCH (p:Person) RETURN count(p)'); print(f'Persons: {r.single()[0]}'); d.close()"
```

**⚠️ Warning**: Container restart will briefly interrupt service. Plan during maintenance window.

---

## 📈 MONITORING

### Real-Time Logs
```bash
# Server logs
tail -f /tmp/genealogy_api_fixed.log

# Database container logs
docker logs -f gmnap-genealogy-memgraph

# Last 100 lines
tail -100 /tmp/genealogy_api_fixed.log
```

### Metrics
```bash
# Prometheus metrics
curl http://localhost:8080/metrics

# Grafana dashboard
open http://localhost:3002
# Login: admin / genealogy2025
```

### Database Queries
```bash
# Connection count
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); s = d.session(); r = s.run('SHOW SESSIONS'); sessions = list(r); print(f'Active sessions: {len(sessions)}'); d.close()"

# Edge statistics
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    # Confidence distribution
    result = s.run("""
        MATCH ()-[r:DOCTORAL_ADVISOR]->()
        WITH r.confidence as conf
        RETURN
            count(CASE WHEN conf >= 0.90 THEN 1 END) as high,
            count(CASE WHEN conf >= 0.70 AND conf < 0.90 THEN 1 END) as medium,
            count(CASE WHEN conf < 0.70 THEN 1 END) as low
    """)

    stats = result.single()
    print(f"High confidence (≥0.90): {stats['high']}")
    print(f"Medium confidence (0.70-0.89): {stats['medium']}")
    print(f"Low confidence (<0.70): {stats['low']}")

driver.close()
EOF
```

---

## 🚀 PRODUCTION USAGE PATTERNS

### Pattern 1: Batch Lineage Extraction
```python
#!/usr/bin/env python3
"""Extract lineage for multiple mathematicians"""

from neo4j import GraphDatabase
import requests
import json

# Get all person IDs
driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    result = s.run("MATCH (p:Person) RETURN p.global_id as id LIMIT 100")
    ids = [r['id'] for r in result]

driver.close()

# Extract lineage for each
lineages = {}
for gid in ids:
    response = requests.get(f'http://localhost:8080/genealogy/lineage/{gid}?max_depth=5')
    if response.status_code == 200:
        lineages[gid] = response.json()

# Save results
with open('lineages_batch.json', 'w') as f:
    json.dump(lineages, f, indent=2)

print(f"Extracted lineage for {len(lineages)} persons")
```

### Pattern 2: Network Visualization Data
```python
#!/usr/bin/env python3
"""Generate network graph data for visualization"""

from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver('bolt://localhost:7688')

with driver.session() as s:
    # Get all relationships
    result = s.run("""
        MATCH (student:Person)-[r:DOCTORAL_ADVISOR]->(advisor:Person)
        RETURN
            student.global_id as student_id,
            student.canonical_name as student_name,
            advisor.global_id as advisor_id,
            advisor.canonical_name as advisor_name,
            r.confidence as confidence
    """)

    # Format for D3.js or similar
    nodes = {}
    links = []

    for record in result:
        # Add nodes
        if record['student_id'] not in nodes:
            nodes[record['student_id']] = {
                'id': record['student_id'],
                'name': record['student_name']
            }
        if record['advisor_id'] not in nodes:
            nodes[record['advisor_id']] = {
                'id': record['advisor_id'],
                'name': record['advisor_name']
            }

        # Add link
        links.append({
            'source': record['student_id'],
            'target': record['advisor_id'],
            'confidence': record['confidence']
        })

    graph = {
        'nodes': list(nodes.values()),
        'links': links
    }

    with open('genealogy_network.json', 'w') as f:
        json.dump(graph, f, indent=2)

    print(f"Generated network: {len(nodes)} nodes, {len(links)} edges")

driver.close()
```

### Pattern 3: API Integration
```python
#!/usr/bin/env python3
"""Example API integration for web application"""

import requests
from typing import Optional, Dict, List

class GenealogyAPI:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    def stats(self) -> Dict:
        """Get database statistics"""
        r = requests.get(f"{self.base_url}/genealogy/stats")
        r.raise_for_status()
        return r.json()

    def lineage(self, global_id: str, max_depth: int = 10) -> Dict:
        """Get academic ancestors"""
        r = requests.get(
            f"{self.base_url}/genealogy/lineage/{global_id}",
            params={'max_depth': max_depth}
        )
        r.raise_for_status()
        return r.json()

    def descendants(self, global_id: str, max_depth: int = 10) -> Dict:
        """Get academic descendants"""
        r = requests.get(
            f"{self.base_url}/genealogy/descendants/{global_id}",
            params={'max_depth': max_depth}
        )
        r.raise_for_status()
        return r.json()

# Usage
api = GenealogyAPI()
stats = api.stats()
print(f"Database has {stats['statistics']['persons']} persons")

lineage = api.lineage('LG4TF2CGQIZNOYRQ52DVK5', max_depth=5)
print(f"Found {lineage['total_paths']} lineage paths")
```

---

## 🐛 TROUBLESHOOTING

### Issue: Server Not Responding
```bash
# Check if server is running
ps -p 96681

# Check port
lsof -i :8080

# Restart server (if needed)
kill 96681
sleep 2
export GENEALOGY_BOLT_URI="bolt://localhost:7688"
export PYTHONPATH=.
python3 -m gmnap.cli serve > /tmp/genealogy_api.log 2>&1 &
```

### Issue: Database Connection Failed
```bash
# Check Memgraph running
docker ps | grep genealogy-memgraph

# Test direct connection
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); print('✅ Connected'); d.close()"

# Check container logs
docker logs gmnap-genealogy-memgraph --tail 50
```

### Issue: Empty Results
```bash
# Verify data loaded
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); s = d.session(); r = s.run('MATCH (p:Person) RETURN count(p) as count'); print(f'Persons: {r.single()[\"count\"]}'); d.close()"

# Check relationships
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); s = d.session(); r = s.run('MATCH ()-[r:DOCTORAL_ADVISOR]->() RETURN count(r) as count'); print(f'Edges: {r.single()[\"count\"]}'); d.close()"
```

### Issue: Slow Queries
```bash
# Check database indexes
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7688')
with driver.session() as s:
    result = s.run("SHOW INDEX INFO")
    for record in result:
        print(record)

driver.close()
EOF

# Create index on global_id (if missing)
python3 -c "from neo4j import GraphDatabase; d = GraphDatabase.driver('bolt://localhost:7688'); s = d.session(); s.run('CREATE INDEX ON :Person(global_id)'); print('✅ Index created'); d.close()"
```

---

## 📚 DATA PIPELINE REFERENCE

### Current Data Source
**Source**: theses.fr (French national thesis repository)
**Records**: 10,000 PhD theses
**Date Range**: 2007-2025 (18 years)
**Last Updated**: November 3, 2025

### Pipeline Stages
1. **Harvest**: OAI-PMH from theses.fr → JSON
2. **Extract**: Parse thesis metadata → DOCTORAL_ADVISOR edges
3. **Normalize**: Name normalization (accent preservation, particles)
4. **Match**: GMNAP GlobalID assignment (69.3% reuse rate)
5. **Load**: Insert to Memgraph with deduplication

### Data Quality
- **High confidence**: 12,640 edges (82.4%, confidence ≥ 0.90)
- **Medium confidence**: 2,700 edges (17.6%, confidence 0.70-0.89)
- **Low confidence**: 0 edges (filtered out)
- **ID reuse**: 69.3% (efficient deduplication)
- **Temporal validation**: 0% violations

### Extending Data
```bash
# Harvest more data
cd src/genealogy
python3 -m harvest_fr_full --target 20000  # Increase to 20K records

# Run pipeline
python3 -m extract_edges
python3 -m normalize_names
python3 -m match_person_ids
python3 -m load_memgraph
```

---

## ✅ SUCCESS CRITERIA

**System is working correctly if**:
- ✅ `curl http://localhost:8080/healthz` returns status "ok"
- ✅ `curl http://localhost:8080/genealogy/stats` shows 12,649+ persons
- ✅ Lineage queries return paths for known IDs
- ✅ Descendants queries return results
- ✅ Query response time < 1 second for depth ≤ 10
- ✅ No errors in `/tmp/genealogy_api_fixed.log`
- ✅ Database accessible via bolt://localhost:7688

---

## 📞 SUPPORT

**Logs**: `/tmp/genealogy_api_fixed.log`
**Database**: bolt://localhost:7688
**Grafana**: http://localhost:3002 (admin/genealogy2025)
**Prometheus**: http://localhost:9091

**Documentation**:
- Technical details: `docs/sessions/2025-11-03/GENEALOGY_API_COMPLETE_2025_11_03.md`
- System audit: `docs/sessions/2025-11-03/COMPLETE_AUDIT_2025_11_03.md`
- Session summary: `docs/sessions/2025-11-03/SESSION_COMPLETE_2025_11_03.md`

---

*Last Updated: November 4, 2025*
*Status: ✅ Production Ready*
*Version: 1.0*
