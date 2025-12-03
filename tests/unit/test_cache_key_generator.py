"""Tests for cache key generator"""

from fastapi_easy.core.cache_key_generator import (
    CacheKeyGenerator,
    generate_cache_key,
)


class TestCacheKeyGenerator:
    """Test cache key generation"""

    def test_generate_consistent_keys(self):
        """Test that same parameters generate same key"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_one", id=1)
        key2 = gen.generate("get_one", id=1)

        assert key1 == key2

    def test_generate_different_keys_different_params(self):
        """Test that different parameters generate different keys"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_one", id=1)
        key2 = gen.generate("get_one", id=2)

        assert key1 != key2

    def test_generate_different_keys_different_operations(self):
        """Test that different operations generate different keys"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_one", id=1)
        key2 = gen.generate("get_all", id=1)

        assert key1 != key2

    def test_parameter_order_independence(self):
        """Test that parameter order doesn't affect key"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_all", filters={"a": 1}, sorts={"b": 2})
        key2 = gen.generate("get_all", sorts={"b": 2}, filters={"a": 1})

        assert key1 == key2

    def test_list_key_generation(self):
        """Test list key generation"""
        gen = CacheKeyGenerator()

        key = gen.generate_list_key("get_all", limit=10, skip=0)

        assert key.startswith("get_all:")

    def test_single_key_generation(self):
        """Test single item key generation"""
        gen = CacheKeyGenerator()

        key = gen.generate_single_key("get_one", item_id=1)

        assert key.startswith("get_one:")

    def test_pattern_generation(self):
        """Test pattern generation"""
        gen = CacheKeyGenerator()

        pattern = gen.get_pattern("get_all")

        assert pattern == "get_all:*"

    def test_non_serializable_objects(self):
        """Test handling of non-serializable objects"""
        gen = CacheKeyGenerator()

        class CustomObj:
            pass

        # Should not raise error
        key = gen.generate("get_one", obj=CustomObj())

        assert key.startswith("get_one:")

    def test_convenience_function(self):
        """Test convenience function"""
        key = generate_cache_key("get_one", id=1)

        assert key.startswith("get_one:")


class TestCacheKeyCollisionPrevention:
    """Test collision prevention"""

    def test_no_collision_with_dict_params(self):
        """Test no collision with dictionary parameters"""
        gen = CacheKeyGenerator()

        # These should generate different keys
        key1 = gen.generate("get_all", filters={"name": "test", "id": 1})
        key2 = gen.generate("get_all", filters={"name": "test1", "id": 1})

        assert key1 != key2

    def test_no_collision_with_list_params(self):
        """Test no collision with list parameters"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_all", ids=[1, 2, 3])
        key2 = gen.generate("get_all", ids=[1, 2, 4])

        assert key1 != key2

    def test_no_collision_with_nested_params(self):
        """Test no collision with nested parameters"""
        gen = CacheKeyGenerator()

        key1 = gen.generate("get_all", filters={"nested": {"a": 1}})
        key2 = gen.generate("get_all", filters={"nested": {"a": 2}})

        assert key1 != key2
