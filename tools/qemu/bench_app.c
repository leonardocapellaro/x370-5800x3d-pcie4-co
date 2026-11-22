/* bench_app.c — the bancada USB-stick EFI application (docs/14).
   Boots from FAT, reads C6HLAB/LISTA.TXT (first line LIVE or REPLAY, then 1
   ..64 aligned NBIO-block addresses) and answers in C6HLAB/LOGnnn.TXT:
     REPLAY mode: values come from the archived capture C6HLAB/A2.BIN
                  (validated against capture_format.h — attrs/magic/version/
                  Phase/ReadsOk/WritesAttempted==0).
     LIVE  mode:  values are read through PciIo via the amd_nbio read helper
                  (nbio.h); on non-AMD platforms the app prints
                  SKIP unsupported-platform and writes the log anyway, so the
                  OVMF harness can observe a controlled, side-effect-free run.
   Never overwrites an existing log (LOG000, LOG001, ...). Built inside EDK2
   (UefiApplicationEntryPoint) or for syntax checking: gcc -fsyntax-only. */
#include "uefi_shim.h"
#include "capture_format.h"
#include "nbio.h"

static UINT32 addresses[NBIO_COUNT];
static UINTN count;
static BOOLEAN replay;
static CHAR8 config[1025];
static struct { UINT32 attributes; SMN_LOG log; UINT32 extra; } capture;
static CHAR8 report[2048];
static UINTN used;

/* At most 64 fixed-size records and a fixed header/trailer. */
static VOID append(const CHAR8 *s) { while (*s) report[used++] = *s++; }
static VOID hex(UINT32 n) {
    for (INTN shift = 28; shift >= 0; shift -= 4)
        report[used++] = "0123456789abcdef"[(n >> shift) & 15];
}

static EFI_STATUS read_file(EFI_FILE_PROTOCOL *dir, CHAR16 *name, VOID *buf, UINTN *size) {
    EFI_FILE_PROTOCOL *file;
    EFI_STATUS status = dir->Open(dir, &file, name, EFI_FILE_MODE_READ, 0);
    if (EFI_ERROR(status)) return status;
    status = file->Read(file, size, buf);
    file->Close(file);
    return status;
}

