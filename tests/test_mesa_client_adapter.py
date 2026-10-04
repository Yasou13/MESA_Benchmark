"""Tests for MesaClientAdapter and BenchmarkAccessControl.

Covers initialization, defaults, config override, and close flows
for MesaClientAdapter and BenchmarkAccessControl.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mesa_benchmark.clients.mesa_client import BenchmarkAccessControl, MesaClientAdapter


class TestMesaClientAdapterDefaults:
    """Verify default attribute values without calling initialize()."""

    def test_defaults(self):
        adapter = MesaClientAdapter()
        assert adapter.enable_multi_hop is True
        assert adapter.enable_rerank is False
        assert adapter.top_n == 5
        assert adapter.timeout_s == 30.0
        assert adapter.memory_dao is None
        assert adapter.retriever is None
        assert adapter.context_id_map == {}

    def test_config_override(self):
        adapter = MesaClientAdapter()
        try:
            # Patch all heavy I/O that initialize() triggers
            with (
                patch("mesa_benchmark.clients.mesa_client.AsyncEngine") as m_sql,
                patch("mesa_benchmark.clients.mesa_client.VectorEngine") as m_vec,
                patch(
                    "mesa_benchmark.clients.mesa_client.KuzuGraphProvider"
                ) as m_graph,
                patch(
                    "mesa_benchmark.clients.mesa_client.initialize_schema",
                    new_callable=AsyncMock,
                ),
                patch("mesa_benchmark.clients.mesa_client.kuzu_initialize_schema"),
                patch("mesa_benchmark.clients.mesa_client.AdapterFactory"),
                patch("mesa_benchmark.clients.mesa_client.QueryAnalyzer"),
                patch("mesa_benchmark.clients.mesa_client.HybridRetriever"),
            ):
                # Make the awaitable mocks return coroutines
                m_sql.return_value.initialize = AsyncMock()
                m_vec.return_value.initialize = AsyncMock()
                m_graph.return_value.initialize = AsyncMock()
                mock_dao = MagicMock()
                mock_dao.initialize = AsyncMock()
                with patch(
                    "mesa_benchmark.clients.mesa_client.MemoryDAO",
                    return_value=mock_dao,
                ):
                    adapter.initialize(
                        {
                            "enable_multi_hop": False,
                            "top_n": 20,
                            "enable_rerank": True,
                            "timeout_s": 60.0,
                        }
                    )

            assert adapter.enable_multi_hop is False
            assert adapter.top_n == 20
            assert adapter.enable_rerank is True
            assert adapter.timeout_s == 60.0
        finally:
            adapter.close()


class TestMesaClientAdapterClose:
    """Verify close() cleans up temp_dir."""

    def test_close_cleans_tempdir(self):
        adapter = MesaClientAdapter()
        mock_temp = MagicMock()
        adapter.temp_dir = mock_temp
        adapter.close()
        mock_temp.cleanup.assert_called_once()

    def test_close_without_tempdir(self):
        adapter = MesaClientAdapter()
        adapter.temp_dir = None
        # Should not raise
        adapter.close()


class TestBenchmarkAccessControl:
    """BenchmarkAccessControl always grants access."""

    @pytest.mark.asyncio
    async def test_always_true(self):
        ac = BenchmarkAccessControl()
        assert await ac.check_access("any", "any", "read") is True
        assert await ac.check_access("", "", "write") is True
