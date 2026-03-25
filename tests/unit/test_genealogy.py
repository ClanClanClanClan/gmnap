"""Tests for src/genealogy/query module."""

from unittest.mock import MagicMock, patch


class TestQueryLineage:
    """Test query_lineage function."""

    def test_import_succeeds(self):
        """Module can be imported."""
        from src.genealogy.query import query_lineage, lineage_to_dot

        assert callable(query_lineage)
        assert callable(lineage_to_dot)

    def test_returns_none_without_driver(self):
        """Returns None when neo4j driver is not installed."""
        with patch("src.genealogy.query.GraphDatabase", None):
            from src.genealogy.query import query_lineage

            result = query_lineage("SOME_GID")
            assert result is None

    def test_returns_none_for_missing_node(self):
        """Returns None when GlobalID not found in graph."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        mock_gd = MagicMock()
        mock_gd.driver.return_value = mock_driver

        with patch("src.genealogy.query.GraphDatabase", mock_gd):
            from src.genealogy.query import query_lineage

            result = query_lineage("NONEXISTENT_GID")
            assert result is None

    def test_returns_lineage_dict(self):
        """Returns proper lineage structure with root, ancestors, descendants, edges."""
        # Mock a root node record
        root_record = {
            "global_id": "EULER_1707",
            "name": "Euler, Leonhard",
            "birth_year": 1707,
            "death_year": 1783,
            "region": "A2",
            "msc_primary": "01-XX",
            "native_name": "Euler, Leonhard",
            "confidence": 1.0,
            "betweenness": 0.5,
        }

        # Mock ancestors
        ancestor_records = [
            {
                "global_id": "BERNOULLI_1667",
                "name": "Bernoulli, Johann",
                "birth_year": 1667,
                "death_year": 1748,
                "region": "A2",
                "msc_primary": None,
                "distance": 1,
            }
        ]

        # Build mock session that returns different results for different queries
        call_count = {"n": 0}

        def mock_run(query, **kwargs):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:  # NODE_QUERY
                record = MagicMock()
                record.items.return_value = root_record.items()
                record.__iter__ = MagicMock(return_value=iter(root_record.items()))
                # Make it behave like dict()
                result.single.return_value = record
                return result
            elif call_count["n"] == 2:  # ANCESTORS_QUERY
                records = []
                for ar in ancestor_records:
                    rec = MagicMock()
                    rec.items.return_value = ar.items()
                    rec.__iter__ = MagicMock(return_value=iter(ar.items()))
                    records.append(rec)
                result.__iter__ = MagicMock(return_value=iter(records))
                return result
            elif call_count["n"] == 3:  # DESCENDANTS_QUERY
                result.__iter__ = MagicMock(return_value=iter([]))
                return result
            else:  # EDGES_QUERY
                result.__iter__ = MagicMock(return_value=iter([]))
                return result

        mock_session = MagicMock()
        mock_session.run = mock_run
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session

        mock_gd = MagicMock()
        mock_gd.driver.return_value = mock_driver

        with patch("src.genealogy.query.GraphDatabase", mock_gd):
            from src.genealogy.query import query_lineage

            result = query_lineage("EULER_1707", depth=3)

        assert result is not None
        assert "root" in result
        assert "ancestors" in result
        assert "descendants" in result
        assert "edges" in result
        assert "meta" in result
        assert result["meta"]["depth"] == 3

    def test_depth_clamped(self):
        """Depth is clamped between 1 and 10."""
        with patch("src.genealogy.query.GraphDatabase", None):
            from src.genealogy.query import query_lineage

            # Just verify it doesn't crash with extreme depth values
            query_lineage("X", depth=0)
            query_lineage("X", depth=100)


class TestLineageToDot:
    """Test DOT format export."""

    def test_produces_valid_dot(self):
        """lineage_to_dot produces valid DOT output."""
        from src.genealogy.query import lineage_to_dot

        lineage = {
            "root": {
                "global_id": "EULER_1707",
                "name": "Euler, Leonhard",
            },
            "ancestors": [
                {
                    "global_id": "BERNOULLI_1667",
                    "name": "Bernoulli, Johann",
                    "birth_year": 1667,
                    "death_year": 1748,
                    "distance": 1,
                }
            ],
            "descendants": [
                {
                    "global_id": "STUDENT_1750",
                    "name": "Student, A.",
                    "birth_year": 1750,
                    "distance": 1,
                }
            ],
            "edges": [
                {
                    "student_id": "EULER_1707",
                    "advisor_id": "BERNOULLI_1667",
                    "confidence": 0.95,
                },
                {
                    "student_id": "STUDENT_1750",
                    "advisor_id": "EULER_1707",
                },
            ],
        }

        dot = lineage_to_dot(lineage)
        assert dot.startswith("digraph lineage {")
        assert dot.endswith("}")
        assert "Euler, Leonhard" in dot
        assert "Bernoulli, Johann" in dot
        assert "EULER_1707" in dot
        assert "->" in dot  # edges present

    def test_empty_lineage(self):
        """Handles lineage with no ancestors or descendants."""
        from src.genealogy.query import lineage_to_dot

        lineage = {
            "root": {"global_id": "SOLO_ID", "name": "Solo, Person"},
            "ancestors": [],
            "descendants": [],
            "edges": [],
        }

        dot = lineage_to_dot(lineage)
        assert "digraph lineage {" in dot
        assert "Solo, Person" in dot
        assert "->" not in dot  # no edges