static BOOLEAN equal(const CHAR8 *a, const CHAR8 *b) {
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

/* ASCII, LF/CRLF, one eight-digit hexadecimal address per line. */
static BOOLEAN parse(UINTN size) {
    BOOLEAN mode_seen = FALSE;
    for (UINTN pos = 0; pos < size;) {
        CHAR8 *line = config + pos;
        while (pos < size && config[pos] != '\n' && config[pos] != '\r') {
            if (config[pos] == 0) return FALSE;
            ++pos;
        }
        config[pos++] = 0;
        if (!*line) continue;
        if (!mode_seen) {
            replay = equal(line, "REPLAY");
            if (!replay && !equal(line, "LIVE")) return FALSE;
            mode_seen = TRUE;
            continue;
        }
        if (count == NBIO_COUNT) return FALSE;
        UINT32 value = 0;
        for (UINTN i = 0; i < 8; ++i) {
            CHAR8 c = *line++;
            if (c >= '0' && c <= '9') value = value * 16 + c - '0';
            else if ((c | 32) >= 'a' && (c | 32) <= 'f') value = value * 16 + (c | 32) - 'a' + 10;
            else return FALSE;
        }
        if (*line || !known_address(value)) return FALSE;
        addresses[count++] = value;
    }
    return count != 0;
}

static EFI_PCI_IO_PROTOCOL *bridge(EFI_BOOT_SERVICES *bs) {
    UINT32 signature, b, c, d;
    __asm__ volatile ("cpuid" : "=a"(signature),"=b"(b),"=c"(c),"=d"(d) : "a"(1U),"c"(0U));
    if (signature != 0x00a20f12U) return NULL;   /* AMD family marker */
    EFI_GUID guid = EFI_PCI_IO_PROTOCOL_GUID;
    EFI_HANDLE *handles;
    UINTN total;
    if (EFI_ERROR(bs->LocateHandleBuffer(ByProtocol, &guid, NULL, &total, &handles))) return NULL;
    EFI_PCI_IO_PROTOCOL *found = NULL;
    for (UINTN i = 0; i < total; ++i) {
        EFI_PCI_IO_PROTOCOL *pci;
        UINTN segment, bus, device, function;
        UINT32 id;
        if (EFI_ERROR(bs->HandleProtocol(handles[i], &guid, (VOID **)&pci))) continue;
        if (EFI_ERROR(pci->GetLocation(pci, &segment, &bus, &device, &function))) continue;
        if (segment || bus || device || function) continue;
        if (!EFI_ERROR(pci->Pci.Read(pci, EfiPciIoWidthUint32, 0, 1, &id)) && id == 0x14801022U) found = pci;
        break;
    }
    bs->FreePool(handles);
    return found;
}

static EFI_STATUS collect(EFI_FILE_PROTOCOL *dir, EFI_BOOT_SERVICES *bs) {
    UINTN size = sizeof(config);
    EFI_STATUS status = read_file(dir, L"LISTA.TXT", config, &size);
    if (EFI_ERROR(status)) return status;
    if (size == sizeof(config) || !parse(size)) {
        append("ERROR invalid-list\r\n"); return EFI_INVALID_PARAMETER;
    }
    EFI_PCI_IO_PROTOCOL *pci = NULL;
    if (replay) {
        append("REPLAY A2 DXE\r\n");
        size = sizeof(capture);
        status = read_file(dir, L"A2.BIN", &capture, &size);
        if (EFI_ERROR(status) || size != sizeof(UINT32) + sizeof(capture.log) ||
            capture.attributes != 6 || capture.log.Magic != SMN12_MAGIC ||
            capture.log.Version != SMN12_VERSION || capture.log.Phase != 1 ||
            capture.log.ReadsOk != SMN12_N_READS || capture.log.WritesAttempted != 0) {
            append("ERROR invalid-capture\r\n"); return EFI_COMPROMISED_DATA;
        }
    } else {
        append("LIVE UEFI application\r\n");
        pci = bridge(bs);
        if (!pci) { append("SKIP unsupported-platform\r\n"); return EFI_UNSUPPORTED; }
    }
    for (UINTN i = 0; i < count; ++i) {
        UINT32 addr = addresses[i], value;
        hex(addr); append(",");
        if (replay) value = capture.log.Raw[SMN12_I_NBIO + (addr - NBIO_BASE) / 4];
        else {
            EFI_TPL previous = bs->RaiseTPL(TPL_NOTIFY);
            status = read_nbio(pci, addr, &value);
            bs->RestoreTPL(previous);
            if (EFI_ERROR(status)) { append("ERROR pci-access\r\n"); return status; }
        }
        hex(value); append("\r\n");
    }
    append("COMPLETE\r\n");
    return EFI_SUCCESS;
}

static EFI_STATUS save(EFI_FILE_PROTOCOL *dir, CHAR16 *name) {
    EFI_FILE_PROTOCOL *file;
    for (UINTN i = 0; i < 1000; ++i) {
        name[3] = '0' + i / 100; name[4] = '0' + (i / 10) % 10; name[5] = '0' + i % 10;
        EFI_STATUS s = dir->Open(dir, &file, name, EFI_FILE_MODE_READ, 0);
        if (!EFI_ERROR(s)) { file->Close(file); continue; }
        if (s != EFI_NOT_FOUND) return s;
        s = dir->Open(dir, &file, name, EFI_FILE_MODE_CREATE | EFI_FILE_MODE_READ | EFI_FILE_MODE_WRITE, 0);
        if (EFI_ERROR(s)) return s;
        UINTN size = used;
        s = file->Write(file, &size, report);
        if (!EFI_ERROR(s) && size != used) s = EFI_VOLUME_FULL;
        if (!EFI_ERROR(s)) s = file->Flush(file);
        EFI_STATUS close = file->Close(file);
        return EFI_ERROR(s) ? s : close;
    }
    return EFI_VOLUME_FULL;
}

EFI_STATUS EFIAPI UefiMain(EFI_HANDLE image, EFI_SYSTEM_TABLE *st) {
    EFI_GUID li = EFI_LOADED_IMAGE_PROTOCOL_GUID, fs = EFI_SIMPLE_FILE_SYSTEM_PROTOCOL_GUID;
    EFI_LOADED_IMAGE_PROTOCOL *loaded;
    EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *volume;
    EFI_FILE_PROTOCOL *root, *dir;
    EFI_BOOT_SERVICES *bs = st->BootServices;
    EFI_STATUS s = bs->HandleProtocol(image, &li, (VOID **)&loaded);
    if (!EFI_ERROR(s)) s = bs->HandleProtocol(loaded->DeviceHandle, &fs, (VOID **)&volume);
    if (!EFI_ERROR(s)) s = volume->OpenVolume(volume, &root);
    if (!EFI_ERROR(s)) {
        s = root->Open(root, &dir, L"C6HLAB", EFI_FILE_MODE_READ, 0);
        root->Close(root);
    }
    if (EFI_ERROR(s)) { st->ConOut->OutputString(st->ConOut, L"C6HLAB: folder unavailable\r\n"); return s; }
    EFI_STATUS result = collect(dir, bs);
    if (!used) append("ERROR cannot-read-list\r\n");
    CHAR16 name[] = L"LOG000.TXT";
    s = save(dir, name);
    dir->Close(dir);
    if (EFI_ERROR(s)) { st->ConOut->OutputString(st->ConOut, L"C6HLAB: save failed\r\n"); return s; }
    st->ConOut->OutputString(st->ConOut, EFI_ERROR(result) ? L"C6HLAB: see diagnostics in " : L"C6HLAB: OK ");
    st->ConOut->OutputString(st->ConOut, name);
    st->ConOut->OutputString(st->ConOut, L"\r\n");
    return result;
}
