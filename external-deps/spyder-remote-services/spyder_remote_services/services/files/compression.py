from collections import deque
from dataclasses import dataclass
from datetime import datetime
import enum
from struct import Struct
from typing import (
    Any,
    BinaryIO,
    Callable,
    Deque,
    Generator,
    Iterable,
    Iterator,
    Tuple,
    Type,
)
import zlib


class CompressionType(enum.Enum):
    ZIP_64 = enum.auto()
    ZIP_32 = enum.auto()
    NO_COMPRESSION_BUFFERED_32 = enum.auto()
    NO_COMPRESSION_BUFFERED_64 = enum.auto()
    NO_COMPRESSION_STREAMED_32 = enum.auto()
    NO_COMPRESSION_STREAMED_64 = enum.auto()


@dataclass(frozen=True)
class MemberFile:
    name: str
    modified_at: datetime
    mode: int
    method: CompressionType
    data: BinaryIO
    size: int = 0
    crc32: int = 0


class ZipStream:
    local_header_signature = b"PK\x03\x04"
    local_header_struct = Struct("<HHH4sIIIHH")

    data_descriptor_signature = b"PK\x07\x08"
    data_descriptor_zip_64_struct = Struct("<IQQ")
    data_descriptor_zip_32_struct = Struct("<III")

    central_directory_header_signature = b"PK\x01\x02"
    central_directory_header_struct = Struct("<BBBBHH4sIIIHHHHHII")

    zip_64_end_of_central_directory_signature = b"PK\x06\x06"
    zip_64_end_of_central_directory_struct = Struct("<QHHIIQQQQ")

    zip_64_end_of_central_directory_locator_signature = b"PK\x06\x07"
    zip_64_end_of_central_directory_locator_struct = Struct("<IQI")

    end_of_central_directory_signature = b"PK\x05\x06"
    end_of_central_directory_struct = Struct("<HHHHIIH")

    zip_64_extra_signature = b"\x01\x00"
    zip_64_local_extra_struct = Struct("<2sHQQ")
    zip_64_central_directory_extra_struct = Struct("<2sHQQQ")

    mod_at_unix_extra_signature = b"UT"
    mod_at_unix_extra_struct = Struct("<2sH1sl")

    modified_at_struct = Struct("<HH")

    data_descriptor_flag = 0b0000000000001000
    utf8_flag = 0b0000100000000000

    raw_compression = {
        CompressionType.ZIP_64: 8,
        CompressionType.ZIP_32: 8,
        CompressionType.NO_COMPRESSION_BUFFERED_64: 0,
        CompressionType.NO_COMPRESSION_BUFFERED_32: 0,
        CompressionType.NO_COMPRESSION_STREAMED_64: 0,
        CompressionType.NO_COMPRESSION_STREAMED_32: 0,
    }

    def __init__(
        self,
        files: Iterable[MemberFile],
        chunk_size: int = 65536,
        get_compressobj: Callable[[], "zlib._Compress"] = lambda: zlib.compressobj(
            wbits=-zlib.MAX_WBITS, level=9
        ),
        extended_timestamps: bool = True,
        auto_upgrade_central_directory: bool = True,
    ):
        self.files = files
        self.chunk_size = chunk_size
        self.get_compressobj = get_compressobj
        self.extended_timestamps = extended_timestamps
        self.auto_upgrade_central_directory = auto_upgrade_central_directory

        self.offset = 0
        self.central_directory: Deque[Tuple[bytes, bytes, bytes]] = deque()
        self.central_directory_size = 0
        self.central_directory_start_offset = 0
        self.zip_64_central_directory = False

        self.data_func_map = {
            CompressionType.ZIP_64: self._zip_64_local_header_and_data,
            CompressionType.ZIP_32: self._zip_32_local_header_and_data,
            CompressionType.NO_COMPRESSION_BUFFERED_64: self._no_compression_64_local_header_and_data,
            CompressionType.NO_COMPRESSION_BUFFERED_32: self._no_compression_32_local_header_and_data,
            CompressionType.NO_COMPRESSION_STREAMED_64: self._no_compression_streamed_64_local_header_and_data,
            CompressionType.NO_COMPRESSION_STREAMED_32: self._no_compression_streamed_32_local_header_and_data,
        }

    def __iter__(self) -> Iterator[bytes]:
        yield from self.generator()

    def generator(self) -> Iterable[bytes]:
        zipped_chunks = self.get_zipped_chunks_uneven()
        yield from self.evenly_sized(zipped_chunks)

    def evenly_sized(self, chunks: Iterable[bytes]) -> Iterable[bytes]:
        chunk = b""
        offset = 0
        it = iter(chunks)

        def up_to(num: int) -> Iterable[bytes]:
            nonlocal chunk, offset

            while num:
                if offset == len(chunk):
                    try:
                        chunk = next(it)
                    except StopIteration:
                        break
                    else:
                        offset = 0
                to_yield = min(num, len(chunk) - offset)
                offset += to_yield
                num -= to_yield
                yield chunk[offset - to_yield : offset]

        while True:
            block = b"".join(up_to(self.chunk_size))
            if not block:
                break
            yield block

    def write_chunk(self, chunk: bytes) -> Iterable[bytes]:
        self.offset += len(chunk)
        yield chunk

    def _raise_if_beyond(
        self, offset: int, maximum: int, exception_class: Type[Exception]
    ) -> None:
        if offset > maximum:
            raise exception_class()

    def get_zipped_chunks_uneven(self) -> Iterable[bytes]:
        for memberfile in self.files:
            name_encoded = memberfile.name.encode("utf-8")
            self._raise_if_beyond(
                len(name_encoded),
                maximum=0xFFFF,
                exception_class=NameLengthOverflowError,
            )

            mod_at_ms_dos = self.modified_at_struct.pack(
                int(memberfile.modified_at.second / 2)
                | (memberfile.modified_at.minute << 5)
                | (memberfile.modified_at.hour << 11),
                memberfile.modified_at.day
                | (memberfile.modified_at.month << 5)
                | (memberfile.modified_at.year - 1980) << 9,
            )
            mod_at_unix_extra = (
                self.mod_at_unix_extra_struct.pack(
                    self.mod_at_unix_extra_signature,
                    5,  # Size of extra
                    b"\x01",  # Only modification time (as opposed to also other times)
                    int(memberfile.modified_at.timestamp()),
                )
                if self.extended_timestamps
                else b""
            )
            external_attr = (memberfile.mode << 16) | (
                0x10 if name_encoded[-1:] == b"/" else 0x0
            )  # MS-DOS directory

            compression = self.raw_compression[memberfile.method]
            crc_32_mask = 0xFFFFFFFF

            (
                central_directory_header_entry,
                name_encoded,
                extra,
            ) = yield from self.data_func_map[memberfile.method](
                compression,
                name_encoded,
                mod_at_ms_dos,
                mod_at_unix_extra,
                external_attr,
                memberfile.size,
                memberfile.crc32,
                crc_32_mask,
                self.io_to_chunks(memberfile.data),
            )
            self.central_directory_size += (
                len(self.central_directory_header_signature)
                + len(central_directory_header_entry)
                + len(name_encoded)
                + len(extra)
            )
            self.central_directory.append(
                (central_directory_header_entry, name_encoded, extra)
            )

            self.zip_64_central_directory = (
                self.zip_64_central_directory
                or (
                    self.auto_upgrade_central_directory
                    and self.offset > 0xFFFFFFFF
                )
                or (
                    self.auto_upgrade_central_directory
                    and len(self.central_directory) > 0xFFFF
                )
                or memberfile.method
                in (
                    CompressionType.ZIP_64,
                    CompressionType.NO_COMPRESSION_BUFFERED_64,
                    CompressionType.NO_COMPRESSION_STREAMED_64,
                )
            )

            (
                max_central_directory_length,
                max_central_directory_start_offset,
                max_central_directory_size,
            ) = (
                (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
                if self.zip_64_central_directory
                else (0xFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
            )

            self.central_directory_start_offset = self.offset
            central_directory_end_offset = (
                self.offset + self.central_directory_size
            )

            self._raise_if_beyond(
                self.central_directory_start_offset,
                maximum=max_central_directory_start_offset,
                exception_class=OffsetOverflowError,
            )
            self._raise_if_beyond(
                len(self.central_directory),
                maximum=max_central_directory_length,
                exception_class=CentralDirectoryNumberOfEntriesOverflowError,
            )
            self._raise_if_beyond(
                self.central_directory_size,
                maximum=max_central_directory_size,
                exception_class=CentralDirectorySizeOverflowError,
            )
            self._raise_if_beyond(
                central_directory_end_offset,
                maximum=0xFFFFFFFFFFFFFFFF,
                exception_class=OffsetOverflowError,
            )

        for (
            central_directory_header_entry,
            name_encoded,
            extra,
        ) in self.central_directory:
            yield from self.write_chunk(
                self.central_directory_header_signature
            )
            yield from self.write_chunk(central_directory_header_entry)
            yield from self.write_chunk(name_encoded)
            yield from self.write_chunk(extra)

        if self.zip_64_central_directory:
            yield from self.write_zip64_end_of_central_directory()
        else:
            yield from self.write_chunk(
                self.end_of_central_directory_signature
            )
            yield from self.write_chunk(
                self.end_of_central_directory_struct.pack(
                    0,  # Disk number
                    0,  # Disk number with central directory
                    len(self.central_directory),  # On this disk
                    len(self.central_directory),  # In total
                    self.central_directory_size,
                    self.central_directory_start_offset,
                    0,  # ZIP_32 file comment length
                )
            )

    def io_to_chunks(self, data: BinaryIO) -> Iterable[bytes]:
        """Convert a BinaryIO object to an iterable of byte chunks."""
        while chunk := data.read(self.chunk_size):
            yield chunk

    def write_zip64_end_of_central_directory(self) -> Iterable[bytes]:
        central_directory_end_offset = self.offset

        yield from self.write_chunk(
            self.zip_64_end_of_central_directory_signature
        )
        yield from self.write_chunk(
            self.zip_64_end_of_central_directory_struct.pack(
                44,  # Size of zip_64 end of central directory record
                45,  # Version made by
                45,  # Version required
                0,  # Disk number
                0,  # Disk number with central directory
                len(self.central_directory),  # On this disk
                len(self.central_directory),  # In total
                self.central_directory_size,
                self.central_directory_start_offset,
            )
        )

        yield from self.write_chunk(
            self.zip_64_end_of_central_directory_locator_signature
        )
        yield from self.write_chunk(
            self.zip_64_end_of_central_directory_locator_struct.pack(
                0,  # Disk number with zip_64 end of central directory record
                central_directory_end_offset,
                1,  # Total number of disks
            )
        )

        yield from self.write_chunk(self.end_of_central_directory_signature)
        yield from self.write_chunk(
            self.end_of_central_directory_struct.pack(
                0xFFFF,  # Disk number - since zip64
                0xFFFF,  # Disk number with central directory - since zip64
                0xFFFF,  # Number of central directory entries on this disk - since zip64
                0xFFFF,  # Number of central directory entries in total - since zip64
                0xFFFFFFFF,  # Central directory size - since zip64
                0xFFFFFFFF,  # Central directory offset - since zip64
                0,  # ZIP_32 file comment length
            )
        )

    def _zip_data(
        self,
        chunks: Iterable[bytes],
        max_uncompressed_size: int,
        max_compressed_size: int,
    ) -> Generator[bytes, None, Tuple[int, int, int]]:
        uncompressed_size = 0
        compressed_size = 0
        crc_32 = zlib.crc32(b"")
        compress_obj = self.get_compressobj()
        for chunk in chunks:
            uncompressed_size += len(chunk)

            self._raise_if_beyond(
                uncompressed_size,
                maximum=max_uncompressed_size,
                exception_class=UncompressedSizeOverflowError,
            )

            crc_32 = zlib.crc32(chunk, crc_32)
            compressed_chunk = compress_obj.compress(chunk)
            compressed_size += len(compressed_chunk)

            self._raise_if_beyond(
                compressed_size,
                maximum=max_compressed_size,
                exception_class=CompressedSizeOverflowError,
            )

            yield from self.write_chunk(compressed_chunk)

        compressed_chunk = compress_obj.flush()
        compressed_size += len(compressed_chunk)

        self._raise_if_beyond(
            compressed_size,
            maximum=max_compressed_size,
            exception_class=CompressedSizeOverflowError,
        )

        yield from self.write_chunk(compressed_chunk)

        return uncompressed_size, compressed_size, crc_32

    def _zip_64_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFFFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        extra = (
            self.zip_64_local_extra_struct.pack(
                self.zip_64_extra_signature,
                16,  # Size of extra
                0,  # Uncompressed size - since data descriptor
                0,  # Compressed size - since data descriptor
            )
            + mod_at_unix_extra
        )

        flags = self.data_descriptor_flag | self.utf8_flag

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                45,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                0,  # CRC32 - 0 since data descriptor
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        (
            uncompressed_size,
            raw_compressed_size,
            crc_32,
        ) = yield from self._zip_data(
            chunks, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
        )

        compressed_size = raw_compressed_size

        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.data_descriptor_signature)
        yield from self.write_chunk(
            self.data_descriptor_zip_64_struct.pack(
                masked_crc_32, compressed_size, uncompressed_size
            )
        )

        extra = (
            self.zip_64_central_directory_extra_struct.pack(
                self.zip_64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            )
            + mod_at_unix_extra
        )

        return (
            self.central_directory_header_struct.pack(
                45,  # Version made by
                3,  # System made by (UNIX)
                45,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                0xFFFFFFFF,  # Offset of local header - since zip64
            ),
            name_encoded,
            extra,
        )

    def _zip_32_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        extra = mod_at_unix_extra
        flags = self.data_descriptor_flag | self.utf8_flag

        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                20,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                0,  # CRC32 - 0 since data descriptor
                0,  # Compressed size - 0 since data descriptor
                0,  # Uncompressed size - 0 since data descriptor
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        (
            uncompressed_size,
            raw_compressed_size,
            crc_32,
        ) = yield from self._zip_data(chunks, 0xFFFFFFFF, 0xFFFFFFFF)

        compressed_size = raw_compressed_size

        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.data_descriptor_signature)
        yield from self.write_chunk(
            self.data_descriptor_zip_32_struct.pack(
                masked_crc_32, compressed_size, uncompressed_size
            )
        )

        extra = mod_at_unix_extra

        return (
            self.central_directory_header_struct.pack(
                20,  # Version made by
                3,  # System made by (UNIX)
                20,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                file_offset,
            ),
            name_encoded,
            extra,
        )

    def _no_compression_64_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFFFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        chunks, uncompressed_size, crc_32 = (
            self._no_compression_buffered_data_size_crc_32(
                chunks, maximum_size=0xFFFFFFFFFFFFFFFF
            )
        )

        compressed_size = uncompressed_size
        extra = (
            self.zip_64_local_extra_struct.pack(
                self.zip_64_extra_signature,
                16,  # Size of extra
                uncompressed_size,
                compressed_size,
            )
            + mod_at_unix_extra
        )
        flags = self.utf8_flag
        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                45,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        for chunk in chunks:
            yield from self.write_chunk(chunk)

        extra = (
            self.zip_64_central_directory_extra_struct.pack(
                self.zip_64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            )
            + mod_at_unix_extra
        )
        return (
            self.central_directory_header_struct.pack(
                45,  # Version made by
                3,  # System made by (UNIX)
                45,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                0xFFFFFFFF,  # File offset - since zip64
            ),
            name_encoded,
            extra,
        )

    def _no_compression_32_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        chunks, uncompressed_size, crc_32 = (
            self._no_compression_buffered_data_size_crc_32(
                chunks, maximum_size=0xFFFFFFFF
            )
        )

        compressed_size = uncompressed_size
        extra = mod_at_unix_extra
        flags = self.utf8_flag
        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                20,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        for chunk in chunks:
            yield from self.write_chunk(chunk)

        return (
            self.central_directory_header_struct.pack(
                20,  # Version made by
                3,  # System made by (UNIX)
                20,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                file_offset,
            ),
            name_encoded,
            extra,
        )

    def _no_compression_buffered_data_size_crc_32(
        self, chunks: Iterable[bytes], maximum_size: int
    ) -> Tuple[Iterable[bytes], int, int]:
        # We need to determine the total length and CRC32 before output of chunks to client code
        size = 0
        crc_32 = zlib.crc32(b"")

        def _chunks() -> Generator[bytes, None, Any]:
            nonlocal size, crc_32
            for chunk in chunks:
                size += len(chunk)
                self._raise_if_beyond(
                    size,
                    maximum=maximum_size,
                    exception_class=UncompressedSizeOverflowError,
                )
                crc_32 = zlib.crc32(chunk, crc_32)
                yield chunk

        __chunks = tuple(_chunks())

        return __chunks, size, crc_32

    def _no_compression_streamed_64_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFFFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        compressed_size = uncompressed_size
        extra = (
            self.zip_64_local_extra_struct.pack(
                self.zip_64_extra_signature,
                16,  # Size of extra
                uncompressed_size,
                compressed_size,
            )
            + mod_at_unix_extra
        )
        flags = self.utf8_flag
        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                45,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        yield from self._no_compression_streamed_data(
            chunks, uncompressed_size, crc_32, 0xFFFFFFFFFFFFFFFF
        )

        extra = (
            self.zip_64_central_directory_extra_struct.pack(
                self.zip_64_extra_signature,
                24,  # Size of extra
                uncompressed_size,
                compressed_size,
                file_offset,
            )
            + mod_at_unix_extra
        )
        return (
            self.central_directory_header_struct.pack(
                45,  # Version made by
                3,  # System made by (UNIX)
                45,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                0xFFFFFFFF,  # Compressed size - since zip64
                0xFFFFFFFF,  # Uncompressed size - since zip64
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                0xFFFFFFFF,  # File offset - since zip64
            ),
            name_encoded,
            extra,
        )

    def _no_compression_streamed_32_local_header_and_data(
        self,
        compression: int,
        name_encoded: bytes,
        mod_at_ms_dos: bytes,
        mod_at_unix_extra: bytes,
        external_attr: int,
        uncompressed_size: int,
        crc_32: int,
        crc_32_mask: int,
        chunks: Iterable[bytes],
    ) -> Generator[bytes, None, Tuple[bytes, bytes, bytes]]:
        file_offset = self.offset

        self._raise_if_beyond(
            file_offset,
            maximum=0xFFFFFFFF,
            exception_class=OffsetOverflowError,
        )

        compressed_size = uncompressed_size
        extra = mod_at_unix_extra
        flags = self.utf8_flag
        masked_crc_32 = crc_32 & crc_32_mask

        yield from self.write_chunk(self.local_header_signature)
        yield from self.write_chunk(
            self.local_header_struct.pack(
                20,  # Version
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
            )
        )
        yield from self.write_chunk(name_encoded)
        yield from self.write_chunk(extra)

        yield from self._no_compression_streamed_data(
            chunks, uncompressed_size, crc_32, 0xFFFFFFFF
        )

        return (
            self.central_directory_header_struct.pack(
                20,  # Version made by
                3,  # System made by (UNIX)
                20,  # Version required
                0,  # Reserved
                flags,
                compression,
                mod_at_ms_dos,
                masked_crc_32,
                compressed_size,
                uncompressed_size,
                len(name_encoded),
                len(extra),
                0,  # File comment length
                0,  # Disk number
                0,  # Internal file attributes - is binary
                external_attr,
                file_offset,
            ),
            name_encoded,
            extra,
        )

    def _no_compression_streamed_data(
        self,
        chunks: Iterable[bytes],
        uncompressed_size: int,
        crc_32: int,
        maximum_size: int,
    ) -> Generator[bytes, None, Any]:
        actual_crc_32 = zlib.crc32(b"")
        size = 0
        for chunk in chunks:
            actual_crc_32 = zlib.crc32(chunk, actual_crc_32)
            size += len(chunk)
            self._raise_if_beyond(
                size,
                maximum=maximum_size,
                exception_class=UncompressedSizeOverflowError,
            )
            yield from self.write_chunk(chunk)

        if actual_crc_32 != crc_32:
            raise CRC32IntegrityError()

        if size != uncompressed_size:
            raise UncompressedSizeIntegrityError()


class ZipError(Exception):
    pass


class ZipValueError(ZipError, ValueError):
    pass


class ZipIntegrityError(ZipValueError):
    pass


class CRC32IntegrityError(ZipIntegrityError):
    pass


class UncompressedSizeIntegrityError(ZipIntegrityError):
    pass


class ZipOverflowError(ZipValueError, OverflowError):
    pass


class UncompressedSizeOverflowError(ZipOverflowError):
    pass


class CompressedSizeOverflowError(ZipOverflowError):
    pass


class CentralDirectorySizeOverflowError(ZipOverflowError):
    pass


class OffsetOverflowError(ZipOverflowError):
    pass


class CentralDirectoryNumberOfEntriesOverflowError(ZipOverflowError):
    pass


class NameLengthOverflowError(ZipOverflowError):
    pass
