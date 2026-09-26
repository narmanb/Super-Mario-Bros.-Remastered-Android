"""Reject APKs that reference Android SAF's DocumentFile without packaging it."""

import struct
import sys
import zipfile


DOCUMENT_FILE = b"Landroidx/documentfile/provider/DocumentFile;"


def defines_document_file(dex: bytes) -> bool:
    if not dex.startswith(b"dex\n"):
        raise ValueError("Invalid DEX file")

    def uint(offset: int) -> int:
        return struct.unpack_from("<I", dex, offset)[0]

    strings_offset = uint(0x3C)
    types_offset = uint(0x44)
    classes_size, classes_offset = uint(0x60), uint(0x64)

    for index in range(classes_size):
        type_index = uint(classes_offset + index * 32)
        string_index = uint(types_offset + type_index * 4)
        string_offset = uint(strings_offset + string_index * 4)
        # DEX strings start with an unsigned LEB128 UTF-16 length.
        while dex[string_offset] & 0x80:
            string_offset += 1
        string_offset += 1
        if dex[string_offset:string_offset + len(DOCUMENT_FILE)] == DOCUMENT_FILE:
            return True
    return False


with zipfile.ZipFile(sys.argv[1]) as apk:
    dex_names = [name for name in apk.namelist() if name.startswith("classes") and name.endswith(".dex")]
    if not any(defines_document_file(apk.read(name)) for name in dex_names):
        sys.exit("APK is missing the DocumentFile class required to read Android folders")

print("APK contains the Android DocumentFile class required for folder imports")
