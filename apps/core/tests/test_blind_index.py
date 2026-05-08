"""Tests for apps.core.blind_index — HMAC-SHA256 blind-index for equality."""
from __future__ import annotations

import base64
import os

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

import pytest

from apps.core import blind_index


def _fresh_key() -> str:
    return blind_index.generate_blind_index_key()


@pytest.fixture(autouse=True)
def _reset_caches():
    blind_index._clear_caches()
    yield
    blind_index._clear_caches()


class TestHashValue:
    def test_round_trip_consistent(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            a = blind_index.hash_value("alice@example.com")
            b = blind_index.hash_value("alice@example.com")
            assert a == b
            assert isinstance(a, bytes) and len(a) == 32

    def test_normalization_case_insensitive(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            assert blind_index.hash_value("Alice@Example.COM") == blind_index.hash_value(
                "alice@example.com"
            )

    def test_normalization_strips_outer_whitespace(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            assert blind_index.hash_value("  alice@example.com  ") == blind_index.hash_value(
                "alice@example.com"
            )

    def test_different_plaintexts_differ(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            a = blind_index.hash_value("alice@example.com")
            b = blind_index.hash_value("bob@example.com")
            assert a != b

    def test_none_and_empty_return_none(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            assert blind_index.hash_value(None) is None
            assert blind_index.hash_value("") is None

    def test_different_keys_produce_different_hashes(self):
        k1 = _fresh_key()
        k2 = _fresh_key()
        with override_settings(BLIND_INDEX_KEYS=k1):
            h1 = blind_index.hash_value("alice@example.com")
        blind_index._clear_caches()
        with override_settings(BLIND_INDEX_KEYS=k2):
            h2 = blind_index.hash_value("alice@example.com")
        assert h1 != h2


class TestKeyConfiguration:
    def test_unset_keys_raises(self):
        with override_settings(BLIND_INDEX_KEYS=""):
            with pytest.raises(ImproperlyConfigured):
                blind_index.hash_value("anything")

    def test_invalid_length_rejected(self):
        bad = base64.urlsafe_b64encode(os.urandom(16)).decode().rstrip("=")  # 16 bytes, not 32
        with override_settings(BLIND_INDEX_KEYS=bad):
            with pytest.raises(ImproperlyConfigured, match="32 bytes"):
                blind_index.hash_value("anything")

    def test_padded_and_unpadded_keys_both_accepted(self):
        material = os.urandom(32)
        unpadded = base64.urlsafe_b64encode(material).decode().rstrip("=")
        padded = base64.urlsafe_b64encode(material).decode()
        # Same key in two encodings should produce the same hash.
        with override_settings(BLIND_INDEX_KEYS=unpadded):
            h1 = blind_index.hash_value("alice@example.com")
        blind_index._clear_caches()
        with override_settings(BLIND_INDEX_KEYS=padded):
            h2 = blind_index.hash_value("alice@example.com")
        assert h1 == h2


class TestLookupHashes:
    def test_single_key_returns_one_hash(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            assert len(blind_index.lookup_hashes("alice@example.com")) == 1

    def test_rotation_two_keys_returns_two_hashes(self):
        new = _fresh_key()
        old = _fresh_key()
        with override_settings(BLIND_INDEX_KEYS=f"{new},{old}"):
            hashes = blind_index.lookup_hashes("alice@example.com")
            assert len(hashes) == 2
            # Mid-rotation, the lookup must include the row's pre-rotation
            # hash so queries continue to match.
            assert hashes[0] != hashes[1]

    def test_lookup_hashes_match_hash_value_under_each_key(self):
        new = _fresh_key()
        old = _fresh_key()

        # What hash_value would have produced under the old key alone:
        with override_settings(BLIND_INDEX_KEYS=old):
            old_hash = blind_index.hash_value("alice@example.com")
        blind_index._clear_caches()

        # And under the new key alone:
        with override_settings(BLIND_INDEX_KEYS=new):
            new_hash = blind_index.hash_value("alice@example.com")
        blind_index._clear_caches()

        # During rotation, lookup_hashes returns both:
        with override_settings(BLIND_INDEX_KEYS=f"{new},{old}"):
            assert blind_index.lookup_hashes("alice@example.com") == [new_hash, old_hash]

    def test_empty_input_returns_empty_list(self):
        with override_settings(BLIND_INDEX_KEYS=_fresh_key()):
            assert blind_index.lookup_hashes(None) == []
            assert blind_index.lookup_hashes("") == []
