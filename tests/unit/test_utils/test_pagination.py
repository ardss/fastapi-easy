"""Tests for pagination utilities"""

import pytest
from fastapi_easy.utils.pagination import PaginationParams, paginate


class TestPaginationParams:
    """Test pagination parameters"""

    def test_default_params(self):
        """Test default pagination parameters"""
        params = PaginationParams()

        assert params.skip == 0
        assert params.limit == 10

    def test_custom_params(self):
        """Test custom pagination parameters"""
        params = PaginationParams(skip=20, limit=50)

        assert params.skip == 20
        assert params.limit == 50

    def test_validation_invalid_skip(self):
        """Test validation with invalid skip"""
        params = PaginationParams(skip=-1)

        with pytest.raises(ValueError, match="skip must be >= 0"):
            params.validate()

    def test_validation_invalid_limit(self):
        """Test validation with invalid limit"""
        params = PaginationParams(limit=0)

        with pytest.raises(ValueError, match="limit must be > 0"):
            params.validate()

    def test_validation_limit_exceeds_max(self):
        """Test validation when limit exceeds max"""
        params = PaginationParams(limit=200)

        with pytest.raises(ValueError, match="limit must be <= 100"):
            params.validate(max_limit=100)

    def test_validation_success(self):
        """Test successful validation"""
        params = PaginationParams(skip=10, limit=20)

        # Should not raise
        params.validate(max_limit=100)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        params = PaginationParams(skip=5, limit=15)

        result = params.to_dict()

        assert result == {"skip": 5, "limit": 15}


class TestPaginate:
    """Test pagination function"""

    def test_paginate_first_page(self):
        """Test pagination of first page"""
        items = list(range(1, 101))  # 100 items

        result = paginate(items, skip=0, limit=10)

        assert result["data"] == list(range(1, 11))
        assert result["total"] == 100
        assert result["skip"] == 0
        assert result["limit"] == 10
        assert result["page"] == 1
        assert result["pages"] == 10

    def test_paginate_middle_page(self):
        """Test pagination of middle page"""
        items = list(range(1, 101))

        result = paginate(items, skip=20, limit=10)

        assert result["data"] == list(range(21, 31))
        assert result["page"] == 3

    def test_paginate_last_page(self):
        """Test pagination of last page"""
        items = list(range(1, 101))

        result = paginate(items, skip=90, limit=10)

        assert result["data"] == list(range(91, 101))
        assert result["page"] == 10

    def test_paginate_partial_last_page(self):
        """Test pagination with partial last page"""
        items = list(range(1, 96))  # 95 items

        result = paginate(items, skip=90, limit=10)

        assert result["data"] == list(range(91, 96))
        assert result["total"] == 95
        assert result["pages"] == 10

    def test_paginate_empty_list(self):
        """Test pagination of empty list"""
        items = []

        result = paginate(items, skip=0, limit=10)

        assert result["data"] == []
        assert result["total"] == 0
        assert result["pages"] == 0

    def test_paginate_skip_beyond_items(self):
        """Test pagination with skip beyond items"""
        items = list(range(1, 11))

        result = paginate(items, skip=20, limit=10)

        assert result["data"] == []
        assert result["total"] == 10

    def test_paginate_large_limit(self):
        """Test pagination with limit larger than items"""
        items = list(range(1, 6))

        result = paginate(items, skip=0, limit=100)

        assert result["data"] == list(range(1, 6))
        assert result["total"] == 5
        assert result["pages"] == 1
