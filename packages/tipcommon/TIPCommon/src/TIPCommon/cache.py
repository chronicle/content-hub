# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""cache
==========

Module for handling distributed context across different context value to avoid
DB key size limitation.

The class 'Cache' can be used to store and retrieve key: value pairs with keys being
str and values being anything that is JSON serializable.

Example usage:
.. code-block:: python

    from TIPCommon.cache import Cache
    from SiemplifyConnectors import SiemplifyConnectorExecution

    siemplify = SiemplifyConnectorExecution("Test Connector")
    cache = Cache(siemplify, "test_prefix", max_size=3_000)

    cache["key1"] = "value1"
    cache["key2"] = "value2"
    cache.commit()

    # Imitate new iteration of the script
    del cache

    cache = Cache(siemplify, "test_prefix", max_size=3_000)
    del cache["key1"]
    cache.commit()
"""

from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import uuid
import warnings
from collections.abc import Iterator, MutableMapping
from typing import Generic, TypeVar

import SiemplifyUtils

from .base.action import Action
from .base.connector import BaseConnector
from .base.job import Job
from .context import Context, get_context_factory
from .types import JsonString, SingleJson

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_CacheChunkContent: type[MutableMapping[_KT, _VT]] = MutableMapping[_KT, _VT]

CACHE_CHUNKS_METADATA_PATH: str = "{prefix}_cache_chunks_metadata"
ROW_PADDING_LENGTH: int = 40
KEY_HASH_LENGTH: int = 8
INT_CAST_BASE_HEX: int = 16


@dataclasses.dataclass
class CacheChunkMetadata:
    """Stores metadata about cache chunk, such as db size, db key and its index."""

    prefix: str
    db_key: str
    index: int = 0
    db_size: int = 0

    @classmethod
    def from_json(cls, json_obj: dict, prefix: str) -> CacheChunkMetadata:
        return cls(
            prefix=prefix,
            db_key=json_obj["db_key"],
            index=json_obj["index"],
            db_size=json_obj["db_size"],
        )

    def to_json(self) -> SingleJson:
        return {
            "db_key": self.db_key,
            "index": self.index,
            "db_size": self.db_size,
        }

    @property
    def key(self) -> str:
        return f"{self.prefix}_{self.index}"


@dataclasses.dataclass
class CacheChunkCut:
    """Helper class representing a result of 'cut chunk' operation."""

    index: int
    content: _CacheChunkContent


class CacheChunk(MutableMapping[_KT, _VT], Generic[_KT, _VT]):
    """Single Cache Chunk object that holds piece of all the data stored in cache."""

    def __init__(
        self,
        context_handler: Context,
        cache_chunk_metadata: CacheChunkMetadata,
        content: _CacheChunkContent[_KT, _VT] | None = None,
    ):
        self._context: Context = context_handler
        self._content: _CacheChunkContent[_KT, _VT] | None = content
        self.cache_chunk_metadata: CacheChunkMetadata = cache_chunk_metadata

    @property
    def content(self) -> _CacheChunkContent[_KT, _VT]:
        """Get content of cache chunk, fetch from db if needed."""
        if self._content is None:
            self._content = _load__json(
                self._context.get_context(key=self.cache_chunk_metadata.key)
            )

        return self._content

    @content.setter
    def content(self, content: _CacheChunkContent[_KT, _VT]) -> None:
        self._content = content

    def popleft(self) -> _VT | None:
        """Pop left (the oldest) key from content."""
        keys = list(self.content.keys())
        return self.content.pop(keys[0]) if keys else None

    def __setitem__(self, __key: _KT, __value: _VT) -> None:
        self.content[__key] = __value

    def __getitem__(self, __key: _KT) -> _VT:
        return self.content[__key]

    def __delitem__(self, __key: _KT) -> None:
        del self.content[__key]

    def __iter__(self) -> Iterator[_KT]:
        return iter(self.content)

    def __len__(self) -> int:
        if self._content is None:
            return self.cache_chunk_metadata.db_size
        return len(self.content)

    def cut(self, target_length: int) -> CacheChunkCut:
        """Cut chunk to target_length.

        Args:
            target_length (int): Maximum resulting chunk length.

        Returns:
            CacheChunkCut: CacheChunkCut object containing all the extra data.

        """
        keys_sorted = sorted(self.content.keys(), key=lambda _k: _hash_string(_k[0]))
        _target_lookup = set(keys_sorted[:target_length])
        _extra_lookup = set(keys_sorted[target_length:])

        _extra = {_k: _v for _k, _v in self.content.items() if _k in _extra_lookup}
        self.content = {_k: _v for _k, _v in self.content.items() if _k in _target_lookup}
        return CacheChunkCut(index=_hash_string(keys_sorted[target_length]), content=_extra)

    def split(self) -> CacheChunk:
        """Splits current chunk in two approximately equal sized chunks."""
        cut_result = self.cut(len(self) // 2)
        warnings.warn(f"Chunk with key {self.cache_chunk_metadata.key} was split", ResourceWarning)
        return CacheChunk(
            context_handler=self._context,
            cache_chunk_metadata=CacheChunkMetadata(
                prefix=self.cache_chunk_metadata.prefix,
                db_key=str(uuid.uuid4()),
                index=cut_result.index,
            ),
            content=cut_result.content,
        )

    def commit(self) -> list[CacheChunk]:
        """Tries to commit the current chunk to DB.

        If chunk is too heavy, it will split chunks unless size is less than
        maximum chunk size.

        Returns:
            List of resulting chunks

        """
        # If self._content is None, it means data was never accessed, so we can
        # skip commit for this chunk
        if self._content is None:
            return [self]

        json_str = _dump_property_value(self.content)
        if not _row_is_too_long(json_str):
            self.cache_chunk_metadata.db_size = len(self.content)
            self._context.set_context(key=self.cache_chunk_metadata.key, value=json_str)
            return [self]

        new_chunk = self.split()
        return [*self.commit(), *new_chunk.commit()]


class Cache(MutableMapping[_KT, _VT], Generic[_KT, _VT]):
    """Cache object that allows to store and retrieve data from multiple DB keys.

    Each DB key will store a single chunk of data and is represented by CacheChunk
    class. The data in cache is 'lazy loaded' by default, so unless we need to
    retrieve / updated / add a key to a specific chunk, data will NOT be queried for it.
    """

    def __init__(
        self, chronicle_soar: Action | Job | BaseConnector, prefix: str, max_size: int | None = None
    ) -> None:
        self._context: Context = get_context_factory(chronicle_soar)
        self.prefix = prefix
        self.max_size = max_size
        self._cache_chunks: list[CacheChunk[_KT, _VT]] = self._lazy_load_cache_chunks()

    def _lazy_load_cache_chunks(self) -> list[CacheChunk[_KT, _VT]]:
        """Lazy Load partial data about cache chunks."""
        cache_chunks_metadata = self._load_chunks_metadata()
        if not cache_chunks_metadata:
            return [
                CacheChunk(
                    context_handler=self._context,
                    cache_chunk_metadata=CacheChunkMetadata(
                        prefix=self.prefix, db_key=str(uuid.uuid4())
                    ),
                    content={},
                )
            ]

        return [
            CacheChunk(context_handler=self._context, cache_chunk_metadata=cache_chunk_metadata)
            for cache_chunk_metadata in cache_chunks_metadata
        ]

    def _load_chunks_metadata(self) -> list[CacheChunkMetadata]:
        """Load chunks metadata from DB / FS."""
        metadata_list_json = self._context.get_context(
            key=CACHE_CHUNKS_METADATA_PATH.format(prefix=self.prefix)
        )
        if metadata_list_json is None:
            return []

        return sorted(
            [
                CacheChunkMetadata(
                    prefix=self.prefix,
                    db_key=metadata_json["db_key"],
                    index=metadata_json["index"],
                    db_size=metadata_json["db_size"],
                )
                for metadata_json in _load__json(metadata_list_json)
            ],
            key=lambda sk: -sk.index,
        )

    def _commit_chunks_metadata(self) -> None:
        """Commit chunks metadata to DB / FS."""
        storage_keys = [chunk.cache_chunk_metadata.to_json() for chunk in self._cache_chunks]
        self._context.set_context(
            key=CACHE_CHUNKS_METADATA_PATH.format(prefix=self.prefix),
            value=_dump_property_value(storage_keys),
        )

    def _find_chunk_by_key(self, __key: _KT) -> CacheChunk[_KT, _VT]:
        """Find chunk that should contain provided key.

        We will iterate through sorted list of chunks until we find the first one
        that has index that's bigger than current key hash value.
        """
        key_hash = _hash_string(__key)
        return next(filter(lambda c: key_hash > c.cache_chunk_metadata.index, self._cache_chunks))

    @property
    def content(self) -> _CacheChunkContent[_KT, _VT]:
        """Retrieve full merged content from all cache chunks.

        Note: Since this will return a new dictionary with merged content across all
        chunks, it is generally not recommended to be used.
        """
        _full_content = {}
        for chunk in self._cache_chunks:
            _full_content.update(chunk.content)

        return _full_content

    # @override
    def __len__(self) -> int:
        return sum(len(chunk) for chunk in self._cache_chunks)

    # @override
    def __iter__(self) -> Iterator[_KT]:
        return itertools.chain.from_iterable(iter(chunk) for chunk in self._cache_chunks)

    # @override
    def __setitem__(self, key: _KT, value: _VT) -> None:
        _cache_chunk = self._find_chunk_by_key(key)
        _cache_chunk[key] = value
        self.__setitem_callback(_cache_chunk)

    def __setitem_callback(self, _cache_chunk: CacheChunk[_KT, _VT]) -> None:
        """Set item callback that's used for cache size management.

        This should be directly called after inside __setitem__ method after its
        finished. Since dictionaries keys are naturally sorted in the same order they
        were added, we will use it to remove the latest key from the chunk that was
        updated.
        """
        if self.max_size is None:
            return

        if len(self) <= self.max_size:
            return

        if len(_cache_chunk) > 1:
            _cache_chunk.popleft()
            return

    # @override
    def __getitem__(self, key: _KT) -> _VT:
        _cache_chunk = self._find_chunk_by_key(key)
        return _cache_chunk[key]

    # @override
    def __delitem__(self, key: _KT) -> None:
        _cache_chunk = self._find_chunk_by_key(key)
        del _cache_chunk[key]

    def _get_next_non_emtpy_chunk(self, index: int) -> CacheChunk | None:
        _cache_chunks_list = self._cache_chunks[index:] + self._cache_chunks[:index]
        return next(filter(lambda chunk: len(chunk) > 0, _cache_chunks_list), None)

    def _truncate_to_max_size(self) -> None:
        """Truncate chunks one value at a time, until cache max size is met."""
        _current_index = 0
        while len(self) > self.max_size:
            _chunk = self._get_next_non_emtpy_chunk(_current_index)
            _chunk.popleft()
            _current_index += 1

    def balance_chunks(self) -> None:
        """Try balancing the chunks, accessing their data only if necessary.

        Whenever chunk size exceeds the target chunk size, its data will be cut to
        the limit with all extra content being migrated to the next chunk. Final
        chunk gets all the extra data that's left.
        """
        target_chunk_size = len(self) // len(self._cache_chunks)
        cut_result = None

        for chunk_ in self._cache_chunks:
            if cut_result is not None:
                chunk_.cache_chunk_metadata.index = cut_result.index
                chunk_.update(cut_result.content)
                cut_result = None

            if len(chunk_) > target_chunk_size and chunk_ != self._cache_chunks[-1]:
                cut_result = chunk_.cut(target_chunk_size)

    def commit(self) -> None:
        """Commit the chunks to DB / FS.

        This procedure will also account for meeting the cache max size, balance or
        split the chunks if necessary.
        """
        if self.max_size is not None and len(self) > self.max_size:
            self._truncate_to_max_size()
            self.balance_chunks()

        self._cache_chunks = list(
            itertools.chain.from_iterable(chunk.commit() for chunk in self._cache_chunks)
        )
        self._commit_chunks_metadata()


def _hash_string(value__: str) -> int:
    """Helper function to compute the has of str type variable.

    The resulting hash will be cut to KEY_HASH_LENGTH length.
    """
    return (
        int(hashlib.sha256(value__.encode("utf-8")).hexdigest(), INT_CAST_BASE_HEX)
        % 10**KEY_HASH_LENGTH
    )


def _load__json(row_value: JsonString) -> SingleJson | list[SingleJson]:
    """Helper function to load json data from json serialized string."""
    _record = {}
    if row_value:
        _record = json.loads(row_value)

    return _record


def _row_is_too_long(row: JsonString) -> bool:
    return len(row) >= SiemplifyUtils.MAXIMUM_PROPERTY_VALUE - ROW_PADDING_LENGTH


def _dump_property_value(__v) -> JsonString:
    return json.dumps(__v, separators=(",", ":"))
